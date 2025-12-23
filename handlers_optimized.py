"""Optimized handler implementations.

Key improvements:
- use LIMIT/OFFSET to avoid loading entire tables into memory
- eliminate N+1 by using a single join to fetch follower User rows
- keep a single COUNT() when total is required but avoid extra per-item queries
"""
from time import monotonic
from typing import Dict, Any


def _auth_check(token: str) -> bool:
    return token == "test-token"


def get_users(db_session, token: str, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
    if not _auth_check(token):
        return {"status": 401, "body": {"detail": "unauthorized"}}

    start = monotonic()

    offset = (page - 1) * per_page
    rows = db_session.execute("SELECT id, username FROM users ORDER BY id LIMIT ? OFFSET ?", (per_page, offset)).fetchall()
    total = db_session.execute("SELECT COUNT(1) FROM users").fetchone()[0]

    body = {"items": [{"id": r[0], "username": r[1]} for r in rows], "page": page, "per_page": per_page, "total": total}
    return {"status": 200, "body": body, "t": (monotonic() - start) * 1000}


def get_user_followers(db_session, token: str, user_id: int, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
    if not _auth_check(token):
        return {"status": 401, "body": {"detail": "unauthorized"}}

    start = monotonic()
    offset = (page - 1) * per_page

    rows = db_session.execute(
        "SELECT u.id, u.username FROM followers f JOIN users u ON f.follower_id = u.id WHERE f.followee_id = ? ORDER BY f.follower_id LIMIT ? OFFSET ?",
        (user_id, per_page, offset),
    ).fetchall()

    total = db_session.execute("SELECT COUNT(1) FROM followers WHERE followee_id = ?", (user_id,)).fetchone()[0]
    body = {"items": [{"id": r[0], "username": r[1]} for r in rows], "page": page, "per_page": per_page, "total": total}
    return {"status": 200, "body": body, "t": (monotonic() - start) * 1000}
