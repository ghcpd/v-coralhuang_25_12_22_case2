from models import execute, get_request_metrics

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
    """Baseline: returns paginated users with follower_count (computed per user via separate query)."""
    _check_auth(headers)
    page = int(query.get("page", 1))
    per_page = int(query.get("per_page", 100))
    offset = (page - 1) * per_page

    users = execute(
        "SELECT id, username, bio FROM users ORDER BY id LIMIT ? OFFSET ?",
        (per_page, offset),
        fetchall=True,
    )

    # N+1: fetch follower_count per user
    out = []
    for u in users:
        row = execute(
            "SELECT COUNT(1) as cnt FROM followers WHERE followee_id = ?",
            (u["id"],),
            fetchone=True,
        )
        out.append({"id": u["id"], "username": u["username"], "bio": u["bio"], "follower_count": row["cnt"]})

    return {"status": 200, "body": {"page": page, "per_page": per_page, "items": out}}


def get_user_followers(headers, path_params, query):
    """Baseline: returns followers of a user but fetches each follower's profile separately."""
    _check_auth(headers)
    user_id = int(path_params.get("user_id"))
    page = int(query.get("page", 1))
    per_page = int(query.get("per_page", 100))
    offset = (page - 1) * per_page

    # get follower ids
    rows = execute(
        "SELECT follower_id FROM followers WHERE followee_id = ? ORDER BY follower_id LIMIT ? OFFSET ?",
        (user_id, per_page, offset),
        fetchall=True,
    )

    items = []
    for r in rows:
        # N+1: fetch each follower's user row separately
        u = execute("SELECT id, username, bio FROM users WHERE id = ?", (r["follower_id"],), fetchone=True)
        items.append({"id": u["id"], "username": u["username"], "bio": u["bio"]})

    return {"status": 200, "body": {"page": page, "per_page": per_page, "items": items}}
