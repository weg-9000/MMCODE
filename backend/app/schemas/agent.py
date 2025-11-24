"""
Pydantic schemas for agent-related API operations
Request/Response models for agent management and communication
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class AgentCapability(str, Enum):
    """Agent capability enumeration"""
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    ARCHITECTURE_DESIGN = "architecture_design"
    STACK_RECOMMENDATION = "stack_recommendation"
    DOCUMENTATION = "documentation_generation"
    TASK_ORCHESTRATION = "task_orchestration"
    PATTERN_MATCHING = "pattern_matching"
    QUALITY_ASSESSMENT = "quality_assessment"


# Agent schemas
class AgentBase(BaseModel):
    """Base agent schema"""
    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Agent display name")
    description: Optional[str] = Field(None, description="Agent description")
    endpoint_url: Optional[str] = Field(None, description="Agent endpoint URL")
    version: str = Field(default="1.0.0", description="Agent version")


class AgentCreate(AgentBase):
    """Schema for registering a new agent"""
    capabilities: List[str] = Field(default_factory=list, description="List of agent capabilities")
    status: AgentStatus = Field(default=AgentStatus.ACTIVE)


class AgentUpdate(BaseModel):
    """Schema for updating agent information"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    endpoint_url: Optional[str] = None
    capabilities: Optional[List[str]] = None
    status: Optional[AgentStatus] = None


class AgentResponse(AgentBase):
    """Schema for agent response"""
    model_config = ConfigDict(from_attributes=True)
    
    status: AgentStatus
    capabilities: List[str] = Field(default_factory=list)
    created_at: datetime
    last_seen: Optional[datetime] = None
    
    # Optional task history
    recent_tasks: Optional[List[Dict[str, Any]]] = None


class AgentCard(BaseModel):
    """Agent card for A2A discovery"""
    agent_id: str
    name: str
    description: str
    endpoint_url: str
    version: str
    capabilities: List[str]
    authentication: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Shared enums
class Priority(str, Enum):
    """Task priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRequest(BaseModel):
    """Request schema for creating agent tasks"""
    session_id: str
    task_type: str
    context: Dict[str, Any]
    priority: Optional[Priority] = Priority.MEDIUM
    timeout: Optional[int] = Field(300, description="Task timeout in seconds")


class TaskResponse(BaseModel):
    """Response schema for task creation"""
    task_id: str
    agent_id: str
    status: TaskStatus
    created_at: datetime
    estimated_completion: Optional[datetime] = None


class AgentHealthCheck(BaseModel):
    """Schema for agent health check response"""
    agent_id: str
    status: AgentStatus
    endpoint_reachable: bool
    last_response_time: Optional[float] = None
    capabilities_verified: bool = False
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Agent communication schemas (A2A)
class A2ATaskRequest(BaseModel):
    """Schema for A2A task requests"""
    task_type: str = Field(..., description="Type of task to execute")
    context: Dict[str, Any] = Field(..., description="Task context and input data")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    priority: str = Field(default="medium", description="Task priority")
    timeout: Optional[int] = Field(None, description="Task timeout in seconds")


class A2ATaskResponse(BaseModel):
    """Schema for A2A task responses"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    artifact: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None
    quality_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class AgentCapabilitiesResponse(BaseModel):
    """Schema for agent capabilities inquiry response"""
    agent_id: str
    agent_name: str
    capabilities: List[str]
    supported_task_types: List[str] = Field(default_factory=list)
    configuration: Optional[Dict[str, Any]] = None
    version: str
    status: AgentStatus


# Agent registry schemas
class AgentRegistryEntry(BaseModel):
    """Schema for agent registry entries"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    endpoint_url: str
    capabilities: List[str]
    status: AgentStatus
    version: str
    last_seen: Optional[datetime] = None
    health_score: Optional[float] = None


class AgentDiscoveryResponse(BaseModel):
    """Schema for agent discovery API response"""
    total_agents: int
    active_agents: int
    agents: List[AgentRegistryEntry]
    capabilities_summary: Dict[str, int] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# LLM Provider schemas
class LLMProviderInfo(BaseModel):
    """Schema for LLM provider information"""
    provider: str
    model: str
    api_key_valid: bool
    initialized: bool
    supported_models: List[str] = Field(default_factory=list)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class LLMProviderResponse(BaseModel):
    """Schema for LLM provider status response"""
    current_provider: LLMProviderInfo
    available_providers: List[str] = Field(default_factory=list)
    auto_detected: bool = False
    configuration_valid: bool = True
    error_message: Optional[str] = None


# Agent metrics and monitoring schemas
class AgentMetrics(BaseModel):
    """Schema for agent performance metrics"""
    agent_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0
    average_processing_time: Optional[float] = None
    average_quality_score: Optional[float] = None
    last_activity: Optional[datetime] = None


class SystemMetrics(BaseModel):
    """Schema for overall system metrics"""
    total_sessions: int = 0
    active_sessions: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    active_agents: int = 0
    system_uptime: Optional[float] = None
    average_session_duration: Optional[float] = None
    agent_metrics: List[AgentMetrics] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)