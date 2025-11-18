from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin

class DecisionLog(Base, UUIDMixin, TimestampMixin):
    """Agent decision tracking for audit purposes"""
    __tablename__ = "decision_logs"
    __table_args__ = {"comment": "Agent decision audit log"}
    
    # Foreign keys
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    
    # Decision data
    agent_name = Column(String(100), nullable=False, comment="Agent identifier")
    prompt_hash = Column(String(64), nullable=True, comment="SHA256 hash of prompt")
    decision = Column(
        JSONB, 
        nullable=False, 
        comment="Decision data: choice, reason, alternatives"
    )
    sources = Column(
        JSONB, 
        nullable=True, 
        comment="Information sources with relevance scores"
    )
    
    # Relationships
    session = relationship("Session", back_populates="decision_logs")