"""
Database seeding script to populate with 10k+ users and 10k+ follower relationships.
"""
from app import engine, Session, create_all, drop_all
from models import User, Follower
import random

def seed_database():
    """Seed the database with users and follower relationships."""
    # Drop and recreate tables
    drop_all()
    create_all()
    
    session = Session()
    
    print("Creating 10000 users...")
    users = []
    for i in range(1, 10001):
        user = User(
            username=f'user_{i}',
            email=f'user_{i}@example.com'
        )
        users.append(user)
        if i % 1000 == 0:
            print(f"  Created {i} users...")
    
    session.add_all(users)
    session.commit()
    print("Users created and committed.")
    
    print("\nCreating 10000+ follower relationships...")
    followers = []
    follower_count = 0
    batch_size = 500
    
    # Create follower relationships: each user can have multiple followers
    for user_id in range(1, 10001):
        # Each user gets 1-2 followers (creates ~10k-20k relationships)
        num_followers = random.randint(1, 2)
        follower_ids = random.sample(
            [uid for uid in range(1, 10001) if uid != user_id],
            num_followers
        )
        
        for follower_id in follower_ids:
            follower = Follower(
                user_id=user_id,
                follower_id=follower_id
            )
            followers.append(follower)
            follower_count += 1
            
            # Batch commit
            if len(followers) >= batch_size:
                session.add_all(followers)
                session.commit()
                followers = []
        
        if user_id % 1000 == 0:
            print(f"  Processed {user_id} users, {follower_count} relationships...")
    
    # Final batch
    if followers:
        session.add_all(followers)
        session.commit()
    
    print(f"Follower relationships created: {follower_count}")
    
    # Verify
    user_count = session.query(User).count()
    follower_count = session.query(Follower).count()
    
    print("\nDatabase seeding complete!")
    print(f"Total users: {user_count}")
    print(f"Total follower relationships: {follower_count}")
    
    session.close()

if __name__ == '__main__':
    seed_database()
