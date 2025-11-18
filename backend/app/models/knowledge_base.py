from sqlalchemy import Column, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from .base import Base, UUIDMixin

class KnowledgeBase(Base, UUIDMixin):
    """External knowledge storage for vector search"""
    __tablename__ = "knowledge_base"
    __table_args__ = {"comment": "Knowledge base for vector search"}
    
    # Content
    content = Column(Text, nullable=False, comment="Document content")
    embedding = Column(Vector(dim=1536), nullable=False, comment="OpenAI text-embedding-3-small")
    
    # Metadata
    metadata = Column(
        JSONB, 
        nullable=False, 
        comment="Metadata: url, source, license, etc."
    )
    
    # Timestamps
    scraped_at = Column(DateTime(timezone=True), nullable=False, comment="Scraping timestamp")