from models import execute, get_request_metrics

# Baseline implementation (intentionally suboptimal):
# - /api/users performs an additional COUNT(*) per user (N+1 style) to fetch follower_count
# - /api/users/<id>/followers fetches follower rows, then for each follower does an extra query to get user details

AUTH_TOKEN = "test-token"

class HTTPError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body


def _check_auth(headers):
    auth = headers.get("Authorization") or headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPError(401, {"error": "unauthorized"})
    token = auth.split(" ", 1)[1]
    if token != AUTH_TOKEN:
        raise HTTPError(403, {"error": "forbidden"})


def get_users(headers, query):
    """Optimized: fetch users and follower counts in a single set-based query (no N+1)."""
    _check_auth(headers)
    page = int(query.get("page", 1))
    per_page = int(query.get("per_page", 100))
    offset = (page - 1) * per_page

    users = execute(
        """
        SELECT u.id, u.username, u.bio, COALESCE(f.cnt, 0) AS follower_count
        FROM users u
        LEFT JOIN (
            SELECT followee_id, COUNT(1) AS cnt FROM followers GROUP BY followee_id
        ) f ON u.id = f.followee_id
        ORDER BY u.id
        LIMIT ? OFFSET ?
        """,
        (per_page, offset),
        fetchall=True,
    )

    out = [{"id": u["id"], "username": u["username"], "bio": u["bio"], "follower_count": u["follower_count"]} for u in users]
    return {"status": 200, "body": {"page": page, "per_page": per_page, "items": out}}


def get_user_followers(headers, path_params, query):
    """Optimized: fetch follower profiles with a single JOIN query (no per-row lookups)."""
    _check_auth(headers)
    user_id = int(path_params.get("user_id"))
    page = int(query.get("page", 1))
    per_page = int(query.get("per_page", 100))
    offset = (page - 1) * per_page

    rows = execute(
        """
        SELECT u.id, u.username, u.bio
        FROM followers f
        JOIN users u ON f.follower_id = u.id
        WHERE f.followee_id = ?
        ORDER BY f.follower_id
        LIMIT ? OFFSET ?
        """,
        (user_id, per_page, offset),
        fetchall=True,
    )

    items = [{"id": r["id"], "username": r["username"], "bio": r["bio"]} for r in rows]
    return {"status": 200, "body": {"page": page, "per_page": per_page, "items": items}}
