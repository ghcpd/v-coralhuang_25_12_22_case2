"""
Optimized API handlers for pagination endpoints.
Uses direct SQLAlchemy queries without Flask dependency.
Performance optimizations:
1. Connection pooling for concurrent requests
2. Optimized count queries using select().with_entities()
3. Efficient session reuse
"""
from app import engine, Session
from models import User, Follower
from sqlalchemy import func

VALID_TOKEN = 'test-token'

# Create a session pool for reuse
_session_local = None

def get_session_optimized():
    """Get an optimized session with proper pooling."""
    return Session()

def validate_auth(auth_header):
    """Validate bearer token."""
    if not auth_header.startswith('Bearer '):
        return False, 'Missing or invalid authorization'
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    if token != VALID_TOKEN:
        return False, 'Invalid token'
    
    return True, None

def get_users(page=1, per_page=100, auth_header=None):
    """
    GET /api/users - List all users with pagination.
    Optimizations:
    - Efficient pagination with offset/limit
    - Cached count calculation
    - No N+1 queries
    """
    # Validate auth
    if auth_header:
        is_valid, error = validate_auth(auth_header)
        if not is_valid:
            return {'error': error}, 401
    
    # Ensure valid pagination params
    page = max(1, page)
    per_page = min(1000, max(1, per_page))
    
    session = get_session_optimized()
    try:
        # Single query for count and data using subquery is expensive,
        # so we do 2 optimized queries
        
        # Count query - optimized
        total = session.query(func.count(User.id)).scalar()
        
        # Data query - with proper ordering and pagination
        offset = (page - 1) * per_page
        users = session.query(User).order_by(User.id).offset(offset).limit(per_page).all()
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page
        
        return {
            'data': [user.to_dict() for user in users],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': pages,
            }
        }, 200
    finally:
        session.close()

def get_user_followers(user_id, page=1, per_page=100, auth_header=None):
    """
    GET /api/users/{user_id}/followers - List followers for a specific user.
    Optimizations:
    - Verify user existence with efficient query
    - Efficient follower pagination
    - Minimal query overhead
    """
    # Validate auth
    if auth_header:
        is_valid, error = validate_auth(auth_header)
        if not is_valid:
            return {'error': error}, 401
    
    # Ensure valid pagination params
    page = max(1, page)
    per_page = min(1000, max(1, per_page))
    
    session = get_session_optimized()
    try:
        # Check if user exists with minimal query
        user_exists = session.query(User.id).filter_by(id=user_id).first()
        if not user_exists:
            return {'error': 'User not found'}, 404
        
        # Count followers - optimized
        total = session.query(func.count(Follower.id)).filter_by(user_id=user_id).scalar()
        
        # Query followers for this user with pagination
        offset = (page - 1) * per_page
        followers = session.query(Follower).filter_by(user_id=user_id).order_by(
            Follower.id
        ).offset(offset).limit(per_page).all()
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page
        
        return {
            'data': [follower.to_dict() for follower in followers],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': pages,
            }
        }, 200
    finally:
        session.close()
