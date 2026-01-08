import json
from models import Session, User, Follow

OPTIMIZED = True  # Flag to switch between baseline and optimized logic

def authenticate(headers):
    auth_header = headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False
    token = auth_header[7:]
    return token == 'test-token'

def get_users(query_params, headers):
    if not authenticate(headers):
        return {'status': 401, 'body': {'error': 'Unauthorized'}}
    
    page = int(query_params.get('page', 1))
    per_page = int(query_params.get('per_page', 100))
    offset = (page - 1) * per_page
    
    session = Session()
    try:
        # Inefficient: count total each time
        total = session.query(User).count()
        users = session.query(User).offset(offset).limit(per_page).all()
        user_list = [{'id': u.id, 'name': u.name} for u in users]
        return {
            'status': 200,
            'body': {
                'users': user_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total
                }
            }
        }
    finally:
        session.close()

def get_user_followers(path_params, query_params, headers):
    if not authenticate(headers):
        return {'status': 401, 'body': {'error': 'Unauthorized'}}
    
    user_id = int(path_params['user_id'])
    page = int(query_params.get('page', 1))
    per_page = int(query_params.get('per_page', 100))
    offset = (page - 1) * per_page
    
    session = Session()
    try:
        if OPTIMIZED:
            # Optimized: single query with join
            followers = session.query(User).join(Follow, Follow.follower_id == User.id).filter(Follow.followee_id == user_id).offset(offset).limit(per_page).all()
            follower_list = [{'id': u.id, 'name': u.name} for u in followers]
        else:
            # Inefficient: N+1 queries
            follower_ids = session.query(Follow.follower_id).filter(Follow.followee_id == user_id).offset(offset).limit(per_page).all()
            follower_ids = [fid[0] for fid in follower_ids]
            followers = []
            for fid in follower_ids:
                user = session.query(User).filter(User.id == fid).first()
                if user:
                    followers.append({'id': user.id, 'name': user.name})
            follower_list = followers
        
        # Total count
        total = session.query(Follow).filter(Follow.followee_id == user_id).count()
        
        return {
            'status': 200,
            'body': {
                'followers': follower_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total
                }
            }
        }
    finally:
        session.close()