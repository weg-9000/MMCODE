"""
A2A Task models for agent communication.
Defines standard A2A protocol structures for task handling.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(str, Enum):
    """A2A Task execution status"""
    SUBMITTED = "submitted"
    WORKING = "working" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AgentSkill(BaseModel):
    """Agent capability definition"""
    id: str = Field(..., description="Skill identifier")
    description: str = Field(..., description="Skill description")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="Input data schema")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="Output data schema")


class AgentCard(BaseModel):
    """A2A Agent Card specification"""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    url: str = Field(..., description="Agent endpoint URL")
    version: str = Field(default="1.0.0", description="Agent version")
    skills: List[AgentSkill] = Field(..., description="Agent capabilities")
    authentication: Dict[str, str] = Field(default_factory=dict, description="Auth requirements")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TaskContext(BaseModel):
    """Task execution context and input data"""
    session_id: str = Field(..., description="Parent session ID")
    architecture: Optional[Dict[str, Any]] = Field(None, description="Architecture context from previous agent")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Original requirements")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Execution constraints")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")


class TaskProgress(BaseModel):
    """Task execution progress tracking"""
    percentage: float = Field(0.0, ge=0.0, le=100.0, description="Completion percentage")
    current_step: str = Field("", description="Current processing step")
    steps_completed: List[str] = Field(default_factory=list, description="Completed steps")
    estimated_remaining: Optional[int] = Field(None, description="Estimated seconds remaining")


class TaskError(BaseModel):
    """Task execution error details"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    recoverable: bool = Field(False, description="Whether error is recoverable")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")


class TaskArtifact(BaseModel):
    """A2A Task artifact output"""
    type: str = Field(..., description="Artifact type")
    content: Dict[str, Any] = Field(..., description="Artifact content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Artifact metadata")
    format: str = Field(default="json", description="Content format")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict()


class A2ATask(BaseModel):
    """A2A Task specification"""
    id: str = Field(..., description="Unique task ID")
    agent_name: str = Field(..., description="Target agent name")
    skill_id: str = Field(..., description="Required skill ID")
    context: TaskContext = Field(..., description="Task context")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    timeout: Optional[int] = Field(300, description="Timeout in seconds")
    retry_count: int = Field(default=0, description="Current retry count")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(..., description="Creator agent/user ID")
    
    model_config = ConfigDict()


class A2ATaskUpdate(BaseModel):
    """A2A Task status update"""
    task_id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Current status")
    progress: Optional[TaskProgress] = Field(None, description="Progress information")
    error: Optional[TaskError] = Field(None, description="Error information if failed")
    message: Optional[str] = Field(None, description="Status message")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict()


class A2ATaskResult(BaseModel):
    """A2A Task completion result"""
    task_id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Final status")
    artifacts: List[TaskArtifact] = Field(default_factory=list, description="Generated artifacts")
    execution_time: float = Field(..., description="Execution time in seconds")
    resource_usage: Optional[Dict[str, float]] = Field(None, description="Resource consumption metrics")
    quality_metrics: Optional[Dict[str, float]] = Field(None, description="Quality assessment")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict()


class StackRecommendationRequest(BaseModel):
    """Stack recommendation task request"""
    session_id: str = Field(..., description="Session identifier")
    architecture_context: Dict[str, Any] = Field(..., description="Architecture information")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Original requirements")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Technical constraints")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    
    class Meta:
        skill_id = "stack-recommendation"
        task_type = "stack_analysis"