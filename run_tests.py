import json
import os
import time
import importlib
import math
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from contextlib import redirect_stdout
import io

# Load input.json
ROOT = Path(__file__).parent
INPUT = json.loads((ROOT / 'input.json').read_text())
ARTIFACTS = ROOT / 'artifacts'
ARTIFACTS.mkdir(exist_ok=True)

# Helpers

def get_handler_from_path(path: str):
    module_name, func_name = path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def run_single_request(handler, request_def, auth_token, timeout_ms):
    method = request_def.get('method', 'GET')
    query = request_def.get('query', {})
    # Map endpoint to parameters
    # For /api/users -> handler get_users(page, per_page)
    t0 = time.time()
    try:
        res = handler(page=query.get('page', 1), per_page=query.get('per_page', 100), auth=auth_token)
        latency = (time.time() - t0) * 1000
        if latency > timeout_ms:
            return {'status': 504, 'latency_ms': latency, 'error': 'timeout'}
        res['_latency_ms'] = latency
        return res
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return {'status': 500, 'latency_ms': latency, 'error': str(e)}


def run_single_followers(handler, request_def, auth_token, timeout_ms):
    query = request_def.get('query', {})
    t0 = time.time()
    try:
        res = handler(user_id=1, page=query.get('page', 1), per_page=query.get('per_page', 100), auth=auth_token)
        latency = (time.time() - t0) * 1000
        if latency > timeout_ms:
            return {'status': 504, 'latency_ms': latency, 'error': 'timeout'}
        res['_latency_ms'] = latency
        return res
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return {'status': 500, 'latency_ms': latency, 'error': str(e)}


def run_workload(label, handler_map, auth_token, total_requests, concurrency, warmup_requests, timeout_ms):
    print(f"Running workload: {label} (total={total_requests}, concurrency={concurrency})")
    # Build list of request defs in order
    requests = INPUT['workload']['requests']

    # Warmup
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = []
        for i in range(warmup_requests):
            req = requests[i % len(requests)]
            if req['endpoint'] == '/api/users':
                handler = handler_map['GET /api/users']
                futures.append(ex.submit(run_single_request, handler, req, auth_token, timeout_ms))
            else:
                handler = handler_map['GET /api/users/1/followers']
                futures.append(ex.submit(run_single_followers, handler, req, auth_token, timeout_ms))
        for f in as_completed(futures):
            _ = f.result()
    print("Warmup complete")

    latencies = []
    statuses = {}
    queries_per_request = []
    slow_queries = []
    errors = 0

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = []
        for i in range(total_requests):
            req = requests[i % len(requests)]
            if req['endpoint'] == '/api/users':
                handler = handler_map['GET /api/users']
                futures.append(ex.submit(run_single_request, handler, req, auth_token, timeout_ms))
            else:
                handler = handler_map['GET /api/users/1/followers']
                futures.append(ex.submit(run_single_followers, handler, req, auth_token, timeout_ms))

        for f in as_completed(futures):
            r = f.result()
            latency = r.get('_latency_ms', r.get('latency_ms', None))
            if latency is not None:
                latencies.append(latency)
            status = r.get('status', 500)
            statuses[status] = statuses.get(status, 0) + 1
            if status != INPUT['metrics']['expected_status']:
                errors += 1
            # metrics
            metrics = r.get('_metrics')
            if metrics:
                queries_per_request.append(metrics.get('queries', 0))
                slow = metrics.get('slow_queries', [])
                for s in slow:
                    s['label'] = label
                    slow_queries.append(s)

    total = len(latencies)
    error_rate = (errors / total_requests) * 100.0
    def percentile(data, p):
        if not data:
            return None
        k = (len(data)-1) * (p/100.0)
        f = int(k)
        c = min(f+1, len(data)-1)
        if f == c:
            return float(sorted(data)[int(k)])
        d0 = sorted(data)[f] * (c - k)
        d1 = sorted(data)[c] * (k - f)
        return float(d0 + d1)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)

    summary = {
        'label': label,
        'total_requests': total_requests,
        'concurrency': concurrency,
        'p50_ms': p50,
        'p95_ms': p95,
        'p99_ms': p99,
        'error_rate_percent': error_rate,
        'status_distribution': statuses,
        'raw_latencies_ms': latencies,
        'queries_per_request': queries_per_request,
        'slow_queries': slow_queries
    }

    # Persist artifacts
    (ARTIFACTS / f'raw_latency_{label}.json').write_text(json.dumps(latencies))
    (ARTIFACTS / f'summary_{label}.json').write_text(json.dumps(summary, default=str))
    (ARTIFACTS / f'queries_{label}.json').write_text(json.dumps(queries_per_request))
    (ARTIFACTS / f'slow_queries_{label}.json').write_text(json.dumps(slow_queries, default=str))

    return summary


def main():
    # Seed DB if required
    seed_info = INPUT.get('dataset', {}).get('seed', {})
    commands_log = []
    run_output = io.StringIO()

    if seed_info.get('required'):
        # execute the seed function from seed_db.py
        import seed_db
        cmd = seed_info.get('cmd', 'python seed_db.py')
        commands_log.append(cmd)
        print(f"Seeding database with command: {cmd}")
        with redirect_stdout(run_output):
            seed_db.seed()

    # Prepare handler map
    handler_map = {}
    for route, func_path in INPUT['entrypoints']['handler_map'].items():
        handler_map[route] = get_handler_from_path(func_path)

    # Run baseline
    load = INPUT['workload']['load_profile']
    auth_token = INPUT['environment']['auth']['token']

    # Baseline
    import handlers
    handlers.OPTIMIZED = False
    summary_before = run_workload('before_optimization', handler_map, auth_token, load['total_requests'], load['concurrency'], load['warmup_requests'], load['timeout_ms'])

    # Optimized
    handlers.OPTIMIZED = True
    summary_after = run_workload('after_optimization', handler_map, auth_token, load['total_requests'], load['concurrency'], load['warmup_requests'], load['timeout_ms'])

    # Comparison
    comparison = {
        'before': {'p50': summary_before['p50_ms'], 'p95': summary_before['p95_ms'], 'p99': summary_before['p99_ms'], 'error_rate': summary_before['error_rate_percent']},
        'after': {'p50': summary_after['p50_ms'], 'p95': summary_after['p95_ms'], 'p99': summary_after['p99_ms'], 'error_rate': summary_after['error_rate_percent']}
    }
    (ARTIFACTS / 'comparison.json').write_text(json.dumps(comparison, default=str))

    # Write logs
    (ARTIFACTS / 'commands_executed_log.txt').write_text('\n'.join(commands_log))
    (ARTIFACTS / 'run_output_log.txt').write_text(run_output.getvalue())

    # Optimization summary
    opt_summary = "Applied batched follower counts in `get_users` and batched user fetch in `get_user_followers` to avoid N+1 queries."
    (ARTIFACTS / 'optimization_summary.txt').write_text(opt_summary)

    # Print final summary
    print("--- Run Complete ---")
    print(json.dumps({'before': {'p95': summary_before['p95_ms'], 'p99': summary_before['p99_ms']}, 'after': {'p95': summary_after['p95_ms'], 'p99': summary_after['p99_ms']}}, indent=2))

if __name__ == '__main__':
    main()
