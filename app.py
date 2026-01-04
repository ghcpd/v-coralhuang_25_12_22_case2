"""
Application with SQLAlchemy database initialization and models.
"""
import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Configure database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'api_perf.db')
DATABASE_URI = f'sqlite:///{db_path}'

# Create database engine
engine = create_engine(
    DATABASE_URI,
    echo=False,
    connect_args={'check_same_thread': False}
)

# Create session factory
Session = sessionmaker(bind=engine, expire_on_commit=False)

# Base for models
Base = declarative_base()

def get_session():
    """Get a new database session."""
    return Session()

def create_all():
    """Create all tables."""
    Base.metadata.create_all(engine)

def drop_all():
    """Drop all tables."""
    Base.metadata.drop_all(engine)

# App reference (for compatibility)
class AppMock:
    pass

app = AppMock()
