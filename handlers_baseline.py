"""Baseline (intentionally suboptimal) handler implementations.

Characteristics that make it slow under load:
- get_users: performs a full table load then slices in Python (memory + CPU).
- get_user_followers: N+1 pattern — first fetch follower ids then issues one query
  per follower to load the User row.
- Both endpoints run a separate COUNT() query before fetching rows.

These behaviors are realistic mistakes often seen in apps and are easy to
measure and fix.
"""
from time import monotonic
from typing import Dict, Any


def _auth_check(token: str) -> bool:
    return token == "test-token"


def get_users(db_session, token: str, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
    """Baseline (inefficient): full-table load then slice in Python.

    This simulates a common anti-pattern where pagination is implemented by
    loading all rows and slicing in application code.
    """
    if not _auth_check(token):
        return {"status": 401, "body": {"detail": "unauthorized"}}

    start = monotonic()

    total = db_session.execute("SELECT COUNT(1) FROM users").fetchone()[0]

    # BAD: load entire table into memory then slice
    all_users = db_session.execute("SELECT id, username FROM users ORDER BY id").fetchall()
    page_items = all_users[(page - 1) * per_page : page * per_page]

    body = {
        "items": [{"id": r[0], "username": r[1]} for r in page_items],
        "page": page,
        "per_page": per_page,
        "total": total,
    }
    return {"status": 200, "body": body, "t": (monotonic() - start) * 1000}


def get_user_followers(db_session, token: str, user_id: int, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
    """Baseline: N+1 — fetch follower ids then query each user row separately."""
    if not _auth_check(token):
        return {"status": 401, "body": {"detail": "unauthorized"}}

    start = monotonic()

    total = db_session.execute("SELECT COUNT(1) FROM followers WHERE followee_id = ?", (user_id,)).fetchone()[0]

    follower_ids = [r[0] for r in db_session.execute("SELECT follower_id FROM followers WHERE followee_id = ? ORDER BY follower_id", (user_id,)).fetchall()]

    followers = []
    for fid in follower_ids[(page - 1) * per_page : page * per_page]:
        row = db_session.execute("SELECT id, username FROM users WHERE id = ?", (fid,)).fetchone()
        followers.append({"id": row[0], "username": row[1]})

    body = {"items": followers, "page": page, "per_page": per_page, "total": total}
    return {"status": 200, "body": body, "t": (monotonic() - start) * 1000}
