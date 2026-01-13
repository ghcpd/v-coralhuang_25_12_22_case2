"""One-command runner for the performance task.

Usage: python run_tests.py

It will:
- read `input.json`
- seed the DB if required
- run baseline (imports `handlers_baseline`)
- run optimized (imports `handlers_optimized`)
- write artifacts under ./artifacts
"""
import json
import math
import os
import random
import statistics
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import app
import models
import seed_db

ARTIFACT_DIR = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

INPUT = json.load(open("input.json"))
WORKLOAD = INPUT["workload"]
METRICS = INPUT["metrics"]

# Thread-local storage for query counting
_tls = threading.local()


def _attach_query_listeners(engine):
    """Attach listeners that increment per-thread counters for executed SQL."""

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        dur = (time.time() - getattr(context, "_query_start_time", time.time()))
        # initialize on demand
        q = getattr(_tls, "queries", None)
        if q is not None:
            q.append({"sql": statement, "params": parameters, "dur": dur})


def _make_request_callable(req_def):
    """Return a callable that runs the handler and returns a result dict."""
    endpoint = req_def["endpoint"]
    page = req_def.get("query", {}).get("page", 1)
    per_page = req_def.get("query", {}).get("per_page", 100)

    if endpoint == "/api/users":
        handler_name = "get_users"
        handler_module = None  # set by runner
    elif endpoint.startswith("/api/users/") and endpoint.endswith("/followers"):
        handler_name = "get_user_followers"
        handler_module = None
        # extract user id
        user_id = int(endpoint.split("/")[3])
    else:
        raise RuntimeError("unknown endpoint")

    def make_call(handler, token):
        def call():
            # create a fresh DB session per request (like web apps do)
            session = app.get_session()
            session.clear_queries()
            start = time.time()
            try:
                if endpoint == "/api/users":
                    r = handler(session, token, page=page, per_page=per_page)
                else:
                    r = handler(session, token, user_id, page=page, per_page=per_page)
                status = r.get("status", 200)
            except Exception as e:
                status = 500
                r = {"status": 500, "body": {"error": str(e)}}
            dur = (time.time() - start) * 1000.0
            qlist = session.fetch_queries()
            # cleanup
            try:
                session.close()
            except Exception:
                pass
            return {"status": status, "body": r.get("body"), "t": dur, "queries": qlist}

        return call

    return endpoint, handler_name, locals().get("user_id", None), make_call


def run_load(handler_callable, token: str, total_requests: int, concurrency: int, timeout_s: float, warmup: int = 0):
    # warmup (per-future tolerant)
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(handler_callable) for _ in range(warmup)]
        for f in futures:
            try:
                f.result(timeout=timeout_s)
            except Exception:
                pass

    results = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(handler_callable) for _ in range(total_requests)]
        for f in futures:
            try:
                results.append(f.result(timeout=timeout_s))
            except Exception as e:
                # timeout or other exception — record as a failure
                results.append({"status": 500, "body": {"error": str(e)}, "t": timeout_s * 1000.0, "queries": []})
    wall = time.time() - start
    return results, wall


def summarize_results(results: List[Dict[str, Any]]):
    latencies = [r["t"] for r in results]
    statuses = [r["status"] for r in results]
    query_counts = [len(r.get("queries", [])) for r in results]
    errors = sum(1 for s in statuses if s != INPUT["metrics"]["expected_status"]) 

    def pct(n):
        if not latencies:
            return None
        return statistics.quantiles(latencies, n=100)[int(n) - 1]

    def percentile(p):
        if not latencies:
            return None
        k = max(0, min(len(latencies) - 1, int(math.ceil((p / 100.0) * len(latencies))) - 1))
        return sorted(latencies)[k]

    summary = {
        "count": len(results),
        "p50_ms": percentile(50),
        "p95_ms": percentile(95),
        "p99_ms": percentile(99),
        "avg_ms": statistics.mean(latencies) if latencies else None,
        "status_counts": dict(Counter(statuses)),
        "error_rate": errors / len(results) if results else None,
        "avg_queries": statistics.mean(query_counts) if query_counts else None,
        "raw_latencies": latencies,
        "query_counts_per_request": query_counts,
    }
    return summary


def write_artifacts(label, results, elapsed_wall, commands_executed: List[str], extra=None):
    summary = summarize_results(results)
    out = {
        "label": label,
        "summary": summary,
        "wall_seconds": elapsed_wall,
        "commands": commands_executed,
        "extra": extra or {},
    }
    open(os.path.join(ARTIFACT_DIR, f"{label}_summary.json"), "w").write(json.dumps(out, indent=2))
    # raw latencies
    open(os.path.join(ARTIFACT_DIR, f"{label}_latencies.json"), "w").write(json.dumps(summary["raw_latencies"]))
    open(os.path.join(ARTIFACT_DIR, f"{label}_query_counts.json"), "w").write(json.dumps(summary["query_counts_per_request"]))
    return out


def single_run(handler_module, handler_name, workload_def, label, input_cfg):
    token = input_cfg["environment"]["auth"]["token"]
    concurrency = input_cfg["workload"]["load_profile"]["concurrency"]
    total = input_cfg["workload"]["load_profile"]["total_requests"]
    warmup = input_cfg["workload"]["load_profile"]["warmup_requests"]
    timeout_s = input_cfg["workload"]["load_profile"]["timeout_ms"] / 1000.0

    endpoint, handler_name, user_id, make_call = _make_request_callable(workload_def)
    handler = getattr(handler_module, handler_name)
    call = make_call(handler, token)

    # ensure DB/schema exists
    app.init_db()

    results, wall = run_load(call, token, total, concurrency, timeout_s, warmup=warmup)
    commands = ["seed_db.py (if run)", f"handler={handler_module.__name__}.{handler_name}"]
    art = write_artifacts(label, results, wall, commands)
    return art


def run_all():
    commands_executed = []

    # 1) seed if required
    if INPUT["dataset"]["seed"]["required"]:
        commands_executed.append(INPUT["dataset"]["seed"]["cmd"])
        seed_db.seed()

    # ensure DB initialized
    engine = app.init_db()

    # import baseline module and run baseline for each workload entry
    import handlers_baseline as baseline_mod

    baseline_arts = []
    for req in WORKLOAD["requests"]:
        label = f"baseline_{req['id']}"
        print("Running baseline:", req["endpoint"])
        art = single_run(baseline_mod, req.get("handler", ""), req, label, INPUT)
        baseline_arts.append(art)

    # run optimized implementations (direct import)
    import handlers_optimized as opt_mod

    opt_arts = []
    for req in WORKLOAD["requests"]:
        label = f"optimized_{req['id']}"
        print("Running optimized:", req["endpoint"])
        art = single_run(opt_mod, req.get("handler", ""), req, label, INPUT)
        opt_arts.append(art)

    # aggregate and write comparison
    comp = {
        "baseline": baseline_arts,
        "optimized": opt_arts,
    }
    open(os.path.join(ARTIFACT_DIR, "comparison.json"), "w").write(json.dumps(comp, indent=2))
    print("All runs complete. Artifacts written to", ARTIFACT_DIR)


if __name__ == "__main__":
    run_all()
