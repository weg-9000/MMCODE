"""
MMCODE Security Platform - PTT State Persistence
===============================================

PTT 상태의 데이터베이스 저장 및 복원
- 세션 간 상태 유지
- 트리 구조 직렬화/역직렬화
- 점진적 백업 및 복원

Version: 1.0.0
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_

from ..models import (
    TaskNode,
    SecurityFinding,
    PentestPhase,
    RiskLevel,
    EngagementScope
)
from .task_tree import PTTState, TreeExpansionStrategy
from ...models.models import (
    PentestingSession,
    PentestingTask,
    SecurityFinding as DBSecurityFinding
)

logger = logging.getLogger(__name__)


class PTTStatePersistence:
    """
    PTT 상태 영속성 관리자
    
    기능:
    - PTT 상태의 완전한 저장/복원
    - 점진적 업데이트
    - 백업 및 복구
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Args:
            db_session: 데이터베이스 세션
        """
        self.db = db_session
        
    async def save_ptt_state(
        self,
        ptt_state: PTTState,
        session_name: str = None
    ) -> str:
        """
        PTT 상태 완전 저장
        
        Args:
            ptt_state: 저장할 PTT 상태
            session_name: 세션 이름 (None이면 자동 생성)
            
        Returns:
            str: 저장된 세션 ID
        """
        try:
            # 1. PentestingSession 저장/업데이트
            session_id = await self._save_session(ptt_state, session_name)
            
            # 2. 모든 태스크 저장
            await self._save_all_tasks(session_id, ptt_state.all_nodes)
            
            # 3. 발견사항 저장
            await self._save_findings(session_id, ptt_state.findings)
            
            # 4. 메타데이터 저장
            await self._save_metadata(session_id, ptt_state)
            
            await self.db.commit()
            
            logger.info(f"Successfully saved PTT state for session {session_id}")
            return session_id
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to save PTT state: {str(e)}")
            raise
    
    async def load_ptt_state(self, session_id: str) -> Optional[PTTState]:
        """
        PTT 상태 복원
        
        Args:
            session_id: 복원할 세션 ID
            
        Returns:
            PTTState: 복원된 PTT 상태 (없으면 None)
        """
        try:
            # 1. 세션 정보 로드
            session_data = await self._load_session(session_id)
            if not session_data:
                logger.warning(f"Session {session_id} not found")
                return None
            
            # 2. 태스크 트리 복원
            all_nodes = await self._load_all_tasks(session_id)
            
            # 3. 발견사항 복원
            findings = await self._load_findings(session_id)
            
            # 4. PTT 상태 재구성
            ptt_state = await self._reconstruct_ptt_state(
                session_data, all_nodes, findings
            )
            
            logger.info(
                f"Successfully loaded PTT state for session {session_id}: "
                f"{len(all_nodes)} tasks, {len(findings)} findings"
            )
            return ptt_state
            
        except Exception as e:
            logger.error(f"Failed to load PTT state for session {session_id}: {str(e)}")
            raise
    
    async def update_task_status(
        self,
        session_id: str,
        task_id: str,
        status: str,
        execution_data: Dict[str, Any] = None
    ):
        """
        개별 태스크 상태 업데이트
        
        Args:
            session_id: 세션 ID
            task_id: 태스크 ID  
            status: 새로운 상태
            execution_data: 실행 데이터 (결과, 로그 등)
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if execution_data:
                if "started_at" in execution_data:
                    update_data["started_at"] = execution_data["started_at"]
                if "completed_at" in execution_data:
                    update_data["completed_at"] = execution_data["completed_at"]
                if "raw_output" in execution_data:
                    update_data["raw_output"] = execution_data["raw_output"]
                if "error_message" in execution_data:
                    update_data["error_message"] = execution_data["error_message"]
                if "actual_duration_seconds" in execution_data:
                    update_data["actual_duration_seconds"] = execution_data["actual_duration_seconds"]
            
            await self.db.execute(
                update(PentestingTask)
                .where(
                    and_(
                        PentestingTask.session_id == session_id,
                        PentestingTask.id == task_id
                    )
                )
                .values(**update_data)
            )
            
            await self.db.commit()
            
            logger.debug(f"Updated task {task_id} status to {status}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update task status: {str(e)}")
            raise
    
    async def add_new_tasks(
        self,
        session_id: str,
        new_tasks: List[TaskNode]
    ):
        """
        새로운 태스크들을 세션에 추가
        
        Args:
            session_id: 세션 ID
            new_tasks: 추가할 태스크 목록
        """
        try:
            for task in new_tasks:
                db_task = PentestingTask(
                    id=task.id,
                    session_id=session_id,
                    parent_id=task.parent_id,
                    name=task.name,
                    description=task.description,
                    phase=task.phase,
                    status=task.status,
                    tool_required=task.tool_required,
                    estimated_duration_seconds=task.estimated_duration_seconds,
                    priority_score=task.priority_score,
                    risk_level=task.risk_level,
                    requires_approval=task.requires_approval,
                    created_at=task.created_at or datetime.now(timezone.utc)
                )
                self.db.add(db_task)
            
            await self.db.commit()
            
            logger.info(f"Added {len(new_tasks)} new tasks to session {session_id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to add new tasks: {str(e)}")
            raise
    
    async def save_findings(
        self,
        session_id: str,
        findings: List[SecurityFinding],
        task_id: str = None
    ):
        """
        발견사항 저장
        
        Args:
            session_id: 세션 ID
            findings: 저장할 발견사항 목록
            task_id: 관련 태스크 ID (옵션)
        """
        try:
            for finding in findings:
                db_finding = DBSecurityFinding(
                    id=finding.finding_id,
                    session_id=session_id,
                    task_id=task_id,
                    title=finding.title,
                    description=finding.description,
                    category=finding.finding_type,
                    severity=finding.severity,
                    confidence=1.0,  # 기본값
                    affected_component=finding.affected_asset,
                    port_number=finding.affected_port,
                    cve_id=finding.cve_id,
                    cvss_score=finding.cvss_score,
                    cvss_vector=finding.cvss_vector,
                    evidence_data=finding.evidence,
                    impact=finding.technical_details,
                    remediation=finding.remediation,
                    status=finding.status,
                    created_at=finding.discovered_at
                )
                self.db.add(db_finding)
            
            await self.db.commit()
            
            logger.info(f"Saved {len(findings)} findings for session {session_id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to save findings: {str(e)}")
            raise
    
    async def get_session_list(self) -> List[Dict[str, Any]]:
        """저장된 PTT 세션 목록 반환"""
        try:
            result = await self.db.execute(
                select(PentestingSession)
                .order_by(PentestingSession.created_at.desc())
            )
            sessions = result.scalars().all()
            
            session_list = []
            for session in sessions:
                session_list.append({
                    "session_id": session.id,
                    "session_name": session.session_name,
                    "scope_id": session.scope_id,
                    "current_phase": session.current_phase.value if session.current_phase else None,
                    "status": session.status,
                    "primary_target": session.primary_target,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "tasks_completed": session.tasks_completed or 0,
                    "findings_count": session.findings_count or 0,
                    "critical_findings_count": session.critical_findings_count or 0,
                    "created_at": session.created_at.isoformat() if session.created_at else None
                })
            
            return session_list
            
        except Exception as e:
            logger.error(f"Failed to get session list: {str(e)}")
            raise
    
    async def delete_session(self, session_id: str):
        """PTT 세션 삭제 (모든 관련 데이터 포함)"""
        try:
            # 발견사항 삭제
            await self.db.execute(
                delete(DBSecurityFinding)
                .where(DBSecurityFinding.session_id == session_id)
            )
            
            # 태스크 삭제
            await self.db.execute(
                delete(PentestingTask)
                .where(PentestingTask.session_id == session_id)
            )
            
            # 세션 삭제
            await self.db.execute(
                delete(PentestingSession)
                .where(PentestingSession.id == session_id)
            )
            
            await self.db.commit()
            
            logger.info(f"Deleted PTT session {session_id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete session {session_id}: {str(e)}")
            raise
    
    async def _save_session(
        self,
        ptt_state: PTTState,
        session_name: str = None
    ) -> str:
        """세션 정보 저장"""
        session_name = session_name or f"PTT_{ptt_state.tree_id}"
        
        # 기존 세션 확인
        result = await self.db.execute(
            select(PentestingSession)
            .where(PentestingSession.tree_id == ptt_state.tree_id)
        )
        existing_session = result.scalar_one_or_none()
        
        if existing_session:
            # 기존 세션 업데이트
            await self.db.execute(
                update(PentestingSession)
                .where(PentestingSession.id == existing_session.id)
                .values(
                    current_phase=self._get_current_phase(ptt_state),
                    tasks_completed=len(ptt_state.completed_tasks),
                    findings_count=len(ptt_state.findings),
                    critical_findings_count=len([
                        f for f in ptt_state.findings
                        if f.severity.value == 'critical'
                    ]),
                    updated_at=datetime.now(timezone.utc)
                )
            )
            return existing_session.id
        else:
            # 새로운 세션 생성
            new_session = PentestingSession(
                id=ptt_state.tree_id,
                scope_id=ptt_state.engagement_scope.engagement_id,
                session_name=session_name,
                current_phase=self._get_current_phase(ptt_state),
                status="active",
                tree_id=ptt_state.tree_id,
                started_at=datetime.now(timezone.utc),
                tasks_completed=len(ptt_state.completed_tasks),
                findings_count=len(ptt_state.findings),
                critical_findings_count=len([
                    f for f in ptt_state.findings
                    if f.severity.value == 'critical'
                ]),
                created_at=ptt_state.created_at
            )
            self.db.add(new_session)
            await self.db.flush()
            return new_session.id
    
    async def _save_all_tasks(
        self,
        session_id: str,
        all_nodes: Dict[str, TaskNode]
    ):
        """모든 태스크 저장"""
        for task in all_nodes.values():
            # 기존 태스크 확인
            result = await self.db.execute(
                select(PentestingTask)
                .where(
                    and_(
                        PentestingTask.session_id == session_id,
                        PentestingTask.id == task.id
                    )
                )
            )
            existing_task = result.scalar_one_or_none()
            
            if existing_task:
                # 기존 태스크 업데이트
                await self.db.execute(
                    update(PentestingTask)
                    .where(
                        and_(
                            PentestingTask.session_id == session_id,
                            PentestingTask.id == task.id
                        )
                    )
                    .values(
                        status=task.status,
                        priority_score=task.priority_score,
                        started_at=task.started_at,
                        completed_at=task.completed_at,
                        raw_output=task.execution_log
                    )
                )
            else:
                # 새로운 태스크 추가
                new_task = PentestingTask(
                    id=task.id,
                    session_id=session_id,
                    parent_id=task.parent_id,
                    name=task.name,
                    description=task.description,
                    phase=task.phase,
                    status=task.status,
                    tool_required=task.tool_required,
                    estimated_duration_seconds=task.estimated_duration_seconds,
                    priority_score=task.priority_score,
                    risk_level=task.risk_level,
                    requires_approval=task.requires_approval,
                    started_at=task.started_at,
                    completed_at=task.completed_at,
                    raw_output=task.execution_log,
                    created_at=task.created_at or datetime.now(timezone.utc)
                )
                self.db.add(new_task)
    
    async def _save_findings(
        self,
        session_id: str,
        findings: List[SecurityFinding]
    ):
        """발견사항 저장"""
        await self.save_findings(session_id, findings)
    
    async def _save_metadata(
        self,
        session_id: str,
        ptt_state: PTTState
    ):
        """메타데이터 저장 (확장 전략, 발견 자산 등)"""
        metadata = {
            "expansion_strategy": ptt_state.expansion_strategy.value,
            "discovered_assets": list(ptt_state.discovered_assets)
        }
        
        # 추가 메타데이터는 세션의 objectives 필드에 JSON으로 저장
        await self.db.execute(
            update(PentestingSession)
            .where(PentestingSession.id == session_id)
            .values(objectives=metadata)
        )
    
    async def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 정보 로드"""
        result = await self.db.execute(
            select(PentestingSession)
            .where(PentestingSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        return {
            "session_id": session.id,
            "scope_id": session.scope_id,
            "session_name": session.session_name,
            "tree_id": session.tree_id,
            "current_phase": session.current_phase,
            "status": session.status,
            "metadata": session.objectives or {},
            "created_at": session.created_at,
            "started_at": session.started_at
        }
    
    async def _load_all_tasks(self, session_id: str) -> Dict[str, TaskNode]:
        """모든 태스크 로드"""
        result = await self.db.execute(
            select(PentestingTask)
            .where(PentestingTask.session_id == session_id)
            .order_by(PentestingTask.created_at)
        )
        db_tasks = result.scalars().all()
        
        all_nodes = {}
        
        for db_task in db_tasks:
            task_node = TaskNode(
                id=db_task.id,
                name=db_task.name,
                description=db_task.description or "",
                phase=db_task.phase,
                status=db_task.status or "available",
                parent_id=db_task.parent_id,
                children_ids=[],  # 나중에 설정
                tool_required=db_task.tool_required,
                estimated_duration_seconds=db_task.estimated_duration_seconds or 300,
                priority_score=db_task.priority_score or 0.5,
                risk_level=db_task.risk_level or RiskLevel.LOW,
                requires_approval=db_task.requires_approval or False,
                findings=[],  # 나중에 로드
                execution_log=db_task.raw_output,
                created_at=db_task.created_at,
                started_at=db_task.started_at,
                completed_at=db_task.completed_at
            )
            all_nodes[task_node.id] = task_node
        
        # 부모-자식 관계 설정
        for task in all_nodes.values():
            if task.parent_id and task.parent_id in all_nodes:
                parent = all_nodes[task.parent_id]
                if task.id not in parent.children_ids:
                    parent.children_ids.append(task.id)
        
        return all_nodes
    
    async def _load_findings(self, session_id: str) -> List[SecurityFinding]:
        """발견사항 로드"""
        result = await self.db.execute(
            select(DBSecurityFinding)
            .where(DBSecurityFinding.session_id == session_id)
            .order_by(DBSecurityFinding.created_at)
        )
        db_findings = result.scalars().all()
        
        findings = []
        
        for db_finding in db_findings:
            finding = SecurityFinding(
                finding_id=db_finding.id,
                finding_type=db_finding.category or "unknown",
                severity=db_finding.severity,
                title=db_finding.title,
                description=db_finding.description,
                technical_details=db_finding.impact,
                cve_id=db_finding.cve_id,
                cvss_score=db_finding.cvss_score,
                cvss_vector=db_finding.cvss_vector,
                affected_asset=db_finding.affected_component,
                affected_port=db_finding.port_number,
                evidence=db_finding.evidence_data or {},
                remediation=db_finding.remediation,
                status=db_finding.status or "open",
                discovered_at=db_finding.created_at or datetime.now(timezone.utc)
            )
            findings.append(finding)
        
        return findings
    
    async def _reconstruct_ptt_state(
        self,
        session_data: Dict[str, Any],
        all_nodes: Dict[str, TaskNode],
        findings: List[SecurityFinding]
    ) -> PTTState:
        """PTT 상태 재구성"""
        # 루트 노드 찾기
        root_node = None
        for node in all_nodes.values():
            if node.parent_id is None:
                root_node = node
                break
        
        if not root_node:
            raise ValueError("Root node not found in loaded tasks")
        
        # 메타데이터 파싱
        metadata = session_data.get("metadata", {})
        expansion_strategy = TreeExpansionStrategy(
            metadata.get("expansion_strategy", "adaptive")
        )
        discovered_assets = set(metadata.get("discovered_assets", []))
        
        # 기본 engagement_scope 생성 (실제로는 별도 로드 필요)
        engagement_scope = EngagementScope(
            engagement_id=session_data["scope_id"],
            engagement_name=session_data["session_name"],
            engagement_type="external"  # 기본값
        )
        
        ptt_state = PTTState(
            tree_id=session_data["tree_id"],
            engagement_scope=engagement_scope,
            root_node=root_node,
            current_node=None,  # 동적으로 결정
            all_nodes=all_nodes,
            completed_tasks=[
                node.id for node in all_nodes.values()
                if node.status == "completed"
            ],
            failed_tasks=[
                node.id for node in all_nodes.values()
                if node.status == "failed"
            ],
            findings=findings,
            discovered_assets=discovered_assets,
            expansion_strategy=expansion_strategy,
            created_at=session_data["created_at"],
            last_updated=datetime.now(timezone.utc)
        )
        
        return ptt_state
    
    def _get_current_phase(self, ptt_state: PTTState) -> PentestPhase:
        """현재 페이즈 결정"""
        active_phases = set()
        
        for node in ptt_state.all_nodes.values():
            if node.status in ["available", "in_progress"]:
                active_phases.add(node.phase)
        
        # 우선순위 순서로 현재 페이즈 결정
        phase_priority = [
            PentestPhase.EXPLOITATION,
            PentestPhase.VULNERABILITY_ASSESSMENT,
            PentestPhase.ENUMERATION,
            PentestPhase.SCANNING,
            PentestPhase.RECONNAISSANCE,
            PentestPhase.POST_EXPLOITATION,
            PentestPhase.REPORTING
        ]
        
        for phase in phase_priority:
            if phase in active_phases:
                return phase
        
        return PentestPhase.RECONNAISSANCE  # 기본값