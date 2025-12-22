from db import get_conn, execute, new_request_context, get_request_context

# Global toggle to switch optimized behavior
# Set to True to enable optimized query patterns by default
OPTIMIZED = True

# Authentication stub
def check_auth(token: str):
    return token == "test-token"


def get_users(page: int = 1, per_page: int = 100, auth: str = None):
    if not check_auth(auth):
        return {"status": 401, "body": {"detail": "Unauthorized"}}

    ctx = new_request_context()
    con = get_conn()
    try:
        offset = (page - 1) * per_page
        users_cur = execute(con, "SELECT id, username FROM users LIMIT ? OFFSET ?", (per_page, offset))
        users = [dict(r) for r in users_cur.fetchall()]

        body = []
        if OPTIMIZED:
            # Optimized: fetch follower counts in a single query
            user_ids = [u['id'] for u in users]
            counts = {}
            if user_ids:
                params = tuple(user_ids)
                placeholders = ','.join(['?'] * len(user_ids))
                rows = execute(con, f"SELECT target_id, COUNT(id) as cnt FROM follows WHERE target_id IN ({placeholders}) GROUP BY target_id", params).fetchall()
                counts = {r['target_id']: r['cnt'] for r in rows}
            for u in users:
                body.append({"id": u['id'], "username": u['username'], "followers": counts.get(u['id'], 0)})
        else:
            for u in users:
                c = execute(con, "SELECT COUNT(1) as cnt FROM follows WHERE target_id = ?", (u['id'],)).fetchone()[0]
                body.append({"id": u['id'], "username": u['username'], "followers": c})

        return {"status": 200, "body": {"users": body, "meta": {"page": page, "per_page": per_page}} , "_metrics": get_request_context()}
    finally:
        con.close()


def get_user_followers(user_id: int = 1, page: int = 1, per_page: int = 100, auth: str = None):
    if not check_auth(auth):
        return {"status": 401, "body": {"detail": "Unauthorized"}}

    ctx = new_request_context()
    con = get_conn()
    try:
        offset = (page - 1) * per_page
        follows_cur = execute(con, "SELECT follower_id FROM follows WHERE target_id = ? LIMIT ? OFFSET ?", (user_id, per_page, offset))
        follows = [dict(r) for r in follows_cur.fetchall()]
        followers = []
        if OPTIMIZED:
            ids = [f['follower_id'] for f in follows]
            if ids:
                placeholders = ','.join(['?'] * len(ids))
                users_cur = execute(con, f"SELECT id, username FROM users WHERE id IN ({placeholders})", tuple(ids))
                users = [dict(r) for r in users_cur.fetchall()]
                users_map = {u['id']: u for u in users}
                for f in follows:
                    u = users_map.get(f['follower_id'])
                    if u:
                        followers.append({"id": u['id'], "username": u['username']})
        else:
            for f in follows:
                u_row = execute(con, "SELECT id, username FROM users WHERE id = ?", (f['follower_id'],)).fetchone()
                if u_row:
                    followers.append({"id": u_row[0], "username": u_row[1]})

        return {"status": 200, "body": {"followers": followers, "meta": {"page": page, "per_page": per_page}}, "_metrics": get_request_context()}
    finally:
        con.close()
