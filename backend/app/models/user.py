from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin

class User(Base, UUIDMixin, TimestampMixin):
    """User model for authentication and profiles"""
    __tablename__ = "users"
    __table_args__ = {"comment": "User information"}
    
    # Basic information
    email = Column(String(255), unique=True, nullable=False, index=True, comment="User email")
    name = Column(String(100), nullable=False, comment="Display name")
    
    # Profile
    profile_image_url = Column(Text, nullable=True, comment="Profile image URL")
    
    # GitHub integration
    github_username = Column(String(100), nullable=True, comment="GitHub username")
    github_access_token = Column(Text, nullable=True, comment="GitHub access token")
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, comment="Active status")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="Soft delete flag")
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")