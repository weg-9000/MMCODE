"""
MMCODE Security Platform - Human Approval Workflow
=================================================

고위험 보안 작업의 인간 승인 워크플로우 관리
- 위험도 평가 및 승인 요청
- 알림 및 추적 시스템
- 타임아웃 및 조건부 승인

Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_

from .models import (
    SecurityAction,
    RiskLevel,
    HumanApproval,
    ActionStatus,
    generate_action_id,
    PentestPhase
)
from ..models.models import HumanApproval as DBHumanApproval

logger = logging.getLogger(__name__)


class ApprovalResult(Enum):
    """승인 결과"""
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"
    PENDING = "pending"
    CANCELLED = "cancelled"


class NotificationChannel(Enum):
    """알림 채널"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class RiskAssessment:
    """위험도 평가 결과"""
    risk_level: RiskLevel
    risk_score: float  # 0.0 - 1.0
    risk_factors: List[str]
    impact_assessment: str
    likelihood: str
    
    # 구체적 위험 요소
    destructive_potential: bool = False
    data_exposure_risk: bool = False
    system_availability_risk: bool = False
    compliance_risk: bool = False
    reputation_risk: bool = False
    
    # 권장 조건
    recommended_conditions: List[str] = field(default_factory=list)
    recommended_timeout_minutes: int = 60
    required_approver_level: str = "security_lead"


@dataclass
class ApprovalRequest:
    """승인 요청"""
    request_id: str
    action: SecurityAction
    risk_assessment: RiskAssessment
    
    # 요청 정보
    requested_by: str
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    justification: str = ""
    
    # 승인 설정
    timeout_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=2))
    required_approver_role: str = "security_lead"
    approval_conditions: List[str] = field(default_factory=list)
    
    # 상태
    status: ApprovalResult = ApprovalResult.PENDING
    notified_approvers: List[str] = field(default_factory=list)
    
    # 결과
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    denial_reason: Optional[str] = None
    approval_conditions_accepted: List[str] = field(default_factory=list)


@dataclass
class ApprovalConfiguration:
    """승인 워크플로우 설정"""
    # 기본 설정
    auto_approve_below: RiskLevel = RiskLevel.LOW
    require_approval_above: RiskLevel = RiskLevel.MEDIUM
    
    # 타임아웃 설정
    default_timeout_minutes: int = 120
    critical_timeout_minutes: int = 30
    low_risk_timeout_minutes: int = 240
    
    # 승인자 매핑
    approver_mapping: Dict[str, List[str]] = field(default_factory=lambda: {
        "low": ["security_analyst"],
        "medium": ["security_lead"],
        "high": ["security_manager", "ciso"],
        "critical": ["ciso", "security_director"]
    })
    
    # 알림 설정
    notification_channels: List[NotificationChannel] = field(default_factory=lambda: [
        NotificationChannel.EMAIL,
        NotificationChannel.SLACK
    ])
    
    # 에스컬레이션 설정
    escalation_timeout_minutes: int = 60
    max_escalation_levels: int = 3


