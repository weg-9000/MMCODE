"""
Core database models for MMCODE DevStrategist AI
SQLAlchemy models for sessions, tasks, agents, and artifacts
"""

from sqlalchemy import Column, String, DateTime, Text, JSON, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.db.session import Base


class Session(Base):
    """User session model for requirement analysis workflows"""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    requirements_text = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, completed, archived
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tasks = relationship("Task", back_populates="session", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(id='{self.id}', title='{self.title}', status='{self.status}')>"


class Agent(Base):
    """Agent registry model"""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)  # agent-id like 'requirement-analyzer'
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)  # orchestrator, architect, tech_lead, technical_writer
    description = Column(Text, nullable=True)
    endpoint_url = Column(String(500), nullable=True)
    capabilities = Column(JSON, nullable=True)  # List of capabilities
    status = Column(String(50), default="active")  # active, inactive, maintenance
    version = Column(String(50), default="1.0.0")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="agent")

    def __repr__(self):
        return f"<Agent(id='{self.id}', name='{self.name}', status='{self.status}')>"


class Task(Base):
    """Task execution model for A2A communication"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    
    # Task details
    task_type = Column(String(100), nullable=False)  # requirement_analysis, architecture_design
    priority = Column(String(20), default="medium")  # high, medium, low
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    
    # Task data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time = Column(Float, nullable=True)  # seconds
    
    # Quality assessment
    quality_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="tasks")
    agent = relationship("Agent", back_populates="tasks")
    artifacts = relationship("Artifact", back_populates="task")

    def __repr__(self):
        return f"<Task(id='{self.id}', type='{self.task_type}', status='{self.status}')>"


class Artifact(Base):
    """Artifact model for storing agent outputs"""
    __tablename__ = "artifacts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    
    # Artifact details
    artifact_type = Column(String(100), nullable=False)  # analysis_result, architecture_design, stack_recommendation
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Content
    content = Column(JSON, nullable=False)  # The actual artifact data
    content_format = Column(String(50), default="json")  # json, markdown, html
    file_path = Column(String(500), nullable=True)  # if stored as file
    
    # Metadata
    quality_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    version = Column(String(20), default="1.0")
    created_by = Column(String(100), nullable=True)  # agent_id
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Flags
    is_final = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    
    # Relationships  
    session = relationship("Session", back_populates="artifacts")
    task = relationship("Task", back_populates="artifacts")

    def __repr__(self):
        return f"<Artifact(id='{self.id}', type='{self.artifact_type}', title='{self.title}')>"


class KnowledgeEntry(Base):
    """Knowledge base entry for RAG system"""
    __tablename__ = "knowledge_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text")  # text, code, markdown
    source_url = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags
    
    # Vector search metadata
    embedding_vector = Column(JSON, nullable=True)  # Store as JSON for now
    chunk_size = Column(Float, nullable=True)
    
    # Quality and relevance
    relevance_score = Column(Float, default=0.0)
    usage_count = Column(Float, default=0)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<KnowledgeEntry(id='{self.id}', title='{self.title}', category='{self.category}')>"