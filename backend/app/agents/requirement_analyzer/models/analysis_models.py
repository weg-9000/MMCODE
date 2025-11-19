"""Analysis Data Models for Requirement Analyzer"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum


class Priority(Enum):
    """Priority levels"""
    HIGH = "high"
    MEDIUM = "medium" 
    LOW = "low"


class RequirementType(Enum):
    """Technology requirement types"""
    REQUIRED = "required"
    PREFERRED = "preferred"
    MENTIONED = "mentioned"


class ConstraintType(Enum):
    """Constraint categories"""
    BUDGET = "budget"
    TIME = "time"
    PLATFORM = "platform"
    COMPLIANCE = "compliance"
    TECHNICAL = "technical"
    BUSINESS = "business"


@dataclass
class Entity:
    """Business entity or data model"""
    name: str
    description: str
    attributes: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "attributes": self.attributes,
            "relationships": self.relationships,
            "priority": self.priority.value
        }


@dataclass 
class UseCase:
    """Functional requirement or use case"""
    name: str
    description: str
    actors: List[str] = field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "actors": self.actors,
            "priority": self.priority.value,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions
        }


@dataclass
class QualityAttribute:
    """Non-functional requirement"""
    name: str  # performance, security, usability, etc.
    requirement: str
    measurable: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "requirement": self.requirement,
            "measurable": self.measurable,
            "priority": self.priority.value
        }


@dataclass
class TechnicalContext:
    """Technical context or stack mention"""
    technology: str
    context: str
    requirement_type: RequirementType
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "technology": self.technology,
            "context": self.context,
            "requirement_type": self.requirement_type.value,
            "version": self.version
        }


@dataclass
class Constraint:
    """Project constraint or limitation"""
    type: ConstraintType
    description: str
    impact: str = ""
    severity: Priority = Priority.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "description": self.description,
            "impact": self.impact,
            "severity": self.severity.value
        }


@dataclass
class AmbiguousItem:
    """Unclear or incomplete requirement"""
    text: str
    question: str
    impact: str
    priority: Priority = Priority.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "question": self.question,
            "impact": self.impact,
            "priority": self.priority.value
        }


@dataclass
class AnalysisResult:
    """Complete requirement analysis result"""
    entities: List[Union[Entity, Dict[str, Any]]]
    use_cases: List[Union[UseCase, Dict[str, Any]]]
    quality_attributes: List[Union[QualityAttribute, Dict[str, Any]]]
    technical_context: List[Union[TechnicalContext, Dict[str, Any]]]
    constraints: List[Union[Constraint, Dict[str, Any]]]
    ambiguous_items: List[Union[AmbiguousItem, Dict[str, Any]]]
    complexity_score: float  # 0.0 to 1.0
    domain: str  # web, mobile, desktop, ai, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.entities],
            "use_cases": [uc.to_dict() if hasattr(uc, 'to_dict') else uc for uc in self.use_cases],
            "quality_attributes": [qa.to_dict() if hasattr(qa, 'to_dict') else qa for qa in self.quality_attributes],
            "technical_context": [tc.to_dict() if hasattr(tc, 'to_dict') else tc for tc in self.technical_context],
            "constraints": [c.to_dict() if hasattr(c, 'to_dict') else c for c in self.constraints],
            "ambiguous_items": [ai.to_dict() if hasattr(ai, 'to_dict') else ai for ai in self.ambiguous_items],
            "complexity_score": self.complexity_score,
            "domain": self.domain,
            "metadata": self.metadata
        }


# Coordination and Task Models

class TaskType(Enum):
    """A2A Task types for agent coordination"""
    ARCHITECTURE_DESIGN = "architecture_design"
    STACK_RECOMMENDATION = "stack_recommendation" 
    DOCUMENT_GENERATION = "document_generation"
    QUALITY_EVALUATION = "quality_evaluation"


class AgentRole(Enum):
    """Agent roles in coordination"""
    ORCHESTRATOR = "orchestrator"
    ANALYZER = "analyzer"
    ARCHITECT = "architect" 
    RECOMMENDER = "recommender"
    DOCUMENTER = "documenter"


@dataclass
class AgentTask:
    """Task assigned to an agent"""
    task_id: str
    task_type: TaskType
    agent_role: AgentRole
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    estimated_duration: int = 60  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "agent_role": self.agent_role.value,
            "dependencies": self.dependencies,
            "context": self.context,
            "priority": self.priority.value,
            "estimated_duration": self.estimated_duration
        }


@dataclass
class CoordinationPlan:
    """Plan for coordinating multiple agents"""
    plan_id: str
    tasks: List[AgentTask] = field(default_factory=list)
    execution_order: List[List[str]] = field(default_factory=list)  # Parallel execution groups
    total_estimated_duration: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "tasks": [task.to_dict() for task in self.tasks],
            "execution_order": self.execution_order,
            "total_estimated_duration": self.total_estimated_duration,
            "created_at": self.created_at.isoformat()
        }


@dataclass 
class OrchestrationResult:
    """Result of agent orchestration"""
    plan_id: str
    executed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    total_execution_time: float = 0.0
    overall_quality_score: float = 0.0
    status: str = "unknown"  # completed, partial, failed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "executed_tasks": self.executed_tasks,
            "failed_tasks": self.failed_tasks,
            "artifacts": self.artifacts,
            "total_execution_time": self.total_execution_time,
            "overall_quality_score": self.overall_quality_score,
            "status": self.status
        }