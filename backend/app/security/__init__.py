"""
MMCODE Security Platform - Security Module
==========================================

Core security components for AI-powered penetration testing platform.

Exports:
    - Security models (EngagementScope, SecurityAction, ValidationResult, etc.)
    - Scope enforcement engine
    - Audit logging system
    - Security utilities

Version: 2.0.0
"""

from .models import (
    # Core enums
    PentestPhase,
    EngagementType,
    RiskLevel,
    SeverityLevel,
    ActionStatus,
    
    # Data models
    TimeWindow,
    EngagementScope,
    SecurityAction,
    LayerResult,
    ValidationResult,
    HumanApproval,
    SecurityFinding,
    TaskNode,
    SecurityContext,
    
    # Utility functions
    generate_action_id,
    generate_finding_id,
    generate_task_id,
)

from .scope_enforcer import (
    ScopeEnforcementEngine,
    ScopeViolationError,
    create_scope_enforcer,
)

from .audit_logger import (
    SecurityAuditLogger,
    AuditEventType,
    AuditEvent,
    create_audit_logger,
)

# Approval workflow components
from .approval_workflow import (
    ApprovalWorkflow,
    RiskEvaluator,
    ApprovalConfiguration,
    ApprovalRequest,
    ApprovalResult,
    RiskAssessment,
)

from .notifications import (
    NotificationManager,
    NotificationConfig,
    NotificationChannel,
)

from .approval_integration import (
    ApprovalIntegrationManager,
    SecurityToolWrapper,
)

__all__ = [
    # Enums
    "PentestPhase",
    "EngagementType", 
    "RiskLevel",
    "SeverityLevel",
    "ActionStatus",
    
    # Models
    "TimeWindow",
    "EngagementScope",
    "SecurityAction",
    "LayerResult",
    "ValidationResult",
    "HumanApproval",
    "SecurityFinding",
    "TaskNode",
    "SecurityContext",
    
    # Core engines
    "ScopeEnforcementEngine",
    "ScopeViolationError",
    "SecurityAuditLogger",
    "AuditEventType",
    "AuditEvent",
    
    # Factories
    "create_scope_enforcer",
    "create_audit_logger",
    
    # Approval workflow
    "ApprovalWorkflow",
    "RiskEvaluator", 
    "ApprovalConfiguration",
    "ApprovalRequest",
    "ApprovalResult",
    "RiskAssessment",
    "NotificationManager",
    "NotificationConfig",
    "NotificationChannel",
    "ApprovalIntegrationManager",
    "SecurityToolWrapper",
    
    # Utilities
    "generate_action_id",
    "generate_finding_id", 
    "generate_task_id",
]

# Version info
__version__ = "2.0.0"
__author__ = "MMCODE Security Team"