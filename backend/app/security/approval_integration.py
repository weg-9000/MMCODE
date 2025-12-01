"""
MMCODE Security Platform - Approval Workflow Integration
=======================================================

보안 도구와 승인 워크플로우 통합
- 자동 승인 요청 생성
- 도구 실행 전 승인 검증
- PTT와 승인 시스템 연동

Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from .models import SecurityAction, generate_action_id, PentestPhase, RiskLevel
from .approval_workflow import ApprovalWorkflow, ApprovalRequest, ApprovalResult
from .notifications import NotificationManager, NotificationConfig
from ..tools.base import ToolResult, BaseSecurityTool

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """실행 결과"""
    success: bool
    action_id: str
    status: str  # "completed", "failed", "denied", "pending_approval"
    message: str = ""
    findings: List[Any] = field(default_factory=list)
    execution_time: float = 0.0
    approval_request_id: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class ApprovalIntegrationManager:
    """
    승인 워크플로우 통합 관리자
    
    기능:
    - 보안 도구 실행 전 자동 승인 검증
    - PTT 작업과 승인 프로세스 연동
    - 승인이 필요한 작업 자동 감지
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        notification_manager: NotificationManager = None
    ):
        """
        Args:
            db_session: 데이터베이스 세션
            notification_manager: 알림 관리자
        """
        self.db = db_session
        self.approval_workflow = ApprovalWorkflow(db_session)
        self.notification_manager = notification_manager or NotificationManager()
        
        # 승인이 필요한 도구/명령어 패턴 정의
        self.high_risk_tools = {
            "metasploit", "empire", "cobalt_strike", "bloodhound",
            "mimikatz", "powersploit", "responder"
        }
        
        self.high_risk_commands = [
            r"exploit.*",
            r"shell.*",
            r"meterpreter.*",
            r"powershell.*-exec.*bypass",
            r".\s*invoke-.*",
            r".\s*get-.*credential",
            r".\s*dump.*",
            r".\s*extract.*"
        ]
        
        # 자동 승인이 가능한 도구들
        self.auto_approve_tools = {
            "nmap", "nuclei", "dirb", "gobuster", "whatweb",
            "nikto", "sslyze", "testssl"
        }
    
    async def check_approval_required(self, action: SecurityAction) -> bool:
        """
        작업이 승인을 필요로 하는지 확인
        
        Args:
            action: 보안 작업
            
        Returns:
            bool: 승인 필요 여부
        """
        try:
            # 1. 명시적 위험 수준 확인
            if action.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                return True
            
            # 2. 파괴적 작업 확인
            if action.is_destructive:
                return True
            
            # 3. 고위험 페이즈 확인
            high_risk_phases = [
                PentestPhase.EXPLOITATION,
                PentestPhase.POST_EXPLOITATION
            ]
            if action.phase in high_risk_phases:
                return True
            
            # 4. 고위험 도구 확인
            if action.tool_name and action.tool_name.lower() in self.high_risk_tools:
                return True
            
            # 5. 고위험 명령어 패턴 확인
            if action.command:
                import re
                for pattern in self.high_risk_commands:
                    if re.search(pattern, action.command.lower()):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check approval requirement: {str(e)}")
            # 에러 발생 시 안전하게 승인 필요로 처리
            return True
    
    async def request_approval_if_needed(
        self,
        action: SecurityAction,
        requested_by: str,
        justification: str = "",
        context: Dict[str, Any] = None
    ) -> Optional[ApprovalRequest]:
        """
        필요시 승인 요청 생성
        
        Args:
            action: 보안 작업
            requested_by: 요청자
            justification: 요청 사유
            context: 추가 컨텍스트
            
        Returns:
            Optional[ApprovalRequest]: 생성된 승인 요청 (승인 불필요시 None)
        """
        try:
            # 승인 필요 여부 확인
            needs_approval = await self.check_approval_required(action)
            
            if not needs_approval:
                logger.info(f"Action {action.action_id} does not require approval")
                return None
            
            # 이미 승인된 작업인지 확인
            existing_approval = await self.approval_workflow.check_action_approval(
                action.action_id
            )
            
            if existing_approval and existing_approval.is_valid():
                logger.info(f"Action {action.action_id} is already approved")
                return None
            
            # 승인 요청 생성
            approval_request = await self.approval_workflow.request_approval(
                action=action,
                requested_by=requested_by,
                justification=justification,
                context=context
            )
            
            logger.info(
                f"Approval request {approval_request.request_id} created for action {action.action_id}"
            )
            
            return approval_request
            
        except Exception as e:
            logger.error(f"Failed to request approval: {str(e)}")
            raise
    
    async def execute_with_approval(
        self,
        action: SecurityAction,
        tool_executor: BaseSecurityTool,
        session_id: str
    ) -> 'ExecutionResult':
        """
        승인이 필요한 작업 실행 (핵심 통합 메서드)
        
        Flow:
        1. 승인 필요 여부 확인
        2. 필요시 승인 요청 생성 및 대기
        3. 승인 완료 후 도구 실행
        4. 감사 로그 기록
        
        Args:
            action: 실행할 보안 작업
            tool_executor: 보안 도구 실행기
            session_id: 세션 식별자
            
        Returns:
            ExecutionResult: 실행 결과
        """
        try:
            # Step 1: 승인 필요 여부 확인
            requires_approval = await self.check_approval_required(action)
            
            if requires_approval:
                # Step 2: 승인 요청 생성
                approval_request = await self.approval_workflow.request_approval(
                    action=action,
                    requested_by=f"session_{session_id}",
                    justification=f"Automated security task: {action.action_type}"
                )
                
                # Step 3: 알림 발송
                await self.notification_manager.send_approval_notification(
                    approval_request
                )
                
                # Step 4: 승인 대기 (비동기)
                approval_status = await self._wait_for_approval(
                    approval_request,
                    timeout_seconds=action.parameters.get('timeout_seconds', 3600)
                )
                
                if approval_status.value != 'approved':
                    return ExecutionResult(
                        success=False,
                        action_id=action.action_id,
                        status="denied",
                        message=f"Approval {approval_status.value}",
                        approval_request_id=approval_request.request_id
                    )
            
            # Step 5: 도구 실행
            result = await tool_executor.execute(action.target, action.parameters)
            
            # Step 6: 감사 로그
            await self._log_execution(action, result, session_id)
            
            return ExecutionResult(
                success=result.success,
                action_id=action.action_id,
                status="completed" if result.success else "failed",
                message=result.output if hasattr(result, 'output') else str(result),
                findings=result.findings if hasattr(result, 'findings') else [],
                execution_time=result.execution_time if hasattr(result, 'execution_time') else 0
            )
            
        except Exception as e:
            logger.error(f"Execution with approval failed: {e}")
            await self._handle_execution_error(action, e, session_id)
            raise

    async def _wait_for_approval(
        self,
        request: ApprovalRequest,
        timeout_seconds: int = 3600
    ) -> 'ApprovalResult':
        """
        승인 대기 (폴링 방식)
        
        구현 옵션:
        - Option A: 폴링 (현재 구현)
        - Option B: WebSocket (향후 개선)
        - Option C: Redis Pub/Sub (분산 환경)
        """
        poll_interval = 5  # 5초마다 확인
        elapsed = 0
        
        while elapsed < timeout_seconds:
            status = await self.approval_workflow.check_request_status(
                request.request_id
            )
            
            if status.value != 'pending':
                return status
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        # 타임아웃 처리
        await self.approval_workflow.timeout_request(request.request_id)
        from .approval_workflow import ApprovalResult
        return ApprovalResult.TIMEOUT

    async def _log_execution(self, action: SecurityAction, result, session_id: str):
        """실행 결과 로깅"""
        try:
            logger.info(
                f"Action executed: {action.action_id} in session {session_id} -> "
                f"success={getattr(result, 'success', False)}"
            )
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")

    async def _handle_execution_error(self, action: SecurityAction, error: Exception, session_id: str):
        """실행 오류 처리"""
        try:
            logger.error(
                f"Action {action.action_id} failed in session {session_id}: {error}"
            )
        except Exception as e:
            logger.error(f"Failed to handle execution error: {e}")

    async def batch_execute_with_approval(
        self,
        actions: List[SecurityAction],
        tool_executor: BaseSecurityTool,
        session_id: str,
        batch_approval: bool = True
    ) -> List['ExecutionResult']:
        """
        배치 작업 승인 및 실행
        
        Args:
            actions: 실행할 작업 목록
            tool_executor: 보안 도구 실행기
            session_id: 세션 식별자
            batch_approval: True면 일괄 승인, False면 개별 승인
        """
        if batch_approval:
            # 가장 높은 위험도로 일괄 승인 요청
            max_risk = max(a.risk_level for a in actions)
            batch_action = SecurityAction(
                action_id=generate_action_id(),
                action_type="batch_execution",
                risk_level=max_risk,
                parameters={"batch_size": len(actions)}
            )
            
            # Mock executor for approval check only
            class MockExecutor:
                async def execute(self, target, params):
                    class MockResult:
                        success = True
                    return MockResult()
            
            approval = await self.execute_with_approval(
                batch_action, 
                MockExecutor(),
                session_id
            )
            
            if not approval.success:
                return [ExecutionResult(
                    success=False,
                    action_id=a.action_id,
                    status="batch_denied",
                    message="Batch approval denied"
                ) for a in actions]
        
        # 개별 실행
        results = []
        for action in actions:
            try:
                result = await self.execute_with_approval(action, tool_executor, session_id)
                results.append(result)
            except Exception as e:
                results.append(ExecutionResult(
                    success=False,
                    action_id=action.action_id,
                    status="failed",
                    message=str(e)
                ))
        
        return results

    async def execute_with_approval_check(
        self,
        tool: BaseSecurityTool,
        target: str,
        options: Dict[str, Any] = None,
        requested_by: str = "system",
        justification: str = "",
        auto_approve_timeout: int = 300  # 5분
    ) -> ToolResult:
        """
        승인 검증 후 도구 실행
        
        Args:
            tool: 보안 도구 인스턴스
            target: 대상
            options: 도구 옵션
            requested_by: 요청자
            justification: 요청 사유
            auto_approve_timeout: 자동 승인 대기 시간(초)
            
        Returns:
            ToolResult: 도구 실행 결과
        """
        options = options or {}
        
        try:
            # SecurityAction 생성
            action = SecurityAction(
                action_id=generate_action_id(),
                action_type=f"{tool.tool_name}_scan",
                target=target,
                tool_name=tool.tool_name,
                command=" ".join(tool.build_command(target, options)),
                phase=options.get("phase", PentestPhase.SCANNING),
                risk_level=options.get("risk_level", RiskLevel.LOW),
                requires_network=True,
                is_destructive=options.get("is_destructive", False)
            )
            
            # 승인 요청 (필요시)
            approval_request = await self.request_approval_if_needed(
                action=action,
                requested_by=requested_by,
                justification=justification,
                context={"target": target, "options": options}
            )
            
            # 승인 대기 (필요시)
            if approval_request:
                logger.info(f"Waiting for approval for action {action.action_id}")
                
                approval_result = await self._wait_for_approval(
                    approval_request,
                    timeout=auto_approve_timeout
                )
                
                if approval_result != ApprovalResult.APPROVED:
                    raise PermissionError(
                        f"Action {action.action_id} was not approved: {approval_result.value}"
                    )
                
                logger.info(f"Action {action.action_id} approved, proceeding with execution")
            
            # 도구 실행
            result = await tool.execute(target, options)
            
            # 실행 결과 기록
            await self._record_execution_result(action, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute tool with approval check: {str(e)}")
            raise
    
    async def integrate_with_ptt(
        self,
        task_id: str,
        action: SecurityAction,
        requested_by: str = "ptt_system"
    ) -> bool:
        """
        PTT 작업과 승인 프로세스 통합
        
        Args:
            task_id: PTT 작업 ID
            action: 보안 작업
            requested_by: 요청자
            
        Returns:
            bool: 실행 가능 여부 (승인됨 또는 승인 불필요)
        """
        try:
            # PTT 작업 정보를 포함한 컨텍스트 생성
            context = {
                "ptt_task_id": task_id,
                "source": "ptt_system",
                "automated": True
            }
            
            # 승인 요청 (필요시)
            approval_request = await self.request_approval_if_needed(
                action=action,
                requested_by=requested_by,
                justification=f"Automated PTT task execution: {task_id}",
                context=context
            )
            
            if approval_request:
                logger.info(
                    f"PTT task {task_id} requires approval: {approval_request.request_id}"
                )
                # PTT에서는 즉시 실행하지 않고 승인 대기 상태로 설정
                return False
            
            # 승인 불필요하거나 이미 승인됨
            return True
            
        except Exception as e:
            logger.error(f"Failed to integrate PTT task with approval: {str(e)}")
            return False
    
    async def bulk_approve_low_risk_actions(
        self,
        actions: List[SecurityAction],
        approver_id: str = "system"
    ) -> Dict[str, bool]:
        """
        저위험 작업들의 일괄 승인
        
        Args:
            actions: 승인할 작업 목록
            approver_id: 승인자 ID
            
        Returns:
            Dict[str, bool]: 작업별 승인 결과
        """
        results = {}
        
        for action in actions:
            try:
                # 저위험 작업인지 확인
                if action.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]:
                    if action.tool_name and action.tool_name.lower() in self.auto_approve_tools:
                        # 자동 승인 생성
                        approval_request = ApprovalRequest(
                            request_id=generate_action_id(),
                            action=action,
                            risk_assessment=None,  # 간단한 평가 사용
                            requested_by="system",
                            justification="Automated approval for low-risk action"
                        )
                        
                        result = await self.approval_workflow.process_approval(
                            request_id=approval_request.request_id,
                            approved=True,
                            approver_id=approver_id,
                            reason="Automated approval for low-risk action"
                        )
                        
                        results[action.action_id] = (result == ApprovalResult.APPROVED)
                    else:
                        results[action.action_id] = False
                else:
                    results[action.action_id] = False
                    
            except Exception as e:
                logger.error(f"Failed to auto-approve action {action.action_id}: {str(e)}")
                results[action.action_id] = False
        
        return results
    
    async def get_approval_stats(self) -> Dict[str, Any]:
        """승인 워크플로우 통계 조회"""
        try:
            from sqlalchemy import select, func
            from ..models.models import HumanApproval
            
            # 기본 통계 쿼리
            total_requests = await self.db.execute(
                select(func.count(HumanApproval.id))
            )
            total_count = total_requests.scalar() or 0
            
            # 상태별 통계
            status_stats = await self.db.execute(
                select(
                    HumanApproval.status,
                    func.count(HumanApproval.id)
                ).group_by(HumanApproval.status)
            )
            
            status_counts = dict(status_stats.fetchall())
            
            # 위험도별 통계
            risk_stats = await self.db.execute(
                select(
                    HumanApproval.risk_level,
                    func.count(HumanApproval.id)
                ).group_by(HumanApproval.risk_level)
            )
            
            risk_counts = dict(risk_stats.fetchall())
            
            return {
                "total_requests": total_count,
                "status_distribution": status_counts,
                "risk_distribution": risk_counts,
                "pending_count": status_counts.get("pending", 0),
                "approved_count": status_counts.get("approved", 0),
                "denied_count": status_counts.get("denied", 0),
                "timeout_count": status_counts.get("timeout", 0),
                "auto_approval_rate": self._calculate_auto_approval_rate(status_counts),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get approval stats: {str(e)}")
            return {"error": str(e)}
    
    # Private methods
    
    async def _wait_for_approval(
        self,
        approval_request: ApprovalRequest,
        timeout: int = 300
    ) -> ApprovalResult:
        """승인 결과 대기"""
        
        start_time = datetime.now(timezone.utc)
        
        while True:
            # 현재 상태 확인
            if approval_request.status != ApprovalResult.PENDING:
                return approval_request.status
            
            # 타임아웃 확인
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= timeout:
                return ApprovalResult.TIMEOUT
            
            # 짧은 대기 후 재확인
            await asyncio.sleep(5)
            
            # 데이터베이스에서 최신 상태 조회
            # (실제 구현에서는 approval_request 객체를 새로고침해야 함)
            
    async def _record_execution_result(
        self,
        action: SecurityAction,
        result: ToolResult
    ):
        """실행 결과 기록"""
        try:
            # 감사 로그 기록
            # 실제 구현에서는 SecurityAuditLog 모델 사용
            logger.info(
                f"Tool execution completed: {action.action_id} -> "
                f"success={result.success}, findings={len(result.findings)}"
            )
            
        except Exception as e:
            logger.error(f"Failed to record execution result: {str(e)}")
    
    def _calculate_auto_approval_rate(self, status_counts: Dict[str, int]) -> float:
        """자동 승인율 계산"""
        total = sum(status_counts.values())
        if total == 0:
            return 0.0
        
        # 자동 승인은 'approved' 상태 중에서 시스템이 승인한 것
        # 실제로는 더 정확한 구분이 필요
        approved = status_counts.get("approved", 0)
        return (approved / total) * 100.0


class SecurityToolWrapper:
    """
    승인 검증이 통합된 보안 도구 래퍼
    
    기존 보안 도구에 승인 워크플로우를 자동으로 통합
    """
    
    def __init__(
        self,
        tool: BaseSecurityTool,
        approval_manager: ApprovalIntegrationManager,
        requested_by: str = "system"
    ):
        """
        Args:
            tool: 래핑할 보안 도구
            approval_manager: 승인 통합 관리자
            requested_by: 기본 요청자
        """
        self.tool = tool
        self.approval_manager = approval_manager
        self.requested_by = requested_by
    
    async def execute(
        self,
        target: str,
        options: Dict[str, Any] = None,
        justification: str = "",
        skip_approval: bool = False
    ) -> ToolResult:
        """
        승인 검증 후 도구 실행
        
        Args:
            target: 대상
            options: 도구 옵션
            justification: 실행 사유
            skip_approval: 승인 건너뛰기 (위험!)
            
        Returns:
            ToolResult: 실행 결과
        """
        if skip_approval:
            logger.warning(f"Skipping approval check for {self.tool.tool_name}")
            return await self.tool.execute(target, options)
        
        # Convert to SecurityAction
        action = SecurityAction(
            action_id=generate_action_id(),
            action_type=f"{self.tool.tool_name}_execution",
            target=target,
            tool_name=self.tool.tool_name,
            parameters=options or {},
            risk_level=options.get('risk_level', RiskLevel.LOW)
        )
        
        result = await self.approval_manager.execute_with_approval(
            action=action,
            tool_executor=self.tool,
            session_id=options.get('session_id', 'default')
        )
        
        # Convert ExecutionResult back to ToolResult format
        return self._convert_to_tool_result(result)
    
    def _convert_to_tool_result(self, execution_result: 'ExecutionResult') -> ToolResult:
        """Convert ExecutionResult to ToolResult"""
        return ToolResult(
            success=execution_result.success,
            output=execution_result.message,
            findings=execution_result.findings,
            execution_time=execution_result.execution_time
        )
    
    def __getattr__(self, name):
        """다른 메서드들은 원본 도구로 위임"""
        return getattr(self.tool, name)