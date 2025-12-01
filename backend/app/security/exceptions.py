"""
MMCODE Security Platform - Exception Handling System
====================================================

보안 플랫폼 예외 처리 및 오류 복구 시스템
- 구조화된 예외 클래스
- 자동 복구 메커니즘
- 에러 추적 및 로깅

Version: 1.0.0
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """오류 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RecoveryResult:
    """복구 결과"""
    success: bool
    action: str  # "retry", "escalate", "abort", "use_alternative"
    message: str
    metadata: Optional[Dict[str, Any]] = None


class SecurityPlatformException(Exception):
    """보안 플랫폼 기본 예외"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.recoverable = recoverable
        self.severity = severity
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": str(self),
            "details": self.details,
            "recoverable": self.recoverable,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat()
        }


# 승인 관련 예외
class ApprovalException(SecurityPlatformException):
    """승인 관련 예외"""
    pass


class ApprovalTimeoutException(ApprovalException):
    """승인 타임아웃"""
    
    def __init__(self, request_id: str, timeout_seconds: int):
        super().__init__(
            message=f"Approval request {request_id} timed out after {timeout_seconds}s",
            error_code="APPROVAL_TIMEOUT",
            details={
                "request_id": request_id,
                "timeout_seconds": timeout_seconds
            },
            recoverable=True,
            severity=ErrorSeverity.HIGH
        )


class ApprovalDeniedException(ApprovalException):
    """승인 거부"""
    
    def __init__(self, request_id: str, reason: str):
        super().__init__(
            message=f"Approval request {request_id} was denied: {reason}",
            error_code="APPROVAL_DENIED",
            details={
                "request_id": request_id,
                "denial_reason": reason
            },
            recoverable=False,
            severity=ErrorSeverity.MEDIUM
        )


class ApprovalNotConfiguredException(ApprovalException):
    """승인 시스템 미설정"""
    
    def __init__(self):
        super().__init__(
            message="Approval system is not properly configured",
            error_code="APPROVAL_NOT_CONFIGURED",
            recoverable=False,
            severity=ErrorSeverity.HIGH
        )


# 실행 관련 예외
class ExecutionException(SecurityPlatformException):
    """작업 실행 예외"""
    pass


class ToolExecutionException(ExecutionException):
    """도구 실행 실패"""
    
    def __init__(
        self, 
        tool_name: str, 
        command: str, 
        error: str,
        exit_code: Optional[int] = None
    ):
        super().__init__(
            message=f"Tool {tool_name} execution failed: {error}",
            error_code="TOOL_EXECUTION_FAILED",
            details={
                "tool_name": tool_name,
                "command": command,
                "exit_code": exit_code,
                "error": error
            },
            recoverable=True,
            severity=ErrorSeverity.MEDIUM
        )


class ToolNotFoundException(ExecutionException):
    """도구 찾을 수 없음"""
    
    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Security tool '{tool_name}' not found or not available",
            error_code="TOOL_NOT_FOUND",
            details={"tool_name": tool_name},
            recoverable=True,
            severity=ErrorSeverity.MEDIUM
        )


class ToolTimeoutException(ExecutionException):
    """도구 실행 타임아웃"""
    
    def __init__(self, tool_name: str, timeout_seconds: int):
        super().__init__(
            message=f"Tool {tool_name} execution timed out after {timeout_seconds}s",
            error_code="TOOL_TIMEOUT",
            details={
                "tool_name": tool_name,
                "timeout_seconds": timeout_seconds
            },
            recoverable=True,
            severity=ErrorSeverity.MEDIUM
        )


# 범위 및 보안 예외
class ScopeViolationException(SecurityPlatformException):
    """범위 위반 예외 (복구 불가)"""
    
    def __init__(self, target: str, allowed_scope: List[str], violation_type: str = "unknown"):
        super().__init__(
            message=f"Target {target} is outside allowed scope",
            error_code="SCOPE_VIOLATION",
            details={
                "target": target,
                "allowed_scope": allowed_scope,
                "violation_type": violation_type
            },
            recoverable=False,  # 복구 불가
            severity=ErrorSeverity.CRITICAL
        )


class SecurityPolicyViolationException(SecurityPlatformException):
    """보안 정책 위반"""
    
    def __init__(self, policy_name: str, violation_details: str):
        super().__init__(
            message=f"Security policy violation: {policy_name}",
            error_code="SECURITY_POLICY_VIOLATION",
            details={
                "policy_name": policy_name,
                "violation_details": violation_details
            },
            recoverable=False,
            severity=ErrorSeverity.CRITICAL
        )


# 세션 관련 예외
class SessionException(SecurityPlatformException):
    """세션 관련 예외"""
    pass


class SessionNotFoundError(SessionException):
    """세션을 찾을 수 없음"""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session {session_id} not found",
            error_code="SESSION_NOT_FOUND",
            details={"session_id": session_id},
            recoverable=False,
            severity=ErrorSeverity.MEDIUM
        )


class SessionExpiredException(SessionException):
    """세션 만료"""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session {session_id} has expired",
            error_code="SESSION_EXPIRED",
            details={"session_id": session_id},
            recoverable=False,
            severity=ErrorSeverity.MEDIUM
        )


class SessionStateException(SessionException):
    """세션 상태 오류"""
    
    def __init__(self, session_id: str, current_state: str, required_state: str):
        super().__init__(
            message=f"Session {session_id} is in {current_state} state, but {required_state} is required",
            error_code="SESSION_INVALID_STATE",
            details={
                "session_id": session_id,
                "current_state": current_state,
                "required_state": required_state
            },
            recoverable=True,
            severity=ErrorSeverity.MEDIUM
        )


# 작업 관련 예외
class TaskException(SecurityPlatformException):
    """작업 관련 예외"""
    pass


class TaskNotFoundError(TaskException):
    """작업을 찾을 수 없음"""
    
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task {task_id} not found",
            error_code="TASK_NOT_FOUND",
            details={"task_id": task_id},
            recoverable=False,
            severity=ErrorSeverity.MEDIUM
        )


class UnsupportedToolError(TaskException):
    """지원되지 않는 도구"""
    
    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Tool {tool_name} is not supported",
            error_code="UNSUPPORTED_TOOL",
            details={"tool_name": tool_name},
            recoverable=True,
            severity=ErrorSeverity.MEDIUM
        )


# 알림 관련 예외
class NotificationException(SecurityPlatformException):
    """알림 관련 예외"""
    pass


class NotificationDeliveryException(NotificationException):
    """알림 발송 실패"""
    
    def __init__(self, channel: str, reason: str):
        super().__init__(
            message=f"Failed to send notification via {channel}: {reason}",
            error_code="NOTIFICATION_DELIVERY_FAILED",
            details={
                "channel": channel,
                "reason": reason
            },
            recoverable=True,
            severity=ErrorSeverity.MEDIUM
        )


# 오류 복구 핸들러
class ErrorRecoveryHandler:
    """오류 복구 관리자"""
    
    def __init__(self, audit_logger=None):
        self.audit_logger = audit_logger
        self.recovery_strategies: Dict[str, Callable] = {
            "APPROVAL_TIMEOUT": self._handle_approval_timeout,
            "TOOL_EXECUTION_FAILED": self._handle_tool_failure,
            "TOOL_NOT_FOUND": self._handle_tool_not_found,
            "TOOL_TIMEOUT": self._handle_tool_timeout,
            "SCOPE_VIOLATION": self._handle_scope_violation,
            "SESSION_NOT_FOUND": self._handle_session_not_found,
            "NOTIFICATION_DELIVERY_FAILED": self._handle_notification_failure,
        }
    
    async def handle_error(
        self,
        exception: SecurityPlatformException,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        오류 처리 및 복구 시도
        
        Args:
            exception: 발생한 예외
            context: 오류 컨텍스트
            
        Returns:
            RecoveryResult: 복구 결과
        """
        # 감사 로그 기록
        if self.audit_logger:
            await self._log_error(exception, context)
        
        # 복구 가능 여부 확인
        if not exception.recoverable:
            return RecoveryResult(
                success=False,
                action="abort",
                message="Non-recoverable error occurred",
                metadata={"error_code": exception.error_code}
            )
        
        # 복구 전략 실행
        strategy = self.recovery_strategies.get(exception.error_code)
        if strategy:
            try:
                return await strategy(exception, context)
            except Exception as e:
                logger.error(f"Recovery strategy failed: {e}")
                return RecoveryResult(
                    success=False,
                    action="abort",
                    message=f"Recovery strategy failed: {e}"
                )
        
        # 기본 복구: 재시도 권장
        return RecoveryResult(
            success=False,
            action="retry_recommended",
            message="No specific recovery strategy, retry recommended",
            metadata={"retry_delay": 30}  # 30초 후 재시도
        )
    
    async def _handle_approval_timeout(
        self,
        exception: ApprovalTimeoutException,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """승인 타임아웃 복구"""
        # 에스컬레이션 시도
        return RecoveryResult(
            success=True,
            action="escalate",
            message="Escalating to higher authority",
            metadata={
                "escalation_level": "security_manager",
                "original_request_id": exception.details.get("request_id"),
                "escalation_timeout": 1800  # 30분
            }
        )
    
    async def _handle_tool_failure(
        self,
        exception: ToolExecutionException,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """도구 실행 실패 복구"""
        tool_name = exception.details.get("tool_name")
        alternatives = self._get_alternative_tools(tool_name)
        
        if alternatives:
            return RecoveryResult(
                success=True,
                action="use_alternative",
                message="Alternative tools available",
                metadata={"alternatives": alternatives}
            )
        else:
            return RecoveryResult(
                success=False,
                action="retry",
                message="No alternatives available, retry with same tool",
                metadata={"retry_count": 1, "retry_delay": 60}
            )
    
    async def _handle_tool_not_found(
        self,
        exception: ToolNotFoundException,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """도구 없음 복구"""
        tool_name = exception.details.get("tool_name")
        alternatives = self._get_alternative_tools(tool_name)
        
        return RecoveryResult(
            success=len(alternatives) > 0,
            action="use_alternative" if alternatives else "abort",
            message="Alternative tools found" if alternatives else "No alternative tools available",
            metadata={"alternatives": alternatives}
        )
    
    async def _handle_tool_timeout(
        self,
        exception: ToolTimeoutException,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """도구 타임아웃 복구"""
        return RecoveryResult(
            success=True,
            action="retry",
            message="Retry with extended timeout",
            metadata={
                "new_timeout": exception.details.get("timeout_seconds", 300) * 2,
                "retry_count": 1
            }
        )
    
    async def _handle_scope_violation(
        self,
        exception: ScopeViolationException,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """범위 위반 처리 (복구 불가)"""
        # 보안 경고 발송
        await self._send_security_alert(exception, context)
        
        return RecoveryResult(
            success=False,
            action="abort_and_alert",
            message="Scope violation detected, session aborted",
            metadata={
                "violation_type": exception.details.get("violation_type"),
                "target": exception.details.get("target")
            }
        )
    
    async def _handle_session_not_found(
        self,
        exception: SessionNotFoundError,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """세션 없음 복구"""
        return RecoveryResult(
            success=True,
            action="create_new_session",
            message="Create new session to continue",
            metadata={
                "original_session_id": exception.details.get("session_id"),
                "suggested_action": "restart_workflow"
            }
        )
    
    async def _handle_notification_failure(
        self,
        exception: NotificationDeliveryException,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """알림 실패 복구"""
        failed_channel = exception.details.get("channel")
        alternative_channels = self._get_alternative_notification_channels(failed_channel)
        
        return RecoveryResult(
            success=len(alternative_channels) > 0,
            action="use_alternative_channel",
            message="Use alternative notification channels",
            metadata={
                "failed_channel": failed_channel,
                "alternative_channels": alternative_channels
            }
        )
    
    def _get_alternative_tools(self, tool_name: str) -> List[str]:
        """대체 도구 목록 반환"""
        tool_alternatives = {
            "nmap": ["masscan", "rustscan"],
            "nuclei": ["nessus", "openvas"],
            "gobuster": ["dirb", "dirbuster"],
            "sqlmap": ["sqlninja", "bbqsql"],
            "metasploit": ["empire", "cobalt_strike"],
            "nikto": ["whatweb", "httprint"],
        }
        return tool_alternatives.get(tool_name.lower(), [])
    
    def _get_alternative_notification_channels(self, failed_channel: str) -> List[str]:
        """대체 알림 채널 목록 반환"""
        if failed_channel == "EMAIL":
            return ["SLACK", "WEBHOOK", "SMS"]
        elif failed_channel == "SLACK":
            return ["EMAIL", "WEBHOOK", "SMS"]
        elif failed_channel == "SMS":
            return ["EMAIL", "SLACK", "WEBHOOK"]
        elif failed_channel == "WEBHOOK":
            return ["EMAIL", "SLACK", "SMS"]
        else:
            return ["EMAIL", "SLACK"]
    
    async def _log_error(self, exception: SecurityPlatformException, context: Dict[str, Any]):
        """오류 로깅"""
        try:
            if self.audit_logger:
                await self.audit_logger.log_error(
                    error_code=exception.error_code,
                    message=str(exception),
                    details=exception.details,
                    context=context,
                    severity=exception.severity.value
                )
            else:
                logger.error(
                    f"Security Platform Error [{exception.error_code}]: {exception}",
                    extra={
                        "error_details": exception.details,
                        "context": context,
                        "severity": exception.severity.value
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    async def _send_security_alert(self, exception: SecurityPlatformException, context: Dict[str, Any]):
        """보안 경고 발송"""
        try:
            # 실제 구현에서는 NotificationManager를 사용하여 긴급 알림 발송
            logger.critical(
                f"SECURITY ALERT: {exception.error_code} - {exception}",
                extra={
                    "alert_type": "scope_violation",
                    "severity": exception.severity.value,
                    "details": exception.details,
                    "context": context
                }
            )
        except Exception as e:
            logger.error(f"Failed to send security alert: {e}")