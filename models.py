"""
SQLAlchemy models for the API.
"""
from app import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from datetime import datetime

class User(Base):
    """User model with pagination support."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_users_id', 'id'),
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class Follower(Base):
    """Follower relationship model."""
    __tablename__ = 'followers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    follower_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'follower_id', name='uq_user_follower'),
        Index('idx_followers_user_id', 'user_id'),
        Index('idx_followers_follower_id', 'follower_id'),
        Index('idx_followers_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'follower_id': self.follower_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
