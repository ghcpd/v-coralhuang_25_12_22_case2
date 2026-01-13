"""Seed the SQLite database with users and follower relationships.

Creates N users and M follower relationships. Uses bulk operations for speed.
"""
import random
import sys

from app import init_db
import models


def seed(n_users: int = 12000, n_rels: int = 20000, db_path: str = "./db.sqlite"):
    # create schema
    init_db(db_path)
    conn = models.get_conn(db_path)

    existing = conn.execute("SELECT COUNT(1) FROM users").fetchone()[0]
    if existing and existing >= n_users:
        print(f"DB already has {existing} users — skipping seed")
        return

    print(f"Seeding {n_users} users and {n_rels} follower relationships...")
    # bulk insert users
    users = [(i + 1, f"user_{i+1}") for i in range(n_users)]
    conn.executemany("INSERT INTO users(id, username) VALUES (?, ?)", users)
    conn.commit()

    # followers
    rels = []
    for i in range(n_rels):
        a = random.randint(1, n_users)
        b = random.randint(1, n_users)
        if a == b:
            continue
        rels.append((a, b))
    conn.executemany("INSERT INTO followers(follower_id, followee_id) VALUES (?, ?)", rels)
    conn.commit()
    conn.close()
    print("seeding complete")


if __name__ == "__main__":
    seed()
