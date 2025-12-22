import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / 'test_db.sqlite'

# Ensure the file exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Per-thread query counters and slow query logs
thread_local = threading.local()

SLOW_MS = 50  # queries slower than this will be recorded


def get_conn():
    # Use check_same_thread=False behavior by opening a new connection per thread
    con = sqlite3.connect(str(DB_PATH), timeout=30.0)
    con.row_factory = sqlite3.Row
    return con


def _record_query(duration_ms, statement):
    ctx = getattr(thread_local, 'metrics', None)
    if ctx is None:
        return
    ctx['queries'] += 1
    if duration_ms >= SLOW_MS:
        ctx['slow_queries'].append({'sql': statement.strip(), 'duration_ms': duration_ms})


def execute(con, sql, params=()):
    t0 = time.time()
    cur = con.execute(sql, params)
    con.commit()
    duration = (time.time() - t0) * 1000
    _record_query(duration, sql)
    return cur


def new_request_context():
    ctx = {'queries': 0, 'slow_queries': []}
    thread_local.metrics = ctx
    return ctx


def get_request_context():
    return getattr(thread_local, 'metrics', {'queries': 0, 'slow_queries': []})
