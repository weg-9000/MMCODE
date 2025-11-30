"""
MMCODE Security Platform - Task Prioritizer
==========================================

PTT 작업 우선순위 계산 엔진
- 다양한 우선순위 요소 종합
- 적응적 우선순위 조정
- 익스플로잇 가능성 기반 점수

Version: 1.0.0
"""

import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass

from ..models import TaskNode, SecurityFinding, PentestPhase, RiskLevel

logger = logging.getLogger(__name__)


class PriorityFactors(Enum):
    """우선순위 결정 요소"""
    EXPLOIT_POTENTIAL = "exploit_potential"    # 익스플로잇 가능성
    FINDING_SEVERITY = "finding_severity"     # 발견사항 심각도  
    PHASE_PRIORITY = "phase_priority"         # 페이즈별 중요도
    TEMPORAL_URGENCY = "temporal_urgency"     # 시간 기반 긴급성
    DEPENDENCY_WEIGHT = "dependency_weight"   # 종속성 가중치
    RESOURCE_EFFICIENCY = "resource_efficiency"  # 리소스 효율성


@dataclass
class PriorityConfig:
    """우선순위 계산 설정"""
    # 요소별 가중치 (합계 = 1.0)
    exploit_potential_weight: float = 0.3
    finding_severity_weight: float = 0.25
    phase_priority_weight: float = 0.2
    temporal_urgency_weight: float = 0.1
    dependency_weight: float = 0.1
    resource_efficiency_weight: float = 0.05
    
    # 페이즈별 기본 우선순위
    phase_priorities: Dict[PentestPhase, float] = None
    
    # 도구별 효율성 점수
    tool_efficiency: Dict[str, float] = None
    
    def __post_init__(self):
        if self.phase_priorities is None:
            self.phase_priorities = {
                PentestPhase.RECONNAISSANCE: 0.8,
                PentestPhase.SCANNING: 0.9,
                PentestPhase.ENUMERATION: 0.7,
                PentestPhase.VULNERABILITY_ASSESSMENT: 1.0,
                PentestPhase.EXPLOITATION: 0.95,
                PentestPhase.POST_EXPLOITATION: 0.6,
                PentestPhase.REPORTING: 0.3
            }
        
        if self.tool_efficiency is None:
            self.tool_efficiency = {
                "nmap": 0.9,
                "nuclei": 0.95,
                "gobuster": 0.8,
                "sqlmap": 0.85,
                "metasploit": 0.7,  # 리소스 집약적
                "burpsuite": 0.8,
                "nslookup": 0.95,
                "subfinder": 0.9,
                "nc": 0.9
            }


