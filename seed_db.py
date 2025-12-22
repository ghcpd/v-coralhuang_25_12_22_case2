from models import Session, User, Follow, engine, Base
import random

def seed_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = Session()

    # Create 10000 users
    users = []
    for i in range(1, 10001):
        user = User(id=i, name=f'User{i}')
        users.append(user)
    session.add_all(users)
    session.commit()

    # Create 10000 follows
    follows = []
    for i in range(10000):
        follower_id = random.randint(1, 10000)
        followee_id = random.randint(1, 10000)
        if follower_id != followee_id:
            follow = Follow(follower_id=follower_id, followee_id=followee_id)
            follows.append(follow)
    session.add_all(follows)
    session.commit()

    session.close()
    print("Database seeded with 10000 users and 10000 follows.")

if __name__ == '__main__':
    seed_database()