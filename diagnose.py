"""
Diagnostic script to identify N+1 query problems in API handlers.
"""
from app import engine, Session
from models import User, Follower
from handlers import get_users, get_user_followers
from sqlalchemy import event

# Track queries
queries_executed = []

def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    queries_executed.append(statement)

# Hook to log queries
event.listen(engine, "before_cursor_execute", before_cursor_execute)

print("="*60)
print("DIAGNOSTIC: Testing GET /api/users with page=1, per_page=100")
print("="*60)

queries_executed.clear()
response, status = get_users(page=1, per_page=100, auth_header='Bearer test-token')
print(f"Status: {status}")
print(f"Total Queries: {len(queries_executed)}")
print("\nQueries executed:")
for i, q in enumerate(queries_executed, 1):
    print(f"{i}. {q[:80]}")

print("\n" + "="*60)
print("DIAGNOSTIC: Testing GET /api/users/1/followers with page=1, per_page=100")
print("="*60)

queries_executed.clear()
response, status = get_user_followers(user_id=1, page=1, per_page=100, auth_header='Bearer test-token')
print(f"Status: {status}")
print(f"Total Queries: {len(queries_executed)}")
print("\nQueries executed:")
for i, q in enumerate(queries_executed, 1):
    print(f"{i}. {q[:80]}")

event.remove(engine, "before_cursor_execute", before_cursor_execute)
