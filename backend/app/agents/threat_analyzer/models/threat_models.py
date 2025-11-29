"""
ThreatAnalyzer Agent Models
===========================

PentestGPT 스타일 위협 분석 모델
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ....security.models import (
    SecurityFinding,
    TaskNode,
    PentestPhase,
    RiskLevel,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """태스크 상태"""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class TaskRecommendation:
    """다음 수행 작업 추천"""
    task: Optional[TaskNode]
    guidance: str
    tools_required: List[str]
    estimated_duration_seconds: int
    risk_level: RiskLevel
    requires_approval: bool
    
    # 추가 정보
    rationale: str = ""
    prerequisites: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggested_commands: List[str] = field(default_factory=list)
    
    # 대안
    alternatives: List['TaskRecommendation'] = field(default_factory=list)
    
    # 페이즈 전환 관련
    is_phase_transition: bool = False
    suggested_next_phase: Optional[PentestPhase] = None
    phase_completion_summary: str = ""


@dataclass
class TaskResult:
    """태스크 실행 결과"""
    task_id: str
    status: str
    findings: List[SecurityFinding]
    raw_output: Optional[str]
    execution_time_seconds: float
    
    # 새로 발견된 정보
    new_targets: List[str] = field(default_factory=list)
    new_services: List[Dict[str, Any]] = field(default_factory=list)
    credentials_found: List[Dict[str, Any]] = field(default_factory=list)
    
    # 에러 정보
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)


class PentestingTaskTree:
    """
    Pentesting Task Tree (PTT)
    
    PentestGPT 스타일의 작업 트리 관리
    - 페이즈별 작업 구조화
    - 동적 태스크 생성
    - 발견사항 기반 확장
    """
    
    def __init__(
        self,
        target: str,
        scope,  # EngagementScope
        objectives: List[str]
    ):
        self.tree_id = f"ptt_{uuid.uuid4().hex[:12]}"
        self.target = target
        self.scope = scope
        self.objectives = objectives
        
        # 태스크 저장소
        self._tasks: Dict[str, TaskNode] = {}
        self._root_tasks: List[str] = []
        
        # 페이즈 관리
        self.current_phase = PentestPhase.RECONNAISSANCE
        self._phase_order = [
            PentestPhase.RECONNAISSANCE,
            PentestPhase.SCANNING,
            PentestPhase.ENUMERATION,
            PentestPhase.VULNERABILITY_ASSESSMENT,
            PentestPhase.EXPLOITATION,
            PentestPhase.POST_EXPLOITATION,
            PentestPhase.REPORTING,
        ]
        
        # 발견사항 추적
        self.findings: List[SecurityFinding] = []
        
        # 메타데이터
        self.created_at = datetime.now(timezone.utc)
        self.last_updated = self.created_at
    
    def add_task(
        self,
        task: TaskNode,
        parent_id: Optional[str] = None
    ) -> str:
        """태스크 추가"""
        self._tasks[task.id] = task
        
        if parent_id and parent_id in self._tasks:
            task.parent_id = parent_id
            parent = self._tasks[parent_id]
            parent.children_ids.append(task.id)
        else:
            self._root_tasks.append(task.id)
        
        self.last_updated = datetime.now(timezone.utc)
        return task.id
    
    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """태스크 조회"""
        return self._tasks.get(task_id)
    
    def get_available_tasks(self) -> List[TaskNode]:
        """실행 가능한 태스크 목록"""
        available = []
        for task in self._tasks.values():
            if task.status == "available" and task.phase == self.current_phase:
                available.append(task)
        return sorted(available, key=lambda t: -t.priority_score)
    
    def get_tasks_by_phase(self, phase: PentestPhase) -> List[TaskNode]:
        """페이즈별 태스크 조회"""
        return [t for t in self._tasks.values() if t.phase == phase]
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[TaskResult] = None
    ):
        """태스크 상태 업데이트"""
        if task_id not in self._tasks:
            return
        
        task = self._tasks[task_id]
        task.status = status
        
        if status == "in_progress":
            task.started_at = datetime.now(timezone.utc)
        elif status == "completed":
            task.completed_at = datetime.now(timezone.utc)
            if result and result.findings:
                task.findings.extend(result.findings)
                self.findings.extend(result.findings)
        
        self.last_updated = datetime.now(timezone.utc)
    
    def can_advance_phase(self) -> Tuple[bool, str]:
        """다음 페이즈로 진행 가능한지 확인"""
        current_tasks = self.get_tasks_by_phase(self.current_phase)
        
        if not current_tasks:
            return False, "No tasks defined for current phase"
        
        completed = sum(1 for t in current_tasks if t.status == "completed")
        total = len(current_tasks)
        
        # 최소 80% 완료 필요
        if completed / total < 0.8:
            return False, f"Only {completed}/{total} tasks completed in {self.current_phase.value}"
        
        return True, f"Phase {self.current_phase.value} ready for advancement"
    
    def advance_phase(self) -> Optional[PentestPhase]:
        """다음 페이즈로 진행"""
        can_advance, reason = self.can_advance_phase()
        if not can_advance:
            logger.warning(f"Cannot advance phase: {reason}")
            return None
        
        current_idx = self._phase_order.index(self.current_phase)
        if current_idx < len(self._phase_order) - 1:
            self.current_phase = self._phase_order[current_idx + 1]
            self.last_updated = datetime.now(timezone.utc)
            return self.current_phase
        
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """PTT 요약"""
        tasks_by_phase = {}
        for phase in self._phase_order:
            tasks = self.get_tasks_by_phase(phase)
            tasks_by_phase[phase.value] = {
                "total": len(tasks),
                "completed": sum(1 for t in tasks if t.status == "completed"),
                "failed": sum(1 for t in tasks if t.status == "failed"),
            }
        
        return {
            "tree_id": self.tree_id,
            "target": self.target,
            "current_phase": self.current_phase.value,
            "total_tasks": len(self._tasks),
            "total_findings": len(self.findings),
            "tasks_by_phase": tasks_by_phase,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }