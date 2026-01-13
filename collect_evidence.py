"""Collect slow-query evidence by exercising the baseline handlers once
and writing the SQL statements observed.
"""
import json

import app
import handlers_baseline as baseline


def capture():
    app.init_db()
    s = app.get_session()
    s.clear_queries()
    # call the baseline list_users which intentionally does a full-table scan
    baseline.get_users(s, token="test-token", page=1, per_page=100)
    q = s.fetch_queries()
    s.clear_queries()

    # call the baseline followers which does N+1
    baseline.get_user_followers(s, token="test-token", user_id=1, page=1, per_page=100)
    q2 = s.fetch_queries()
    s.close()

    out = {
        "list_users_queries": q,
        "followers_queries": q2,
        "notes": "Queries captured from baseline handlers; durations not available with sqlite wrapper, flagged by heuristic (full-table SELECT, repeated per-row SELECT).",
    }
    open("artifacts/slow_query_log_excerpt.json", "w").write(json.dumps(out, indent=2))


if __name__ == '__main__':
    capture()
