import os
import random
import string
from models import execute, executemany

DB_PATH = "./test.db"


def _create_schema():
    execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            bio TEXT
        )
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS followers (
            follower_id INTEGER NOT NULL,
            followee_id INTEGER NOT NULL,
            PRIMARY KEY (follower_id, followee_id)
        )
        """
    )
    # indexes to support optimized queries
    execute("CREATE INDEX IF NOT EXISTS idx_followers_followee ON followers(followee_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_followers_follower ON followers(follower_id)")


def _random_username(i):
    return f"user_{i}"


def seed(min_users=10000, min_relationships=10000):
    # quick existence check: see if table has enough rows
    _create_schema()
    # insert users
    existing = execute("SELECT COUNT(1) as cnt FROM users", fetchone=True)
    if existing["cnt"] >= min_users and execute("SELECT COUNT(1) as cnt FROM followers", fetchone=True)["cnt"] >= min_relationships:
        print("DB already seeded")
        return

    print("Seeding users...")
    users = [(i + 1, _random_username(i + 1), f"bio for user {i+1}") for i in range(min_users)]
    executemany("INSERT OR IGNORE INTO users(id, username, bio) VALUES (?, ?, ?)", users)

    print("Seeding follower relationships...")
    rels = []
    for i in range(min_relationships):
        # create random follower -> followee pairs (avoid self-follow)
        a = random.randint(1, min_users)
        b = random.randint(1, min_users)
        if a == b:
            b = (b % min_users) + 1
        rels.append((a, b))
    executemany("INSERT OR IGNORE INTO followers(follower_id, followee_id) VALUES (?, ?)", rels)
    print("Seeding complete")


if __name__ == "__main__":
    seed()