class RiskEvaluator:
    """위험도 평가 엔진"""
    
    def __init__(self):
        """위험 평가 규칙 초기화"""
        self.destructive_patterns = [
            r"rm\s+-rf",
            r"format\s+[a-z]:",
            r"del\s+/[sqf]",
            r"shutdown",
            r"reboot",
            r"halt",
            r"service\s+stop",
            r"systemctl\s+stop",
            r"kill\s+-9",
            r"dd\s+if=",
            r"mkfs\.",
            r"fdisk"
        ]
        
        self.data_extraction_patterns = [
            r"copy\s+.*\\",
            r"scp\s+.*:",
            r"rsync\s+.*:",
            r"curl\s+.*--data",
            r"wget\s+.*--post",
            r"exfiltrate",
            r"download\s+.*\.(db|sql|csv|xlsx)",
            r"backup\s+.*database"
        ]
        
        self.high_impact_targets = [
            "domain_controller",
            "database_server",
            "file_server",
            "web_server",
            "mail_server",
            "backup_server",
            "authentication_server"
        ]
    
    async def assess_risk(
        self,
        action: SecurityAction,
        context: Dict[str, Any] = None
    ) -> RiskAssessment:
        """
        보안 작업의 위험도 평가
        
        Args:
            action: 평가할 보안 작업
            context: 추가 컨텍스트 정보
            
        Returns:
            RiskAssessment: 위험도 평가 결과
        """
        context = context or {}
        risk_factors = []
        risk_score = 0.0
        
        # 1. 페이즈별 기본 위험도
        phase_risk = self._assess_phase_risk(action.phase)
        risk_score += phase_risk
        risk_factors.append(f"Phase risk: {action.phase.value}")
        
        # 2. 도구별 위험도
        tool_risk = self._assess_tool_risk(action.tool_name)
        risk_score += tool_risk
        if tool_risk > 0.3:
            risk_factors.append(f"High-risk tool: {action.tool_name}")
        
        # 3. 대상 중요도
        target_risk = self._assess_target_risk(action.target, context)
        risk_score += target_risk
        if target_risk > 0.2:
            risk_factors.append(f"Critical target: {action.target}")
        
        # 4. 명령어 분석
        command_risk = self._assess_command_risk(action.command)
        risk_score += command_risk
        if command_risk > 0.3:
            risk_factors.append("Potentially destructive command")
        
        # 5. 네트워크 영향도
        if action.requires_network:
            network_risk = self._assess_network_risk(action, context)
            risk_score += network_risk
            if network_risk > 0.2:
                risk_factors.append("High network impact")
        
        # 6. 시간 민감도
        time_risk = self._assess_time_sensitivity(context)
        risk_score += time_risk
        
        # 정규화 (0.0 - 1.0)
        risk_score = min(risk_score, 1.0)
        
        # 위험 수준 결정
        if risk_score < 0.3:
            risk_level = RiskLevel.LOW
        elif risk_score < 0.5:
            risk_level = RiskLevel.MEDIUM
        elif risk_score < 0.8:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL
        
        # 구체적 위험 요소 분석
        destructive_potential = self._check_destructive_potential(action)
        data_exposure_risk = self._check_data_exposure_risk(action)
        system_availability_risk = self._check_availability_risk(action)
        compliance_risk = self._check_compliance_risk(action, context)
        
        # 영향도 평가
        impact_assessment = self._generate_impact_assessment(
            risk_level, destructive_potential, data_exposure_risk,
            system_availability_risk, compliance_risk
        )
        
        # 가능성 평가
        likelihood = self._assess_likelihood(action, context)
        
        # 권장 조건 생성
        conditions = self._generate_recommended_conditions(
            risk_level, action, destructive_potential, data_exposure_risk
        )
        
        # 권장 타임아웃
        timeout_minutes = self._calculate_recommended_timeout(risk_level, action)
        
        # 필요 승인자 레벨
        approver_level = self._determine_approver_level(risk_level, action)
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            impact_assessment=impact_assessment,
            likelihood=likelihood,
            destructive_potential=destructive_potential,
            data_exposure_risk=data_exposure_risk,
            system_availability_risk=system_availability_risk,
            compliance_risk=compliance_risk,
            recommended_conditions=conditions,
            recommended_timeout_minutes=timeout_minutes,
            required_approver_level=approver_level
        )
    
    def _assess_phase_risk(self, phase: PentestPhase) -> float:
        """페이즈별 위험도 평가"""
        phase_risks = {
            PentestPhase.RECONNAISSANCE: 0.1,
            PentestPhase.SCANNING: 0.15,
            PentestPhase.ENUMERATION: 0.2,
            PentestPhase.VULNERABILITY_ASSESSMENT: 0.25,
            PentestPhase.EXPLOITATION: 0.7,
            PentestPhase.POST_EXPLOITATION: 0.8,
            PentestPhase.REPORTING: 0.05
        }
        return phase_risks.get(phase, 0.3)
    
    def _assess_tool_risk(self, tool_name: Optional[str]) -> float:
        """도구별 위험도 평가"""
        if not tool_name:
            return 0.1
        
        tool_name = tool_name.lower()
        
        high_risk_tools = ["metasploit", "cobalt_strike", "empire", "powershell_empire"]
        medium_risk_tools = ["nessus", "openvas", "burp_suite", "sqlmap"]
        low_risk_tools = ["nmap", "nuclei", "dirb", "gobuster"]
        
        if any(tool in tool_name for tool in high_risk_tools):
            return 0.6
        elif any(tool in tool_name for tool in medium_risk_tools):
            return 0.3
        elif any(tool in tool_name for tool in low_risk_tools):
            return 0.1
        else:
            return 0.2
    
    def _assess_target_risk(self, target: Optional[str], context: Dict[str, Any]) -> float:
        """대상 중요도 평가"""
        if not target:
            return 0.1
        
        target_lower = target.lower()
        
        # 중요 시스템 키워드 확인
        critical_keywords = [
            "dc", "domain", "controller", "database", "db", "sql",
            "backup", "exchange", "sharepoint", "citrix"
        ]
        
        for keyword in critical_keywords:
            if keyword in target_lower:
                return 0.4
        
        # 프로덕션 환경 지시자
        prod_keywords = ["prod", "production", "live", "www"]
        for keyword in prod_keywords:
            if keyword in target_lower:
                return 0.3
        
        return 0.1
    
    def _assess_command_risk(self, command: Optional[str]) -> float:
        """명령어 위험도 분석"""
        if not command:
            return 0.0
        
        import re
        
        command_lower = command.lower()
        risk_score = 0.0
        
        # 파괴적 명령어 패턴 확인
        for pattern in self.destructive_patterns:
            if re.search(pattern, command_lower):
                risk_score += 0.4
                break
        
        # 데이터 추출 패턴 확인
        for pattern in self.data_extraction_patterns:
            if re.search(pattern, command_lower):
                risk_score += 0.3
                break
        
        return min(risk_score, 0.7)
    
    def _assess_network_risk(self, action: SecurityAction, context: Dict[str, Any]) -> float:
        """네트워크 영향도 평가"""
        risk_score = 0.0
        
        # 포트 범위 확인
        if action.target_ports:
            if len(action.target_ports) > 100:
                risk_score += 0.2  # 광범위 스캔
            elif any(port in [22, 80, 443, 3389] for port in action.target_ports):
                risk_score += 0.1  # 중요 포트
        
        # 동시 요청 수
        concurrent_requests = context.get('concurrent_requests', 1)
        if concurrent_requests > 10:
            risk_score += 0.2
        
        return min(risk_score, 0.3)
    
    def _assess_time_sensitivity(self, context: Dict[str, Any]) -> float:
        """시간 민감도 평가"""
        # 업무 시간 외 요청은 위험도 증가
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        
        if 18 <= hour <= 23 or 0 <= hour <= 6:  # 밤 시간
            return 0.1
        
        return 0.0
    
    def _check_destructive_potential(self, action: SecurityAction) -> bool:
        """파괴적 잠재력 확인"""
        if action.is_destructive:
            return True
        
        if action.command:
            import re
            for pattern in self.destructive_patterns:
                if re.search(pattern, action.command.lower()):
                    return True
        
        return False
    
    def _check_data_exposure_risk(self, action: SecurityAction) -> bool:
        """데이터 노출 위험 확인"""
        if action.command:
            import re
            for pattern in self.data_extraction_patterns:
                if re.search(pattern, action.command.lower()):
                    return True
        
        return False
    
    def _check_availability_risk(self, action: SecurityAction) -> bool:
        """가용성 영향 확인"""
        if action.phase in [PentestPhase.EXPLOITATION, PentestPhase.POST_EXPLOITATION]:
            return True
        
        if action.tool_name and "dos" in action.tool_name.lower():
            return True
        
        return False
    
    def _check_compliance_risk(self, action: SecurityAction, context: Dict[str, Any]) -> bool:
        """컴플라이언스 위험 확인"""
        # PCI DSS, HIPAA, SOX 등 규제 환경에서는 특별한 주의 필요
        regulated_environment = context.get('compliance_requirements', [])
        
        if regulated_environment and action.phase == PentestPhase.EXPLOITATION:
            return True
        
        return False
    
    def _generate_impact_assessment(
        self,
        risk_level: RiskLevel,
        destructive: bool,
        data_exposure: bool,
        availability: bool,
        compliance: bool
    ) -> str:
        """영향도 평가 텍스트 생성"""
        impacts = []
        
        if destructive:
            impacts.append("잠재적 시스템 손상")
        if data_exposure:
            impacts.append("데이터 노출 위험")
        if availability:
            impacts.append("서비스 중단 가능성")
        if compliance:
            impacts.append("규제 준수 위험")
        
        if not impacts:
            return f"{risk_level.value} 위험 수준의 일반적인 보안 테스트"
        
        return f"{risk_level.value} 위험 수준: " + ", ".join(impacts)
    
    def _assess_likelihood(self, action: SecurityAction, context: Dict[str, Any]) -> str:
        """가능성 평가"""
        if action.phase in [PentestPhase.EXPLOITATION, PentestPhase.POST_EXPLOITATION]:
            return "중간"
        elif action.phase == PentestPhase.VULNERABILITY_ASSESSMENT:
            return "낮음"
        else:
            return "매우 낮음"
    
    def _generate_recommended_conditions(
        self,
        risk_level: RiskLevel,
        action: SecurityAction,
        destructive: bool,
        data_exposure: bool
    ) -> List[str]:
        """권장 승인 조건 생성"""
        conditions = []
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            conditions.append("실시간 모니터링 필수")
            conditions.append("즉시 중단 가능한 상태 유지")
        
        if destructive:
            conditions.append("시스템 백업 확인 완료")
            conditions.append("복구 계획 수립")
        
        if data_exposure:
            conditions.append("데이터 보호 조치 적용")
            conditions.append("로그 모니터링 강화")
        
        if action.phase == PentestPhase.EXPLOITATION:
            conditions.append("대상 시스템 격리 준비")
            conditions.append("사고 대응팀 대기")
        
        return conditions
    
    def _calculate_recommended_timeout(self, risk_level: RiskLevel, action: SecurityAction) -> int:
        """권장 타임아웃 계산"""
        base_timeout = {
            RiskLevel.LOW: 240,      # 4시간
            RiskLevel.MEDIUM: 120,   # 2시간
            RiskLevel.HIGH: 60,      # 1시간
            RiskLevel.CRITICAL: 30   # 30분
        }
        
        timeout = base_timeout.get(risk_level, 120)
        
        # 주말/야간에는 타임아웃 단축
        current_time = datetime.now(timezone.utc)
        if current_time.weekday() >= 5:  # 주말
            timeout = max(timeout // 2, 30)
        
        return timeout
    
    def _determine_approver_level(self, risk_level: RiskLevel, action: SecurityAction) -> str:
        """필요 승인자 레벨 결정"""
        approver_mapping = {
            RiskLevel.LOW: "security_analyst",
            RiskLevel.MEDIUM: "security_lead",
            RiskLevel.HIGH: "security_manager",
            RiskLevel.CRITICAL: "ciso"
        }
        
        base_level = approver_mapping.get(risk_level, "security_lead")
        
        # 특별 조건에서는 승인자 레벨 상향
        if action.phase == PentestPhase.EXPLOITATION and risk_level != RiskLevel.CRITICAL:
            higher_levels = {
                "security_analyst": "security_lead",
                "security_lead": "security_manager",
                "security_manager": "ciso"
            }
            return higher_levels.get(base_level, "ciso")
        
        return base_level


class ApprovalWorkflow:
    """
    인간 승인 워크플로우 관리자
    
    기능:
    - 승인 요청 생성 및 관리
    - 알림 발송 및 추적
    - 타임아웃 및 에스컬레이션 처리
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        config: ApprovalConfiguration = None
    ):
        """
        Args:
            db_session: 데이터베이스 세션
            config: 승인 워크플로우 설정
        """
        self.db = db_session
        self.config = config or ApprovalConfiguration()
        self.risk_evaluator = RiskEvaluator()
        
        # 활성 승인 요청 추적
        self._active_requests: Dict[str, ApprovalRequest] = {}
        
        # 알림 핸들러
        self._notification_handlers: Dict[NotificationChannel, Callable] = {}
        
        # 타임아웃 태스크 추적
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
    
    async def request_approval(
        self,
        action: SecurityAction,
        requested_by: str,
        justification: str = "",
        context: Dict[str, Any] = None
    ) -> ApprovalRequest:
        """
        승인 요청 생성
        
        Args:
            action: 승인이 필요한 보안 작업
            requested_by: 요청자 ID
            justification: 요청 사유
            context: 추가 컨텍스트
            
        Returns:
            ApprovalRequest: 생성된 승인 요청
        """
        try:
            # 1. 위험도 평가
            risk_assessment = await self.risk_evaluator.assess_risk(action, context)
            
            # 2. 자동 승인 가능 여부 확인
            if risk_assessment.risk_level.value <= self.config.auto_approve_below.value:
                # 자동 승인
                logger.info(f"Auto-approving action {action.action_id} (risk: {risk_assessment.risk_level.value})")
                return await self._create_auto_approval(action, risk_assessment, requested_by)
            
            # 3. 승인 요청 생성
            request = ApprovalRequest(
                request_id=generate_action_id(),
                action=action,
                risk_assessment=risk_assessment,
                requested_by=requested_by,
                justification=justification,
                timeout_at=datetime.now(timezone.utc) + timedelta(
                    minutes=risk_assessment.recommended_timeout_minutes
                ),
                required_approver_role=risk_assessment.required_approver_level,
                approval_conditions=risk_assessment.recommended_conditions
            )
            
            # 4. 데이터베이스 저장
            await self._save_approval_request(request)
            
            # 5. 활성 요청 추적
            self._active_requests[request.request_id] = request
            
            # 6. 알림 발송
            await self._send_approval_notification(request)
            
            # 7. 타임아웃 스케줄링
            await self._schedule_timeout(request)
            
            logger.info(
                f"Created approval request {request.request_id} for action {action.action_id} "
                f"(risk: {risk_assessment.risk_level.value}, timeout: {risk_assessment.recommended_timeout_minutes}m)"
            )
            
            return request
            
        except Exception as e:
            logger.error(f"Failed to create approval request for action {action.action_id}: {str(e)}")
            raise
    
    async def process_approval(
        self,
        request_id: str,
        approved: bool,
        approver_id: str,
        reason: str = "",
        conditions_accepted: List[str] = None
    ) -> ApprovalResult:
        """
        승인/거부 처리
        
        Args:
            request_id: 승인 요청 ID
            approved: 승인 여부
            approver_id: 승인자 ID
            reason: 승인/거부 사유
            conditions_accepted: 수락된 조건 목록
            
        Returns:
            ApprovalResult: 처리 결과
        """
        try:
            # 1. 요청 확인
            request = self._active_requests.get(request_id)
            if not request:
                # 데이터베이스에서 로드 시도
                request = await self._load_approval_request(request_id)
                if not request:
                    logger.warning(f"Approval request {request_id} not found")
                    return ApprovalResult.CANCELLED
            
            # 2. 타임아웃 확인
            if datetime.now(timezone.utc) > request.timeout_at:
                logger.warning(f"Approval request {request_id} has timed out")
                await self._handle_timeout(request)
                return ApprovalResult.TIMEOUT
            
            # 3. 승인 처리
            if approved:
                request.status = ApprovalResult.APPROVED
                request.approved_by = approver_id
                request.approved_at = datetime.now(timezone.utc)
                request.approval_conditions_accepted = conditions_accepted or []
                
                logger.info(f"Approval request {request_id} approved by {approver_id}")
            else:
                request.status = ApprovalResult.DENIED
                request.denial_reason = reason
                
                logger.info(f"Approval request {request_id} denied by {approver_id}: {reason}")
            
            # 4. 데이터베이스 업데이트
            await self._update_approval_request(request)
            
            # 5. 타임아웃 태스크 취소
            await self._cancel_timeout(request_id)
            
            # 6. 요청자에게 알림
            await self._send_result_notification(request, approver_id)
            
            # 7. 활성 요청에서 제거
            if request_id in self._active_requests:
                del self._active_requests[request_id]
            
            return request.status
            
        except Exception as e:
            logger.error(f"Failed to process approval request {request_id}: {str(e)}")
            raise
    
    async def get_pending_requests(
        self,
        approver_role: str = None
    ) -> List[ApprovalRequest]:
        """
        대기 중인 승인 요청 목록 조회
        
        Args:
            approver_role: 승인자 역할 필터
            
        Returns:
            List[ApprovalRequest]: 대기 중인 요청 목록
        """
        try:
            pending_requests = []
            
            for request in self._active_requests.values():
                if request.status == ApprovalResult.PENDING:
                    if not approver_role or request.required_approver_role == approver_role:
                        pending_requests.append(request)
            
            return pending_requests
            
        except Exception as e:
            logger.error(f"Failed to get pending requests: {str(e)}")
            raise
    
    async def cancel_request(
        self,
        request_id: str,
        cancelled_by: str,
        reason: str = ""
    ) -> bool:
        """
        승인 요청 취소
        
        Args:
            request_id: 요청 ID
            cancelled_by: 취소자 ID
            reason: 취소 사유
            
        Returns:
            bool: 취소 성공 여부
        """
        try:
            request = self._active_requests.get(request_id)
            if not request:
                return False
            
            request.status = ApprovalResult.CANCELLED
            request.denial_reason = f"Cancelled by {cancelled_by}: {reason}"
            
            await self._update_approval_request(request)
            await self._cancel_timeout(request_id)
            
            if request_id in self._active_requests:
                del self._active_requests[request_id]
            
            logger.info(f"Approval request {request_id} cancelled by {cancelled_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel approval request {request_id}: {str(e)}")
            return False
    
    async def check_action_approval(self, action_id: str) -> Optional[HumanApproval]:
        """
        작업의 승인 상태 확인
        
        Args:
            action_id: 작업 ID
            
        Returns:
            Optional[HumanApproval]: 승인 정보 (승인되지 않았으면 None)
        """
        try:
            # 활성 요청에서 확인
            for request in self._active_requests.values():
                if (request.action.action_id == action_id and 
                    request.status == ApprovalResult.APPROVED):
                    
                    return HumanApproval(
                        granted=True,
                        approver=request.approved_by,
                        approved_at=request.approved_at,
                        conditions=request.approval_conditions_accepted,
                        expires_at=request.timeout_at
                    )
            
            # 데이터베이스에서 확인
            result = await self.db.execute(
                select(DBHumanApproval)
                .where(DBHumanApproval.action_id == action_id)
                .where(DBHumanApproval.status == "approved")
            )
            db_approval = result.scalar_one_or_none()
            
            if db_approval:
                return HumanApproval(
                    granted=True,
                    approver=db_approval.approver_id,
                    approved_at=db_approval.approved_at,
                    conditions=db_approval.approval_conditions or [],
                    expires_at=db_approval.expires_at,
                    reason=db_approval.reason
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check approval for action {action_id}: {str(e)}")
            return None
    
    def register_notification_handler(
        self,
        channel: NotificationChannel,
        handler: Callable
    ):
        """알림 핸들러 등록"""
        self._notification_handlers[channel] = handler
        logger.info(f"Registered notification handler for {channel.value}")
    
    async def cleanup_expired_requests(self):
        """만료된 요청 정리"""
        try:
            expired_requests = []
            current_time = datetime.now(timezone.utc)
            
            for request_id, request in self._active_requests.items():
                if current_time > request.timeout_at and request.status == ApprovalResult.PENDING:
                    expired_requests.append(request_id)
            
            for request_id in expired_requests:
                request = self._active_requests[request_id]
                await self._handle_timeout(request)
            
            logger.info(f"Cleaned up {len(expired_requests)} expired approval requests")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired requests: {str(e)}")
    
    # Private methods
    
    async def _create_auto_approval(
        self,
        action: SecurityAction,
        risk_assessment: RiskAssessment,
        requested_by: str
    ) -> ApprovalRequest:
        """자동 승인 요청 생성"""
        request = ApprovalRequest(
            request_id=generate_action_id(),
            action=action,
            risk_assessment=risk_assessment,
            requested_by=requested_by,
            status=ApprovalResult.APPROVED,
            approved_by="system",
            approved_at=datetime.now(timezone.utc),
            justification="Auto-approved based on low risk assessment"
        )
        
        await self._save_approval_request(request)
        return request
    
    async def _save_approval_request(self, request: ApprovalRequest):
        """승인 요청을 데이터베이스에 저장"""
        db_approval = DBHumanApproval(
            id=request.request_id,
            action_id=request.action.action_id,
            action_type=request.action.action_type,
            target=request.action.target,
            tool_name=request.action.tool_name,
            risk_level=request.risk_assessment.risk_level,
            risk_score=request.risk_assessment.risk_score,
            risk_factors=request.risk_assessment.risk_factors,
            requested_by=request.requested_by,
            requested_at=request.requested_at,
            justification=request.justification,
            required_approver_role=request.required_approver_role,
            approval_conditions=request.approval_conditions,
            timeout_at=request.timeout_at,
            status=request.status.value,
            approved_by=request.approved_by,
            approved_at=request.approved_at,
            denial_reason=request.denial_reason
        )
        
        self.db.add(db_approval)
        await self.db.commit()
    
    async def _update_approval_request(self, request: ApprovalRequest):
        """승인 요청 상태 업데이트"""
        await self.db.execute(
            update(DBHumanApproval)
            .where(DBHumanApproval.id == request.request_id)
            .values(
                status=request.status.value,
                approved_by=request.approved_by,
                approved_at=request.approved_at,
                denial_reason=request.denial_reason,
                approval_conditions_accepted=request.approval_conditions_accepted
            )
        )
        await self.db.commit()
    
    async def _load_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """데이터베이스에서 승인 요청 로드"""
        # Implementation would load from database and reconstruct ApprovalRequest
        # This is a placeholder for now
        return None
    
    async def _send_approval_notification(self, request: ApprovalRequest):
        """승인 요청 알림 발송"""
        for channel in self.config.notification_channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    await handler(request, "approval_request")
                    request.notified_approvers.append(f"{channel.value}:sent")
                except Exception as e:
                    logger.error(f"Failed to send {channel.value} notification: {str(e)}")
    
    async def _send_result_notification(self, request: ApprovalRequest, approver: str):
        """승인 결과 알림 발송"""
        for channel in self.config.notification_channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    await handler(request, "approval_result")
                except Exception as e:
                    logger.error(f"Failed to send result {channel.value} notification: {str(e)}")
    
    async def _schedule_timeout(self, request: ApprovalRequest):
        """타임아웃 스케줄링"""
        async def timeout_handler():
            await asyncio.sleep(
                (request.timeout_at - datetime.now(timezone.utc)).total_seconds()
            )
            await self._handle_timeout(request)
        
        task = asyncio.create_task(timeout_handler())
        self._timeout_tasks[request.request_id] = task
    
    async def _cancel_timeout(self, request_id: str):
        """타임아웃 태스크 취소"""
        task = self._timeout_tasks.get(request_id)
        if task:
            task.cancel()
            del self._timeout_tasks[request_id]
    
    async def _handle_timeout(self, request: ApprovalRequest):
        """타임아웃 처리"""
        request.status = ApprovalResult.TIMEOUT
        request.denial_reason = "Request timed out without approval"
        
        await self._update_approval_request(request)
        
        if request.request_id in self._active_requests:
            del self._active_requests[request.request_id]
        
        logger.warning(f"Approval request {request.request_id} timed out")
        
        # 타임아웃 알림 발송
        for channel in self.config.notification_channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    await handler(request, "timeout")
                except Exception as e:
                    logger.error(f"Failed to send timeout {channel.value} notification: {str(e)}")