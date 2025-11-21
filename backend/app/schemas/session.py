"""
Pydantic schemas for session-related API operations
Request/Response models for session management
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Priority(str, Enum):
    """Task priority enumeration"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Session schemas
class SessionBase(BaseModel):
    """Base session schema"""
    title: str = Field(..., min_length=1, max_length=255, description="Session title")
    description: Optional[str] = Field(None, description="Session description")
    requirements_text: Optional[str] = Field(None, description="Raw requirements text")


class SessionCreate(SessionBase):
    """Schema for creating a new session"""
    pass


class SessionUpdate(BaseModel):
    """Schema for updating a session"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    requirements_text: Optional[str] = None
    status: Optional[SessionStatus] = None


class SessionResponse(SessionBase):
    """Schema for session response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    
    # Optional related data
    tasks: Optional[List["TaskSummary"]] = None
    artifacts: Optional[List["ArtifactSummary"]] = None


# Task schemas
class TaskBase(BaseModel):
    """Base task schema"""
    task_type: str = Field(..., description="Type of task to execute")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Task input data")


class TaskCreate(TaskBase):
    """Schema for creating a new task"""
    agent_id: str = Field(..., description="Target agent ID")


class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class TaskResponse(TaskBase):
    """Schema for task response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    session_id: str
    agent_id: str
    status: TaskStatus
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # Timing
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None
    
    # Quality metrics
    quality_score: Optional[float] = None
    confidence_score: Optional[float] = None


class TaskSummary(BaseModel):
    """Lightweight task summary for session responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    task_type: str
    agent_id: str
    status: TaskStatus
    priority: Priority
    created_at: datetime
    quality_score: Optional[float] = None


# Artifact schemas
class ArtifactBase(BaseModel):
    """Base artifact schema"""
    artifact_type: str = Field(..., description="Type of artifact")
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    content_format: str = Field(default="json", description="Content format")


class ArtifactCreate(ArtifactBase):
    """Schema for creating an artifact"""
    content: Dict[str, Any] = Field(..., description="Artifact content")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_by: Optional[str] = Field(None, description="Creator agent ID")


class ArtifactResponse(ArtifactBase):
    """Schema for artifact response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    session_id: str
    task_id: Optional[str] = None
    content: Dict[str, Any]
    
    # Metadata
    quality_score: Optional[float] = None
    confidence_score: Optional[float] = None
    version: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Flags
    is_final: bool
    is_public: bool


class ArtifactSummary(BaseModel):
    """Lightweight artifact summary"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    artifact_type: str
    title: str
    quality_score: Optional[float] = None
    created_at: datetime
    is_final: bool


# Analysis request schemas
class RequirementAnalysisRequest(BaseModel):
    """Request schema for requirement analysis"""
    requirements: str = Field(..., min_length=10, description="Requirements text to analyze")
    session_id: Optional[str] = Field(None, description="Optional session ID")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Analysis options")


class AnalysisResponse(BaseModel):
    """Response schema for analysis results"""
    session_id: str
    task_id: str
    status: TaskStatus
    analysis_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None
    quality_score: Optional[float] = None


# Agent orchestration schemas
class OrchestrationRequest(BaseModel):
    """Request schema for full agent orchestration"""
    requirements: str = Field(..., min_length=10)
    session_title: Optional[str] = Field(None, description="Session title")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class OrchestrationResponse(BaseModel):
    """Response schema for orchestration results"""
    session_id: str
    status: str
    analysis: Optional[Dict[str, Any]] = None
    coordination_plan: Optional[Dict[str, Any]] = None
    orchestration_result: Optional[Dict[str, Any]] = None
    tasks: List[TaskSummary] = Field(default_factory=list)
    artifacts: List[ArtifactSummary] = Field(default_factory=list)
    total_processing_time: Optional[float] = None
    overall_quality_score: Optional[float] = None