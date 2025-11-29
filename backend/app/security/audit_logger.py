"""
MMCODE Security Platform - Security Audit Logger
================================================

불변 감사 로그 시스템
- 모든 보안 작업의 완전한 추적
- 해시 체인 기반 무결성 검증
- 다중 백엔드 지원 (파일, DB)

Version: 2.0.0
"""

import json
import hashlib
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .models import SecurityAction, ValidationResult, HumanApproval

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """감사 이벤트 타입"""
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    ACTION_PROPOSED = "action_proposed"
    ACTION_APPROVED = "action_approved"
    ACTION_DENIED = "action_denied"
    ACTION_EXECUTED = "action_executed"
    SCOPE_VALIDATION = "scope_validation"
    SCOPE_VIOLATION = "scope_violation"
    TOOL_EXECUTION = "tool_execution"
    FINDING_DISCOVERED = "finding_discovered"
    HUMAN_INTERVENTION = "human_intervention"
    PHASE_TRANSITION = "phase_transition"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class AuditEvent:
    """감사 이벤트"""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    session_id: str
    
    # 이벤트 상세
    details: Dict[str, Any] = field(default_factory=dict)
    
    # 컨텍스트
    actor_type: str = "system"  # system, human, agent
    actor_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # 보안
    integrity_hash: Optional[str] = None
    previous_hash: Optional[str] = None
    
    # 메타데이터
    severity: str = "info"
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """해시 계산"""
        if not self.integrity_hash:
            self.integrity_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """이벤트 무결성 해시 계산"""
        content = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "details": self.details,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
        }
        
        # 이전 해시 포함 (체인 구성)
        if self.previous_hash:
            content["previous_hash"] = self.previous_hash
        
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """무결성 검증"""
        calculated_hash = self._calculate_hash()
        return calculated_hash == self.integrity_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "details": self.details,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "integrity_hash": self.integrity_hash,
            "previous_hash": self.previous_hash,
            "severity": self.severity,
            "tags": self.tags,
        }


