"""Lightweight sqlite-backed DB helpers used by the in-process runner.

This module intentionally avoids SQLAlchemy so the test runner can run in
restricted environments. It exposes the minimal surface the handlers and
benchmarks need: schema creation and a connection/session wrapper that
records executed SQL for instrumentation.
"""
import sqlite3
import threading
from typing import Any, List

DB_PATH = "./db.sqlite"

_schema = [
    "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT);",
    "CREATE TABLE IF NOT EXISTS followers (follower_id INTEGER, followee_id INTEGER);",
    "CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);",
    "CREATE INDEX IF NOT EXISTS idx_followers_followee ON followers(followee_id);",
    "CREATE INDEX IF NOT EXISTS idx_followers_follower ON followers(follower_id);",
]

_tls = threading.local()


def init_db(path: str = DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    for s in _schema:
        conn.execute(s)
    conn.commit()
    return conn


class Session:
    """A tiny wrapper around sqlite3.Connection that records executed SQL
    statements into a thread-local list so the benchmark can attribute
    query counts and slow queries to individual requests.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def execute(self, sql: str, params: Any = None):
        if not hasattr(_tls, "queries"):
            _tls.queries = []
        cur = self._conn.execute(sql, params or ())
        # record a lightweight entry
        _tls.queries.append({"sql": sql, "params": params, "rowcount": cur.rowcount})
        return cur

    def executemany(self, sql: str, seq):
        if not hasattr(_tls, "queries"):
            _tls.queries = []
        cur = self._conn.executemany(sql, seq)
        _tls.queries.append({"sql": sql, "params": "<many>", "rowcount": cur.rowcount})
        return cur

    def fetch_queries(self) -> List[dict]:
        return getattr(_tls, "queries", [])

    def clear_queries(self):
        _tls.queries = []

    def commit(self):
        return self._conn.commit()

    def close(self):
        try:
            return self._conn.close()
        except Exception:
            pass


def get_conn(path: str = DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def make_session(path: str = DB_PATH):
    conn = get_conn(path)
    return Session(conn)
