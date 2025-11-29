"""
MMCODE Security Platform - Security Models
============================================

보안 작업에 필요한 핵심 데이터 모델 정의
- EngagementScope: 펜테스팅 범위 정의
- SecurityAction: 보안 작업 정의
- ValidationResult: 검증 결과

Version: 2.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import List, Optional, Dict, Any, Set
from ipaddress import IPv4Network, IPv4Address, ip_address, ip_network
import re
import hashlib


class PentestPhase(Enum):
    """펜테스팅 페이즈"""
    RECONNAISSANCE = "reconnaissance"
    SCANNING = "scanning"
    ENUMERATION = "enumeration"
    VULNERABILITY_ASSESSMENT = "vulnerability_assessment"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    REPORTING = "reporting"


class EngagementType(Enum):
    """엔게이지먼트 유형"""
    INTERNAL = "internal"
    EXTERNAL = "external"
    WEB_APP = "web_app"
    CLOUD = "cloud"
    AI_REDTEAM = "ai_redteam"
    NETWORK = "network"
    MOBILE = "mobile"


class RiskLevel(Enum):
    """위험 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SeverityLevel(Enum):
    """심각도 수준"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class TimeWindow:
    """허용된 작업 시간 윈도우"""
    start_time: time
    end_time: time
    timezone: str = "UTC"
    days_of_week: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon-Fri
    
    def is_within_window(self, check_time: datetime) -> bool:
        """현재 시간이 허용된 윈도우 내인지 확인"""
        current_time = check_time.time()
        current_day = check_time.weekday()
        
        if current_day not in self.days_of_week:
            return False
        
        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        else:
            # 자정을 넘어가는 경우
            return current_time >= self.start_time or current_time <= self.end_time


@dataclass
class EngagementScope:
    """
    펜테스팅 엔게이지먼트 범위 정의
    
    모든 보안 테스트는 이 범위 내에서만 수행되어야 함
    """
    # 기본 정보
    engagement_id: str
    engagement_name: str
    engagement_type: EngagementType
    
    # 대상 범위
    ip_ranges: List[str] = field(default_factory=list)  # CIDR 형식: ["192.168.1.0/24"]
    domains: List[str] = field(default_factory=list)    # ["example.com", "*.example.com"]
    urls: List[str] = field(default_factory=list)       # 특정 URL 목록
    
    # 제외 대상
    excluded_ips: List[str] = field(default_factory=list)
    excluded_domains: List[str] = field(default_factory=list)
    excluded_ports: List[int] = field(default_factory=list)
    
    # 허용된 포트 (비어있으면 모든 포트 허용)
    allowed_ports: List[int] = field(default_factory=list)
    
    # 허용된 방법론
    allowed_methods: List[str] = field(default_factory=lambda: [
        "port_scan", "vuln_scan", "web_scan", "dns_enum"
    ])
    
    # 금지된 방법론
    prohibited_methods: List[str] = field(default_factory=lambda: [
        "dos_attack", "data_exfiltration", "ransomware", "social_engineering"
    ])
    
    # 시간 제약
    time_windows: List[TimeWindow] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Rate Limiting
    max_requests_per_second: int = 10
    max_concurrent_scans: int = 3
    
    # 기타 제약
    requires_approval_above: RiskLevel = RiskLevel.MEDIUM
    emergency_contact: Optional[str] = None
    
    def __post_init__(self):
        """초기화 후 IP 네트워크 파싱"""
        self._parsed_networks: List[IPv4Network] = []
        self._parsed_excluded: List[IPv4Network] = []
        
        for ip_range in self.ip_ranges:
            try:
                self._parsed_networks.append(ip_network(ip_range, strict=False))
            except ValueError:
                pass
        
        for ip_range in self.excluded_ips:
            try:
                self._parsed_excluded.append(ip_network(ip_range, strict=False))
            except ValueError:
                pass
    
    def is_ip_in_scope(self, ip: str) -> bool:
        """IP가 허용된 범위 내인지 확인"""
        try:
            addr = ip_address(ip)
        except ValueError:
            return False
        
        # 제외 대상 체크
        for excluded in self._parsed_excluded:
            if addr in excluded:
                return False
        
        # 허용 범위 체크
        for network in self._parsed_networks:
            if addr in network:
                return True
        
        return False
    
    def is_domain_in_scope(self, domain: str) -> bool:
        """도메인이 허용된 범위 내인지 확인"""
        domain = domain.lower().strip()
        
        # 제외 대상 체크
        for excluded in self.excluded_domains:
            if self._domain_matches(domain, excluded):
                return False
        
        # 허용 범위 체크
        for allowed in self.domains:
            if self._domain_matches(domain, allowed):
                return True
        
        return False
    
    def _domain_matches(self, domain: str, pattern: str) -> bool:
        """도메인 패턴 매칭 (와일드카드 지원)"""
        pattern = pattern.lower().strip()
        
        if pattern.startswith("*."):
            # 와일드카드 패턴: *.example.com
            suffix = pattern[1:]  # .example.com
            return domain.endswith(suffix) or domain == pattern[2:]
        else:
            return domain == pattern
    
    def is_port_allowed(self, port: int) -> bool:
        """포트가 허용되었는지 확인"""
        if port in self.excluded_ports:
            return False
        
        if not self.allowed_ports:
            return True
        
        return port in self.allowed_ports
    
    def is_method_allowed(self, method: str) -> bool:
        """방법론이 허용되었는지 확인"""
        method = method.lower()
        
        if method in self.prohibited_methods:
            return False
        
        if not self.allowed_methods:
            return True
        
        return method in self.allowed_methods


@dataclass
class SecurityAction:
    """
    보안 작업 정의
    
    에이전트가 수행하려는 모든 보안 관련 작업을 표현
    """
    action_id: str
    action_type: str
    
    # 대상 정보
    target: Optional[str] = None
    target_ip: Optional[str] = None
    target_ports: List[int] = field(default_factory=list)
    target_domain: Optional[str] = None
    target_url: Optional[str] = None
    
    # 실행 정보
    tool_name: Optional[str] = None
    command: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 메타데이터
    method: Optional[str] = None
    phase: PentestPhase = PentestPhase.RECONNAISSANCE
    risk_level: RiskLevel = RiskLevel.LOW
    requires_network: bool = True
    is_destructive: bool = False
    
    # 추적 정보
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    correlation_id: Optional[str] = None
    
    def get_hash(self) -> str:
        """작업의 고유 해시 생성 (감사 추적용)"""
        content = f"{self.action_type}:{self.target}:{self.command}:{self.created_at.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class LayerResult:
    """단일 검증 레이어 결과"""
    layer: str  # "prompt", "deterministic", "network"
    valid: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0


@dataclass
class ValidationResult:
    """
    3계층 검증 결과
    
    스코프 검증 엔진의 최종 결과를 표현
    """
    valid: bool
    blocked_at: Optional[str] = None  # None if valid, else "prompt"/"deterministic"/"network"
    layer_results: List[LayerResult] = field(default_factory=list)
    
    # 메타데이터
    action_id: Optional[str] = None
    validation_time_ms: float = 0.0
    validated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def all_violations(self) -> List[str]:
        """모든 레이어의 위반 사항 수집"""
        violations = []
        for result in self.layer_results:
            violations.extend(result.violations)
        return violations
    
    @property
    def all_warnings(self) -> List[str]:
        """모든 레이어의 경고 수집"""
        warnings = []
        for result in self.layer_results:
            warnings.extend(result.warnings)
        return warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (로깅/저장용)"""
        return {
            "valid": self.valid,
            "blocked_at": self.blocked_at,
            "violations": self.all_violations,
            "warnings": self.all_warnings,
            "action_id": self.action_id,
            "validation_time_ms": self.validation_time_ms,
            "validated_at": self.validated_at.isoformat(),
            "layer_details": [
                {
                    "layer": r.layer,
                    "valid": r.valid,
                    "violations": r.violations,
                    "execution_time_ms": r.execution_time_ms
                }
                for r in self.layer_results
            ]
        }


