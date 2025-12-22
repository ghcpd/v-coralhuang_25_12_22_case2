from sqlalchemy import Column, Integer, String, ForeignKey, Table, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), index=True)

    followers = relationship("Follow", back_populates="target_user", lazy="select")

class Follow(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer, ForeignKey("users.id"), index=True)
    target_id = Column(Integer, ForeignKey("users.id"), index=True)

    follower = relationship("User", foreign_keys=[follower_id])
    target_user = relationship("User", foreign_keys=[target_id], back_populates="followers")

# Index to speed up follower lookups
Index("ix_follows_target_id", Follow.target_id)
Index("ix_follows_follower_id", Follow.follower_id)
