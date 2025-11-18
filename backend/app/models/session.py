from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin

class Session(Base, UUIDMixin, TimestampMixin):
    """Analysis session model"""
    __tablename__ = "sessions"
    __table_args__ = {"comment": "Analysis sessions"}
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Session data
    requirements = Column(Text, nullable=False, comment="User requirements input")
    status = Column(
        String(20), 
        default="draft", 
        nullable=False, 
        comment="Session status: draft, analyzing, completed, failed"
    )
    version = Column(Integer, default=1, nullable=False, comment="Session version")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="Completion timestamp")
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    artifacts = relationship("Artifact", back_populates="session", cascade="all, delete-orphan")
    decision_logs = relationship("DecisionLog", back_populates="session", cascade="all, delete-orphan")