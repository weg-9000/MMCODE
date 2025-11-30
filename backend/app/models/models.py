"""
Core database models for MMCODE DevStrategist AI
SQLAlchemy models for sessions, tasks, agents, and artifacts
"""

from sqlalchemy import Column, String, DateTime, Text, JSON, Float, ForeignKey, Boolean, Integer, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum

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


# Security Platform Models

class PentestPhaseEnum(enum.Enum):
    """Pentesting phases"""
    RECONNAISSANCE = "reconnaissance"
    SCANNING = "scanning"
    ENUMERATION = "enumeration"
    VULNERABILITY_ASSESSMENT = "vulnerability_assessment"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    REPORTING = "reporting"


class RiskLevelEnum(enum.Enum):
    """Risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SeverityLevelEnum(enum.Enum):
    """Severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EngagementScope(Base):
    """Security engagement scope definition"""
    __tablename__ = "engagement_scopes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Scope definition
    domains = Column(JSON)  # List of allowed domains
    ip_ranges = Column(JSON)  # List of allowed IP ranges
    excluded_ips = Column(JSON)  # List of excluded IPs
    allowed_ports = Column(JSON)  # List of allowed ports
    
    # Testing constraints
    testing_window_start = Column(DateTime(timezone=True))
    testing_window_end = Column(DateTime(timezone=True))
    max_concurrent_scans = Column(Integer, default=5)
    rate_limit_per_second = Column(Integer, default=10)
    
    # Authorization
    authorized_by = Column(String(255))
    authorization_document = Column(String(500))  # File path
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    pentesting_sessions = relationship("PentestingSession", back_populates="scope")

    def __repr__(self):
        return f"<EngagementScope(id='{self.id}', name='{self.engagement_name}')>"


class PentestingSession(Base):
    """Security pentesting session"""
    __tablename__ = "pentesting_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scope_id = Column(String, ForeignKey("engagement_scopes.id"), nullable=False)
    
    # Session details
    session_name = Column(String(255), nullable=False)
    objectives = Column(JSON)  # List of testing objectives
    current_phase = Column(Enum(PentestPhaseEnum), default=PentestPhaseEnum.RECONNAISSANCE)
    status = Column(String(50), default="active")  # active, paused, completed, terminated
    
    # PTT Management
    tree_id = Column(String(100))  # Pentesting Task Tree ID
    primary_target = Column(String(255))
    
    # Timing
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True))
    estimated_duration_hours = Column(Integer)
    
    # Statistics
    tasks_completed = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    critical_findings_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    scope = relationship("EngagementScope", back_populates="pentesting_sessions")
    task_nodes = relationship("PentestingTask", back_populates="session")
    findings = relationship("SecurityFinding", back_populates="session")
    audit_logs = relationship("SecurityAuditLog", back_populates="session")

    def __repr__(self):
        return f"<PentestingSession(id='{self.id}', name='{self.session_name}', phase='{self.current_phase}')>"


class PentestingTask(Base):
    """Individual pentesting task (PTT node)"""
    __tablename__ = "pentesting_tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("pentesting_sessions.id"), nullable=False)
    parent_id = Column(String, ForeignKey("pentesting_tasks.id"))
    
    # Task details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    phase = Column(Enum(PentestPhaseEnum), nullable=False)
    status = Column(String(50), default="available")  # available, in_progress, completed, failed, blocked
    
    # Execution details
    tool_required = Column(String(100))
    estimated_duration_seconds = Column(Integer, default=300)
    actual_duration_seconds = Column(Integer)
    priority_score = Column(Float, default=0.5)
    risk_level = Column(Enum(RiskLevelEnum), default=RiskLevelEnum.LOW)
    requires_approval = Column(Boolean, default=False)
    
    # Results
    raw_output = Column(Text)
    exit_code = Column(Integer)
    error_message = Column(Text)
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    session = relationship("PentestingSession", back_populates="task_nodes")
    parent = relationship("PentestingTask", remote_side=[id])
    children = relationship("PentestingTask")
    findings = relationship("SecurityFinding", back_populates="task")

    def __repr__(self):
        return f"<PentestingTask(id='{self.id}', name='{self.name}', status='{self.status}')>"


