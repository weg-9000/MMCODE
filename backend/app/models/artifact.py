from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin

class Artifact(Base, UUIDMixin, TimestampMixin):
    """Generated artifacts from agent analysis"""
    __tablename__ = "artifacts"
    __table_args__ = {"comment": "Generated artifacts"}
    
    # Foreign keys
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    
    # Artifact data
    type = Column(
        String(50), 
        nullable=False, 
        comment="Artifact type: analysis, architecture, stack, openapi, erd, context"
    )
    content = Column(JSONB, nullable=False, comment="Artifact content as JSON")
    quality_score = Column(JSONB, nullable=True, comment="Quality metrics: completeness, relevance")
    
    # Relationships
    session = relationship("Session", back_populates="artifacts")