@dataclass
class HumanApproval:
    """인간 승인 정보"""
    granted: bool
    approver: str
    approved_at: datetime = field(default_factory=datetime.utcnow)
    conditions: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None
    
    def is_valid(self) -> bool:
        """승인이 여전히 유효한지 확인"""
        if not self.granted:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


@dataclass
class SecurityFinding:
    """보안 발견사항"""
    finding_id: str
    finding_type: str
    severity: SeverityLevel
    
    # 취약점 정보
    title: str
    description: str
    technical_details: Optional[str] = None
    
    # 표준 식별자
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    
    # MITRE ATT&CK 매핑
    mitre_technique: Optional[str] = None
    mitre_tactic: Optional[str] = None
    
    # 영향받는 대상
    affected_asset: Optional[str] = None
    affected_port: Optional[int] = None
    affected_service: Optional[str] = None
    
    # 증거
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # 수정 정보
    remediation: Optional[str] = None
    remediation_complexity: Optional[str] = None
    
    # 상태
    status: str = "open"
    false_positive: bool = False
    verified: bool = False
    
    # 타임스탬프
    discovered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskNode:
    """PTT (Pentesting Task Tree) 노드"""
    id: str
    name: str
    description: str
    phase: PentestPhase
    
    # 상태
    status: str = "available"  # available, in_progress, completed, failed, blocked
    priority_score: float = 0.5
    
    # 관계
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    # 실행 정보
    tool_required: Optional[str] = None
    estimated_duration_seconds: int = 300
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    
    # 결과
    findings: List[SecurityFinding] = field(default_factory=list)
    execution_log: Optional[str] = None
    
    # 메타데이터
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class SecurityContext:
    """보안 작업 실행 컨텍스트"""
    session_id: str
    engagement_scope: EngagementScope
    current_phase: PentestPhase = PentestPhase.RECONNAISSANCE
    
    # 실행 제약
    rate_limit: int = 10
    request_timeout: int = 30
    scan_timeout: int = 300
    
    # 네트워크 정책
    network_policy: str = "restricted"
    allowed_outbound: List[str] = field(default_factory=list)
    
    # 추적
    correlation_id: Optional[str] = None
    parent_task_id: Optional[str] = None


# 유틸리티 함수
def generate_action_id() -> str:
    """고유 작업 ID 생성"""
    import uuid
    return f"act_{uuid.uuid4().hex[:12]}"


def generate_finding_id() -> str:
    """고유 발견사항 ID 생성"""
    import uuid
    return f"fnd_{uuid.uuid4().hex[:12]}"


def generate_task_id() -> str:
    """고유 태스크 ID 생성"""
    import uuid
    return f"tsk_{uuid.uuid4().hex[:12]}"