class SecurityFinding(Base):
    """Security vulnerability/finding"""
    __tablename__ = "security_findings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("pentesting_sessions.id"), nullable=False)
    task_id = Column(String, ForeignKey("pentesting_tasks.id"))
    
    # Finding details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100))
    severity = Column(Enum(SeverityLevelEnum), default=SeverityLevelEnum.LOW)
    confidence = Column(Float, default=0.5)  # 0.0-1.0
    
    # Technical details
    affected_component = Column(String(255))
    service_name = Column(String(100))
    port_number = Column(Integer)
    protocol = Column(String(20))
    
    # Vulnerability information
    cve_id = Column(String(50))
    cvss_score = Column(Float)
    cvss_vector = Column(String(200))
    exploit_available = Column(Boolean, default=False)
    
    # Evidence
    evidence_data = Column(JSON)
    proof_of_concept = Column(Text)
    screenshots = Column(JSON)  # List of file paths
    
    # Impact and remediation
    impact = Column(Text)
    remediation = Column(Text)
    references = Column(JSON)  # List of reference URLs
    
    # Status tracking
    status = Column(String(50), default="new")  # new, verified, false_positive, fixed
    verified_at = Column(DateTime(timezone=True))
    fixed_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    session = relationship("PentestingSession", back_populates="findings")
    task = relationship("PentestingTask", back_populates="findings")

    def __repr__(self):
        return f"<SecurityFinding(id='{self.id}', title='{self.title}', severity='{self.severity}')>"


class SecurityAuditLog(Base):
    """Security audit log for compliance"""
    __tablename__ = "security_audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("pentesting_sessions.id"))
    
    # Event details
    event_type = Column(String(100), nullable=False)  # action_execution, scope_validation, session_started, etc.
    event_category = Column(String(50), default="security")
    severity = Column(String(20), default="info")  # debug, info, warning, error, critical
    
    # Actor information
    actor_type = Column(String(50))  # human, system, agent
    actor_id = Column(String(100))
    
    # Action details
    action_id = Column(String(100))
    action_type = Column(String(100))
    target = Column(String(255))
    tool_name = Column(String(100))
    
    # Context and results
    context = Column(JSON)
    result = Column(JSON)
    error_message = Column(Text)
    
    # Integrity
    hash_chain = Column(String(64))  # SHA-256 hash for integrity
    previous_hash = Column(String(64))
    
    # Timing
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    session = relationship("PentestingSession", back_populates="audit_logs")

    def __repr__(self):
        return f"<SecurityAuditLog(id='{self.id}', event_type='{self.event_type}', timestamp='{self.timestamp}')>"


class HumanApproval(Base):
    """Human approval records for security actions"""
    __tablename__ = "human_approvals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Action details
    action_id = Column(String(100), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    target = Column(String(500), nullable=True)
    tool_name = Column(String(100), nullable=True)
    command = Column(Text, nullable=True)
    
    # Risk assessment
    risk_level = Column(Enum(RiskLevelEnum), nullable=False)
    risk_score = Column(Float, nullable=False)  # 0.0 - 1.0
    risk_factors = Column(JSON, nullable=True)  # List of risk factors
    impact_assessment = Column(Text, nullable=True)
    
    # Request details
    requested_by = Column(String(255), nullable=False)
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    justification = Column(Text, nullable=True)
    
    # Approval workflow
    required_approver_role = Column(String(100), nullable=False)
    approval_conditions = Column(JSON, nullable=True)  # Required conditions
    timeout_at = Column(DateTime(timezone=True), nullable=False)
    
    # Status and result
    status = Column(String(50), default="pending")  # pending, approved, denied, timeout, cancelled
    approver_id = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    denial_reason = Column(Text, nullable=True)
    approval_conditions_accepted = Column(JSON, nullable=True)  # Accepted conditions
    
    # Metadata
    reason = Column(Text, nullable=True)  # Additional approval/denial reason
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When approval expires
    signature_hash = Column(String(128), nullable=True)  # Digital signature
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<HumanApproval(id='{self.id}', action_id='{self.action_id}', status='{self.status}')>"