class SecurityAuditLogger:
    """
    보안 감사 로거
    
    모든 보안 관련 이벤트를 불변 로그에 기록
    해시 체인을 통한 무결성 보장
    """
    
    def __init__(
        self,
        session_id: str,
        backend: str = "file",
        log_file: Optional[str] = None,
        db_connection = None
    ):
        self.session_id = session_id
        self.backend = backend
        self.log_file = log_file or f"audit_{session_id}.jsonl"
        self.db_connection = db_connection
        
        # 해시 체인 관리
        self._last_hash: Optional[str] = None
        self._event_count = 0
        
        # 통계
        self._events_by_type: Dict[str, int] = {}
        self._total_events = 0
    
    async def log_session_event(
        self,
        event_type: AuditEventType,
        details: Dict[str, Any],
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        severity: str = "info",
        tags: List[str] = None
    ) -> str:
        """세션 이벤트 로깅"""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            session_id=self.session_id,
            details=details,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=correlation_id,
            previous_hash=self._last_hash,
            severity=severity,
            tags=tags or []
        )
        
        await self._write_event(event)
        return event.event_id
    
    async def log_scope_validation(
        self,
        action: SecurityAction,
        validation_result: ValidationResult,
        correlation_id: Optional[str] = None
    ) -> str:
        """스코프 검증 이벤트 로깅"""
        event_type = (
            AuditEventType.SCOPE_VIOLATION 
            if not validation_result.valid 
            else AuditEventType.SCOPE_VALIDATION
        )
        
        severity = "critical" if not validation_result.valid else "info"
        
        details = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "target": action.target,
            "tool_name": action.tool_name,
            "validation_result": validation_result.to_dict(),
        }
        
        return await self.log_session_event(
            event_type=event_type,
            details=details,
            correlation_id=correlation_id,
            severity=severity,
            tags=["scope_validation", action.action_type]
        )
    
    async def log_action_execution(
        self,
        action: SecurityAction,
        approval: Optional[HumanApproval],
        status: str,
        result_details: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> str:
        """작업 실행 이벤트 로깅"""
        details = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "target": action.target,
            "tool_name": action.tool_name,
            "command": action.command,
            "status": status,
            "result": result_details,
        }
        
        if approval:
            details["approval"] = {
                "granted": approval.granted,
                "approver": approval.approver,
                "approved_at": approval.approved_at.isoformat(),
                "conditions": approval.conditions,
            }
        
        severity = "warning" if status == "failed" else "info"
        
        return await self.log_session_event(
            event_type=AuditEventType.ACTION_EXECUTED,
            details=details,
            actor_type="human" if approval else "system",
            actor_id=approval.approver if approval else None,
            correlation_id=correlation_id,
            severity=severity,
            tags=["action_execution", action.action_type, status]
        )
    
    async def log_human_approval(
        self,
        action: SecurityAction,
        approval: HumanApproval,
        correlation_id: Optional[str] = None
    ) -> str:
        """인간 승인 이벤트 로깅"""
        event_type = (
            AuditEventType.ACTION_APPROVED 
            if approval.granted 
            else AuditEventType.ACTION_DENIED
        )
        
        details = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "target": action.target,
            "approval_details": {
                "granted": approval.granted,
                "approver": approval.approver,
                "approved_at": approval.approved_at.isoformat(),
                "conditions": approval.conditions,
                "reason": approval.reason,
            }
        }
        
        return await self.log_session_event(
            event_type=event_type,
            details=details,
            actor_type="human",
            actor_id=approval.approver,
            correlation_id=correlation_id,
            tags=["human_approval", action.action_type]
        )
    
    async def log_tool_execution(
        self,
        tool_name: str,
        command: str,
        target: Optional[str],
        status: str,
        output_summary: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """도구 실행 이벤트 로깅"""
        details = {
            "tool_name": tool_name,
            "command": command,
            "target": target,
            "status": status,
            "output_summary": output_summary,
        }
        
        severity = "warning" if status == "failed" else "info"
        
        return await self.log_session_event(
            event_type=AuditEventType.TOOL_EXECUTION,
            details=details,
            correlation_id=correlation_id,
            severity=severity,
            tags=["tool_execution", tool_name, status]
        )
    
    async def log_emergency_stop(
        self,
        reason: str,
        stopped_by: str,
        correlation_id: Optional[str] = None
    ) -> str:
        """비상 정지 이벤트 로깅"""
        details = {
            "reason": reason,
            "stopped_by": stopped_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        return await self.log_session_event(
            event_type=AuditEventType.EMERGENCY_STOP,
            details=details,
            actor_type="human",
            actor_id=stopped_by,
            correlation_id=correlation_id,
            severity="critical",
            tags=["emergency", "stop"]
        )
    
    async def _write_event(self, event: AuditEvent):
        """이벤트 저장"""
        # 해시 체인 업데이트
        self._last_hash = event.integrity_hash
        self._event_count += 1
        
        # 통계 업데이트
        self._events_by_type[event.event_type.value] = (
            self._events_by_type.get(event.event_type.value, 0) + 1
        )
        self._total_events += 1
        
        # 백엔드별 저장
        if self.backend == "file":
            await self._write_to_file(event)
        elif self.backend == "database":
            await self._write_to_database(event)
        elif self.backend == "both":
            await asyncio.gather(
                self._write_to_file(event),
                self._write_to_database(event)
            )
        
        logger.info(f"Audit event logged: {event.event_type.value} ({event.event_id})")
    
    async def _write_to_file(self, event: AuditEvent):
        """파일에 이벤트 저장"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit event to file: {e}")
    
    async def _write_to_database(self, event: AuditEvent):
        """데이터베이스에 이벤트 저장"""
        if not self.db_connection:
            logger.warning("Database connection not available for audit logging")
            return
        
        # TODO: 실제 DB 연결 및 저장 로직 구현
        try:
            # 예시 SQL
            query = """
                INSERT INTO security_audit_log 
                (event_id, event_type, timestamp, session_id, details, 
                 actor_type, actor_id, correlation_id, integrity_hash, 
                 previous_hash, severity, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # await self.db_connection.execute(query, event.to_tuple())
            pass
        except Exception as e:
            logger.error(f"Failed to write audit event to database: {e}")
    
    def _generate_event_id(self) -> str:
        """고유 이벤트 ID 생성"""
        return f"evt_{uuid.uuid4().hex[:12]}"
    
    async def verify_chain_integrity(self) -> bool:
        """감사 로그 체인 무결성 검증"""
        if self.backend != "file":
            logger.warning("Chain verification only supported for file backend")
            return False
        
        try:
            previous_hash = None
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    event_data = json.loads(line.strip())
                    
                    # 이벤트 무결성 검증
                    event = AuditEvent(**{
                        k: v for k, v in event_data.items() 
                        if k not in ['integrity_hash']
                    })
                    
                    if not event.verify_integrity():
                        logger.error(f"Integrity check failed at line {line_num}")
                        return False
                    
                    # 체인 연결 검증
                    if previous_hash != event.previous_hash:
                        logger.error(f"Chain break detected at line {line_num}")
                        return False
                    
                    previous_hash = event.integrity_hash
            
            logger.info("Audit log chain integrity verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Chain verification failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """감사 로그 통계"""
        return {
            "session_id": self.session_id,
            "total_events": self._total_events,
            "events_by_type": self._events_by_type.copy(),
            "last_hash": self._last_hash,
            "backend": self.backend,
            "log_file": self.log_file,
        }
    
    async def search_events(
        self,
        event_types: Optional[List[AuditEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """이벤트 검색"""
        if self.backend != "file":
            logger.warning("Event search only supported for file backend")
            return []
        
        events = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    event_data = json.loads(line.strip())
                    
                    # 필터링 조건 적용
                    if event_types and event_data["event_type"] not in [et.value for et in event_types]:
                        continue
                    
                    event_time = datetime.fromisoformat(event_data["timestamp"].replace('Z', '+00:00'))
                    if start_time and event_time < start_time:
                        continue
                    if end_time and event_time > end_time:
                        continue
                    
                    if actor_id and event_data.get("actor_id") != actor_id:
                        continue
                    
                    if correlation_id and event_data.get("correlation_id") != correlation_id:
                        continue
                    
                    # AuditEvent 객체 생성
                    event_data["event_type"] = AuditEventType(event_data["event_type"])
                    event_data["timestamp"] = event_time
                    events.append(AuditEvent(**event_data))
                    
                    if len(events) >= limit:
                        break
                        
        except Exception as e:
            logger.error(f"Event search failed: {e}")
        
        return events


# 팩토리 함수
def create_audit_logger(
    session_id: str,
    backend: str = "file",
    log_file: Optional[str] = None,
    db_connection = None
) -> SecurityAuditLogger:
    """
    감사 로거 생성
    
    Args:
        session_id: 세션 ID
        backend: 저장 백엔드 ("file", "database", "both")
        log_file: 로그 파일 경로 (파일 백엔드용)
        db_connection: DB 연결 (DB 백엔드용)
    
    Returns:
        SecurityAuditLogger 인스턴스
    """
    return SecurityAuditLogger(
        session_id=session_id,
        backend=backend,
        log_file=log_file,
        db_connection=db_connection
    )