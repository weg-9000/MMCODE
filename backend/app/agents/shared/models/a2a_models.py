"""A2A Protocol Data Models"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid
from datetime import datetime


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentFramework(Enum):
    """Supported agent frameworks"""
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    SEMANTIC_KERNEL = "semantic_kernel"
    CREWAI = "crewai"
    CUSTOM = "custom"


@dataclass
class AgentCard:
    """Agent identification and capability card"""
    agent_id: str
    agent_name: str
    framework: AgentFramework
    capabilities: List[str]
    endpoint_url: str
    version: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "framework": self.framework.value,
            "capabilities": self.capabilities,
            "endpoint_url": self.endpoint_url,
            "version": self.version,
            "metadata": self.metadata
        }


@dataclass
class A2AMessage:
    """A2A communication message"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    message_type: str = "task"
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


@dataclass
class A2ATask:
    """A2A Task definition"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    status: TaskStatus = TaskStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    assigned_agent: Optional[str] = None
    parent_task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Artifact:
    """Agent output artifact"""
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    artifact_type: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None