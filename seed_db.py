from db import get_conn, execute
from faker import Faker
import random


def seed(min_users=10000, min_relationships=10000):
    con = get_conn()
    cur = con.cursor()
    print(f"Seeding {min_users} users...")
    cur.execute("DROP TABLE IF EXISTS follows")
    cur.execute("DROP TABLE IF EXISTS users")
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT)")
    cur.execute("CREATE TABLE follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower_id INTEGER, target_id INTEGER)")
    con.commit()

    fake = Faker()
    users = [(fake.user_name(),) for _ in range(min_users)]
    cur.executemany("INSERT INTO users (username) VALUES (?)", users)
    con.commit()

    user_ids = [r[0] for r in cur.execute("SELECT id FROM users").fetchall()]

    print(f"Seeding {min_relationships} follower relationships...")
    follows = []
    for _ in range(min_relationships):
        a = random.choice(user_ids)
        b = random.choice(user_ids)
        if a == b:
            continue
        follows.append((a, b))
    cur.executemany("INSERT INTO follows (follower_id, target_id) VALUES (?, ?)", follows)
    con.commit()
    con.close()
    print("Seeding complete.")

if __name__ == '__main__':
    seed()