class TaskPrioritizer:
    """
    PTT 작업 우선순위 계산기
    
    특징:
    - 다차원 우선순위 분석
    - 컨텍스트 기반 적응적 조정
    - 익스플로잇 체인 고려
    """
    
    def __init__(self, config: PriorityConfig = None):
        """
        Args:
            config: 우선순위 계산 설정
        """
        self.config = config or PriorityConfig()
        self.recent_findings: List[SecurityFinding] = []
        self.execution_history: List[TaskNode] = []
        self.failed_tasks: Set[str] = set()
        
    async def calculate_priority(
        self,
        task: TaskNode,
        context: Dict[str, Any] = None
    ) -> float:
        """
        작업 우선순위 점수 계산
        
        Args:
            task: 우선순위를 계산할 작업
            context: 계산 컨텍스트 (발견사항, 실행 기록 등)
            
        Returns:
            float: 우선순위 점수 (0.0 - 1.0)
        """
        context = context or {}
        
        # 각 요소별 점수 계산
        scores = {}
        
        scores[PriorityFactors.EXPLOIT_POTENTIAL] = self._calculate_exploit_potential(
            task, context.get('findings', [])
        )
        
        scores[PriorityFactors.FINDING_SEVERITY] = self._calculate_severity_impact(
            task, context.get('findings', [])
        )
        
        scores[PriorityFactors.PHASE_PRIORITY] = self._calculate_phase_priority(task)
        
        scores[PriorityFactors.TEMPORAL_URGENCY] = self._calculate_temporal_urgency(task)
        
        scores[PriorityFactors.DEPENDENCY_WEIGHT] = self._calculate_dependency_weight(
            task, context.get('all_tasks', {})
        )
        
        scores[PriorityFactors.RESOURCE_EFFICIENCY] = self._calculate_resource_efficiency(task)
        
        # 가중 평균 계산
        final_score = (
            scores[PriorityFactors.EXPLOIT_POTENTIAL] * self.config.exploit_potential_weight +
            scores[PriorityFactors.FINDING_SEVERITY] * self.config.finding_severity_weight +
            scores[PriorityFactors.PHASE_PRIORITY] * self.config.phase_priority_weight +
            scores[PriorityFactors.TEMPORAL_URGENCY] * self.config.temporal_urgency_weight +
            scores[PriorityFactors.DEPENDENCY_WEIGHT] * self.config.dependency_weight +
            scores[PriorityFactors.RESOURCE_EFFICIENCY] * self.config.resource_efficiency_weight
        )
        
        # 보너스 및 페널티 적용
        final_score = self._apply_bonuses_penalties(task, final_score, context)
        
        # 0.0 - 1.0 범위로 정규화
        final_score = max(0.0, min(1.0, final_score))
        
        logger.debug(
            f"Priority calculated for {task.name}: {final_score:.3f} "
            f"(exploit: {scores[PriorityFactors.EXPLOIT_POTENTIAL]:.2f}, "
            f"severity: {scores[PriorityFactors.FINDING_SEVERITY]:.2f}, "
            f"phase: {scores[PriorityFactors.PHASE_PRIORITY]:.2f})"
        )
        
        return final_score
    
    def _calculate_exploit_potential(
        self,
        task: TaskNode,
        findings: List[SecurityFinding]
    ) -> float:
        """익스플로잇 가능성 점수 계산"""
        base_score = 0.5
        
        # 작업 종류별 익스플로잇 잠재력
        exploit_potential = {
            "vulnerability_assessment": 0.8,
            "exploitation": 1.0,
            "privilege_escalation": 0.9,
            "lateral_movement": 0.7,
            "data_exfiltration": 0.6
        }
        
        # 도구별 익스플로잇 가능성
        tool_potential = {
            "metasploit": 1.0,
            "sqlmap": 0.9,
            "nuclei": 0.8,
            "burpsuite": 0.7,
            "gobuster": 0.3,
            "nmap": 0.2
        }
        
        # 작업 유형 기반 점수
        for key, score in exploit_potential.items():
            if key in task.name.lower() or key in task.description.lower():
                base_score = max(base_score, score)
                break
        
        # 도구 기반 점수 조정
        if task.tool_required:
            tool_score = tool_potential.get(task.tool_required.lower(), 0.5)
            base_score = (base_score + tool_score) / 2
        
        # 관련 발견사항 기반 부스트
        related_findings = [
            f for f in findings
            if (task.name.lower() in f.title.lower() or
                (f.affected_asset and f.affected_asset in task.description))
        ]
        
        if related_findings:
            high_severity_count = len([
                f for f in related_findings
                if f.severity.value in ['high', 'critical']
            ])
            if high_severity_count > 0:
                base_score += 0.2 * min(high_severity_count, 3) / 3
        
        # 위험 수준 반영
        risk_multiplier = {
            RiskLevel.LOW: 0.8,
            RiskLevel.MEDIUM: 1.0,
            RiskLevel.HIGH: 1.2,
            RiskLevel.CRITICAL: 1.4
        }
        
        multiplier = risk_multiplier.get(task.risk_level, 1.0)
        base_score *= multiplier
        
        return min(base_score, 1.0)
    
    def _calculate_severity_impact(
        self,
        task: TaskNode,
        findings: List[SecurityFinding]
    ) -> float:
        """발견사항 심각도 영향 점수"""
        if not findings:
            return 0.5
        
        # 최근 2시간 내 발견사항
        recent_findings = [
            f for f in findings
            if f.discovered_at > datetime.utcnow() - timedelta(hours=2)
        ]
        
        if not recent_findings:
            return 0.3
        
        # 심각도별 점수
        severity_scores = {
            'info': 0.1,
            'low': 0.3,
            'medium': 0.6,
            'high': 0.9,
            'critical': 1.0
        }
        
        # 최고 심각도 기반 점수
        max_severity = max(
            [severity_scores.get(f.severity.value, 0.0) for f in recent_findings],
            default=0.0
        )
        
        # 발견사항 수 기반 보너스
        finding_count_bonus = min(len(recent_findings) * 0.1, 0.3)
        
        return min(max_severity + finding_count_bonus, 1.0)
    
    def _calculate_phase_priority(self, task: TaskNode) -> float:
        """페이즈 우선순위 점수"""
        return self.config.phase_priorities.get(task.phase, 0.5)
    
    def _calculate_temporal_urgency(self, task: TaskNode) -> float:
        """시간 기반 긴급성 점수"""
        now = datetime.utcnow()
        
        # 작업 생성 후 경과 시간
        if task.created_at:
            age_hours = (now - task.created_at).total_seconds() / 3600
            
            # 3시간 후부터 긴급성 증가
            if age_hours > 3:
                urgency = min(0.2 + (age_hours - 3) * 0.1, 1.0)
            else:
                urgency = 0.2
        else:
            urgency = 0.5
        
        # 승인 필요한 작업은 긴급성 증가
        if task.requires_approval:
            urgency += 0.3
        
        # 실패한 작업은 긴급성 감소
        if task.id in self.failed_tasks:
            urgency *= 0.5
        
        return min(urgency, 1.0)
    
    def _calculate_dependency_weight(
        self,
        task: TaskNode,
        all_tasks: Dict[str, TaskNode]
    ) -> float:
        """종속성 가중치 계산"""
        base_weight = 0.5
        
        # 자식 작업 수 (이 작업이 완료되면 실행 가능한 작업들)
        child_count = len(task.children_ids)
        if child_count > 0:
            base_weight += min(child_count * 0.15, 0.4)
        
        # 부모 작업 완료 여부
        if task.parent_id and task.parent_id in all_tasks:
            parent = all_tasks[task.parent_id]
            if parent.status == "completed":
                base_weight += 0.2
            elif parent.status == "in_progress":
                base_weight += 0.1
        
        # 전제조건 만족 여부
        if hasattr(task, 'prerequisites'):
            satisfied_count = sum(
                1 for prereq in task.prerequisites
                if self._is_prerequisite_satisfied(prereq, all_tasks)
            )
            if task.prerequisites:
                satisfaction_ratio = satisfied_count / len(task.prerequisites)
                base_weight = base_weight * satisfaction_ratio + 0.2
        
        return min(base_weight, 1.0)
    
    def _calculate_resource_efficiency(self, task: TaskNode) -> float:
        """리소스 효율성 점수"""
        efficiency = 0.5
        
        # 도구별 효율성
        if task.tool_required:
            tool_efficiency = self.config.tool_efficiency.get(
                task.tool_required.lower(), 0.5
            )
            efficiency = tool_efficiency
        
        # 예상 실행 시간 기반 조정
        if task.estimated_duration_seconds:
            # 5분 이하: 높은 효율성, 30분 이상: 낮은 효율성
            if task.estimated_duration_seconds <= 300:  # 5분
                efficiency += 0.2
            elif task.estimated_duration_seconds >= 1800:  # 30분
                efficiency -= 0.2
        
        return max(0.1, min(efficiency, 1.0))
    
    def _apply_bonuses_penalties(
        self,
        task: TaskNode,
        base_score: float,
        context: Dict[str, Any]
    ) -> float:
        """보너스 및 페널티 적용"""
        adjusted_score = base_score
        
        # 페널티
        
        # 반복 실패 페널티
        if task.id in self.failed_tasks:
            adjusted_score *= 0.6
            logger.debug(f"Applied failure penalty to {task.name}")
        
        # 긴급 승인 페널티 (승인 대기가 오래 걸릴 수 있음)
        if task.requires_approval and task.risk_level == RiskLevel.CRITICAL:
            adjusted_score *= 0.8
        
        # 보너스
        
        # 연쇄 익스플로잇 보너스
        if self._is_exploit_chain_task(task, context):
            adjusted_score *= 1.3
            logger.debug(f"Applied exploit chain bonus to {task.name}")
        
        # 최근 성공한 유사 작업 보너스
        if self._has_recent_similar_success(task):
            adjusted_score *= 1.1
        
        # 다중 타겟 보너스
        if self._affects_multiple_targets(task, context):
            adjusted_score *= 1.2
        
        return adjusted_score
    
    def _is_prerequisite_satisfied(
        self,
        prerequisite: str,
        all_tasks: Dict[str, TaskNode]
    ) -> bool:
        """전제조건 만족 여부 확인"""
        # TODO: 더 정교한 전제조건 검사 로직
        if "port scan" in prerequisite.lower():
            return any(
                "port" in task.name.lower() and task.status == "completed"
                for task in all_tasks.values()
            )
        return True
    
    def _is_exploit_chain_task(
        self,
        task: TaskNode,
        context: Dict[str, Any]
    ) -> bool:
        """익스플로잇 체인의 일부인지 확인"""
        if task.phase not in [PentestPhase.EXPLOITATION, PentestPhase.POST_EXPLOITATION]:
            return False
        
        # 최근 익스플로잇 성공이 있었는지 확인
        recent_exploits = [
            t for t in self.execution_history
            if (t.phase == PentestPhase.EXPLOITATION and
                t.status == "completed" and
                t.completed_at and
                t.completed_at > datetime.utcnow() - timedelta(hours=1))
        ]
        
        return len(recent_exploits) > 0
    
    def _has_recent_similar_success(self, task: TaskNode) -> bool:
        """최근 유사한 성공 작업이 있는지 확인"""
        if not self.execution_history:
            return False
        
        similar_tasks = [
            t for t in self.execution_history
            if (t.tool_required == task.tool_required and
                t.status == "completed" and
                t.completed_at and
                t.completed_at > datetime.utcnow() - timedelta(hours=6))
        ]
        
        return len(similar_tasks) > 0
    
    def _affects_multiple_targets(
        self,
        task: TaskNode,
        context: Dict[str, Any]
    ) -> bool:
        """다중 타겟에 영향을 주는 작업인지 확인"""
        # 네트워크 스캔, 도메인 열거 등
        multi_target_keywords = [
            "network scan", "subnet scan", "domain enum",
            "subdomain", "dns enum", "range scan"
        ]
        
        task_text = f"{task.name} {task.description}".lower()
        
        return any(keyword in task_text for keyword in multi_target_keywords)
    
    def update_context(
        self,
        new_findings: List[SecurityFinding] = None,
        completed_task: TaskNode = None,
        failed_task_id: str = None
    ):
        """컨텍스트 업데이트"""
        if new_findings:
            self.recent_findings.extend(new_findings)
            # 오래된 발견사항 제거 (24시간 이상)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self.recent_findings = [
                f for f in self.recent_findings
                if f.discovered_at > cutoff
            ]
        
        if completed_task:
            self.execution_history.append(completed_task)
            # 최근 50개만 유지
            if len(self.execution_history) > 50:
                self.execution_history = self.execution_history[-50:]
        
        if failed_task_id:
            self.failed_tasks.add(failed_task_id)
    
    def get_priority_explanation(
        self,
        task: TaskNode,
        score: float,
        context: Dict[str, Any] = None
    ) -> str:
        """우선순위 점수 설명 생성"""
        explanations = []
        
        if score > 0.8:
            explanations.append("High priority task")
        elif score > 0.6:
            explanations.append("Medium-high priority")
        elif score > 0.4:
            explanations.append("Medium priority")
        else:
            explanations.append("Lower priority")
        
        if task.phase == PentestPhase.VULNERABILITY_ASSESSMENT:
            explanations.append("vulnerability assessment phase")
        elif task.phase == PentestPhase.EXPLOITATION:
            explanations.append("active exploitation phase")
        
        if task.requires_approval:
            explanations.append("requires human approval")
        
        if task.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            explanations.append(f"{task.risk_level.value} risk level")
        
        return "; ".join(explanations)
    
    def get_stats(self) -> Dict[str, Any]:
        """우선순위 계산기 통계"""
        return {
            "recent_findings_count": len(self.recent_findings),
            "execution_history_count": len(self.execution_history),
            "failed_tasks_count": len(self.failed_tasks),
            "config": {
                "exploit_potential_weight": self.config.exploit_potential_weight,
                "finding_severity_weight": self.config.finding_severity_weight,
                "phase_priority_weight": self.config.phase_priority_weight
            }
        }