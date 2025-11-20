"""
Data models for StackRecommender agent.
"""

from .stack_models import (
    StackCategory,
    QualityAttribute, 
    TechnologyChoice,
    StackRecommendation,
    QualityScore,
    ArchitectureContext,
    StackArtifact,
    StackTemplate
)

from .task_models import (
    TaskStatus,
    TaskPriority,
    AgentSkill,
    AgentCard,
    TaskContext,
    TaskProgress,
    TaskError,
    TaskArtifact,
    A2ATask,
    A2ATaskUpdate,
    A2ATaskResult,
    StackRecommendationRequest
)

__all__ = [
    # Stack models
    "StackCategory",
    "QualityAttribute",
    "TechnologyChoice", 
    "StackRecommendation",
    "QualityScore",
    "ArchitectureContext",
    "StackArtifact",
    "StackTemplate",
    
    # Task models
    "TaskStatus",
    "TaskPriority",
    "AgentSkill",
    "AgentCard",
    "TaskContext",
    "TaskProgress", 
    "TaskError",
    "TaskArtifact",
    "A2ATask",
    "A2ATaskUpdate",
    "A2ATaskResult",
    "StackRecommendationRequest"
]