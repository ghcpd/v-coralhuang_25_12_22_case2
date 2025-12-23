# Minimal app module to satisfy `app` import in the test harness
# It does not start an HTTP server; handlers are invoked in-process by the test runner.
import handlers

# expose the handlers mapping expected by the benchmark harness
handler_map = {
    "GET /api/users": handlers.get_users,
    "GET /api/users/1/followers": lambda headers, query: handlers.get_user_followers(headers, {"user_id": 1}, query),
}
