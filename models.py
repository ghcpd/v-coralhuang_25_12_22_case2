import sqlite3
import threading
import time
from contextlib import contextmanager

DB_PATH = "./test.db"

# Thread-local storage for per-request instrumentation
_tls = threading.local()

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_thread_state():
    if not hasattr(_tls, "query_count"):
        _tls.query_count = 0
        _tls.queries = []
        _tls.slow_queries = []

@contextmanager
def instrument_request():
    """Context manager to reset and collect per-request query counts and slow queries."""
    ensure_thread_state()
    _tls.query_count = 0
    _tls.queries = []
    _tls.slow_queries = []
    start = time.time()
    try:
        yield
    finally:
        _tls.request_time = time.time() - start

def log_query(sql, params, duration):
    ensure_thread_state()
    _tls.query_count += 1
    _tls.queries.append({"sql": sql, "params": params, "duration": duration})
    if duration >= 0.005:  # 5ms threshold for "slow"
        _tls.slow_queries.append({"sql": sql, "params": params, "duration": duration})

def get_request_metrics():
    ensure_thread_state()
    return {
        "query_count": _tls.query_count,
        "queries": _tls.queries,
        "slow_queries": _tls.slow_queries,
        "request_time": getattr(_tls, "request_time", None),
    }

# Lightweight execute helper that logs timings
def execute(sql, params=(), fetchall=False, fetchone=False):
    conn = get_conn()
    cur = conn.cursor()
    t0 = time.time()
    try:
        cur.execute(sql, params)
        conn.commit()
        duration = time.time() - t0
        log_query(sql, params, duration)
        if fetchall:
            return [dict(r) for r in cur.fetchall()]
        if fetchone:
            row = cur.fetchone()
            return dict(row) if row else None
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()

# Convenience helpers
def executemany(sql, seq_of_params):
    conn = get_conn()
    cur = conn.cursor()
    t0 = time.time()
    try:
        cur.executemany(sql, seq_of_params)
        conn.commit()
        duration = time.time() - t0
        log_query(sql, (len(seq_of_params),), duration)
        return cur.rowcount
    finally:
        cur.close()
        conn.close()
