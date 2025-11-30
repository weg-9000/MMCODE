"""
MMCODE Security Platform - Pentesting Task Tree Core
===================================================

PentestGPT 스타일 작업 트리 핵심 구현
- 동적 작업 확장 및 우선순위 계산
- LLM 컨텍스트 손실 문제 해결
- 스코프 검증 통합

Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4

from ..models import (
    TaskNode,
    SecurityFinding,
    PentestPhase,
    RiskLevel,
    EngagementScope,
    SecurityAction,
    generate_task_id
)
from ..scope_enforcer import ScopeEnforcementEngine

logger = logging.getLogger(__name__)


class TreeExpansionStrategy(Enum):
    """트리 확장 전략"""
    DEPTH_FIRST = "depth_first"      # 한 경로를 깊이 탐색
    BREADTH_FIRST = "breadth_first"  # 모든 서비스를 병렬 탐색
    RISK_BASED = "risk_based"        # 위험도 기반 우선순위
    ADAPTIVE = "adaptive"            # 발견사항에 따른 동적 조정


class TaskStatus(Enum):
    """작업 상태"""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class TaskRecommendation:
    """다음 실행할 작업 추천"""
    task: TaskNode
    reasoning: str
    priority_score: float
    estimated_duration: int  # seconds
    tools_required: List[str]
    prerequisites: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    expected_outcomes: List[str] = field(default_factory=list)
    requires_approval: bool = False


@dataclass 
class TaskResult:
    """작업 실행 결과"""
    task_id: str
    status: str  # "success", "failed", "partial"
    findings: List[SecurityFinding] = field(default_factory=list)
    new_targets: List[str] = field(default_factory=list)
    new_services: List[Dict[str, Any]] = field(default_factory=list)
    raw_output: Optional[str] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    next_recommendations: List[str] = field(default_factory=list)


@dataclass
class PTTState:
    """PTT 전체 상태"""
    tree_id: str
    engagement_scope: EngagementScope
    root_node: TaskNode
    current_node: Optional[TaskNode]
    all_nodes: Dict[str, TaskNode] = field(default_factory=dict)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    findings: List[SecurityFinding] = field(default_factory=list)
    discovered_assets: Set[str] = field(default_factory=set)
    expansion_strategy: TreeExpansionStrategy = TreeExpansionStrategy.ADAPTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)


class PentestingTaskTree:
    """
    PentestGPT 스타일 Pentesting Task Tree 관리
    
    특징:
    - 발견사항 기반 동적 트리 확장
    - 우선순위 기반 작업 선택
    - LLM 컨텍스트 요약 생성
    - 스코프 검증 통합
    """
    
    def __init__(
        self,
        target: str,
        engagement_scope: EngagementScope,
        scope_enforcer: ScopeEnforcementEngine,
        expansion_strategy: TreeExpansionStrategy = TreeExpansionStrategy.ADAPTIVE
    ):
        """
        Args:
            target: 주 타겟 (IP, 도메인, 범위)
            engagement_scope: 펜테스팅 범위 정의
            scope_enforcer: 스코프 검증 엔진
            expansion_strategy: 트리 확장 전략
        """
        self.tree_id = f"ptt_{uuid4().hex[:12]}"
        self.target = target
        self.scope = engagement_scope
        self.scope_enforcer = scope_enforcer
        self.expansion_strategy = expansion_strategy
        
        # 루트 노드 생성
        self.root = TaskNode(
            id=generate_task_id(),
            name=f"Pentest: {target}",
            description=f"Comprehensive penetration test of {target}",
            phase=PentestPhase.RECONNAISSANCE,
            status=TaskStatus.IN_PROGRESS.value,
            priority_score=1.0
        )
        
        # 상태 관리
        self.current_node: Optional[TaskNode] = None
        self.nodes: Dict[str, TaskNode] = {self.root.id: self.root}
        self.execution_history: List[TaskNode] = []
        self.findings: List[SecurityFinding] = []
        self.discovered_assets: Set[str] = {target}
        
        # 성능 추적
        self.task_count = 1
        self.completion_rate = 0.0
        self.avg_task_duration = 0.0
        
        # 초기 작업 생성
        self._initialize_reconnaissance_tasks()
        
    def _initialize_reconnaissance_tasks(self):
        """정찰 페이즈 초기 작업 생성"""
        recon_tasks = [
            {
                "name": "DNS Enumeration",
                "description": f"DNS enumeration of {self.target}",
                "tool_required": "nslookup",
                "estimated_duration_seconds": 120,
                "priority_score": 0.9
            },
            {
                "name": "Port Scanning",
                "description": f"Port scan of {self.target}",
                "tool_required": "nmap",
                "estimated_duration_seconds": 300,
                "priority_score": 0.8
            },
            {
                "name": "Web Service Discovery",
                "description": f"Identify web services on {self.target}",
                "tool_required": "http_probe",
                "estimated_duration_seconds": 180,
                "priority_score": 0.7
            }
        ]
        
        for task_data in recon_tasks:
            child = TaskNode(
                id=generate_task_id(),
                name=task_data["name"],
                description=task_data["description"],
                phase=PentestPhase.RECONNAISSANCE,
                status=TaskStatus.AVAILABLE.value,
                parent_id=self.root.id,
                tool_required=task_data["tool_required"],
                estimated_duration_seconds=task_data["estimated_duration_seconds"],
                priority_score=task_data["priority_score"]
            )
            
            self.nodes[child.id] = child
            self.root.children_ids.append(child.id)
            self.task_count += 1
    
    async def select_next_task(self) -> Optional[TaskRecommendation]:
        """
        다음 실행할 작업 선택
        
        Returns:
            TaskRecommendation: 추천 작업 정보
        """
        available_tasks = self._get_available_tasks()
        
        if not available_tasks:
            logger.info(f"No available tasks in tree {self.tree_id}")
            return None
        
        # 우선순위 기반 정렬
        scored_tasks = []
        for task in available_tasks:
            score = await self._calculate_priority_score(task)
            scored_tasks.append((task, score))
        
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        best_task = scored_tasks[0][0]
        
        # 스코프 검증
        if not await self._validate_task_scope(best_task):
            logger.warning(f"Task {best_task.id} failed scope validation")
            # 다음 작업 시도
            if len(scored_tasks) > 1:
                best_task = scored_tasks[1][0]
            else:
                return None
        
        recommendation = TaskRecommendation(
            task=best_task,
            reasoning=self._generate_reasoning(best_task, scored_tasks),
            priority_score=scored_tasks[0][1],
            estimated_duration=best_task.estimated_duration_seconds,
            tools_required=[best_task.tool_required] if best_task.tool_required else [],
            prerequisites=self._identify_prerequisites(best_task),
            risks=self._assess_risks(best_task),
            expected_outcomes=self._predict_outcomes(best_task),
            requires_approval=best_task.requires_approval
        )
        
        return recommendation
    
    async def update_task_result(
        self, 
        task_id: str, 
        result: TaskResult
    ) -> List[TaskNode]:
        """
        작업 결과 업데이트 및 트리 확장
        
        Args:
            task_id: 완료된 작업 ID
            result: 작업 실행 결과
            
        Returns:
            List[TaskNode]: 새로 생성된 작업들
        """
        task = self.nodes.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in tree")
        
        # 작업 상태 업데이트
        if result.status == "success":
            task.status = TaskStatus.COMPLETED.value
            self.execution_history.append(task)
            task.completed_at = datetime.utcnow()
        elif result.status == "failed":
            task.status = TaskStatus.FAILED.value
            task.execution_log = result.error_message
        
        # 발견사항 추가
        task.findings.extend(result.findings)
        self.findings.extend(result.findings)
        
        # 새로운 자산 추가
        for target in result.new_targets:
            if self.scope.is_ip_in_scope(target) or self.scope.is_domain_in_scope(target):
                self.discovered_assets.add(target)
        
        # 트리 확장 (새로운 작업 생성)
        new_tasks = await self._expand_tree(task, result)
        
        # 완료율 업데이트
        self._update_completion_stats()
        
        logger.info(
            f"Updated task {task_id}: {result.status}, "
            f"created {len(new_tasks)} new tasks"
        )
        
        return new_tasks
    
    async def _expand_tree(
        self, 
        completed_task: TaskNode, 
        result: TaskResult
    ) -> List[TaskNode]:
        """
        완료된 작업 결과 기반 트리 확장
        
        Args:
            completed_task: 완료된 작업
            result: 실행 결과
            
        Returns:
            List[TaskNode]: 새로 생성된 하위 작업들
        """
        new_tasks = []
        
        # 페이즈별 확장 로직
        if completed_task.phase == PentestPhase.RECONNAISSANCE:
            new_tasks.extend(
                self._expand_from_reconnaissance(completed_task, result)
            )
        elif completed_task.phase == PentestPhase.SCANNING:
            new_tasks.extend(
                self._expand_from_scanning(completed_task, result)
            )
        elif completed_task.phase == PentestPhase.ENUMERATION:
            new_tasks.extend(
                self._expand_from_enumeration(completed_task, result)
            )
        elif completed_task.phase == PentestPhase.VULNERABILITY_ASSESSMENT:
            new_tasks.extend(
                self._expand_from_vulnerability_assessment(completed_task, result)
            )
        
        # 노드 추가
        for task in new_tasks:
            self.nodes[task.id] = task
            completed_task.children_ids.append(task.id)
            self.task_count += 1
        
        return new_tasks
    
    def _expand_from_reconnaissance(
        self, 
        task: TaskNode, 
        result: TaskResult
    ) -> List[TaskNode]:
        """정찰 단계 완료 후 스캐닝 작업 생성"""
        new_tasks = []
        
        if task.tool_required == "nslookup" and result.new_targets:
            # DNS 열거 성공 시 추가 도메인 탐색
            for domain in result.new_targets[:3]:  # 최대 3개
                if self.scope.is_domain_in_scope(domain):
                    new_tasks.append(TaskNode(
                        id=generate_task_id(),
                        name=f"Subdomain Enumeration: {domain}",
                        description=f"Enumerate subdomains of {domain}",
                        phase=PentestPhase.RECONNAISSANCE,
                        status=TaskStatus.AVAILABLE.value,
                        parent_id=task.id,
                        tool_required="subfinder",
                        estimated_duration_seconds=300,
                        priority_score=0.6
                    ))
        
        elif task.tool_required == "nmap":
            # 포트 스캔 완료 시 서비스 열거 생성
            if result.new_services:
                for service in result.new_services:
                    port = service.get('port')
                    service_name = service.get('service', 'unknown')
                    
                    if service_name in ['http', 'https']:
                        new_tasks.append(TaskNode(
                            id=generate_task_id(),
                            name=f"Web Service Enumeration: {port}",
                            description=f"Enumerate web service on port {port}",
                            phase=PentestPhase.ENUMERATION,
                            status=TaskStatus.AVAILABLE.value,
                            parent_id=task.id,
                            tool_required="gobuster",
                            estimated_duration_seconds=600,
                            priority_score=0.8,
                            risk_level=RiskLevel.MEDIUM
                        ))
                    
                    elif service_name in ['ssh', 'ftp', 'telnet']:
                        new_tasks.append(TaskNode(
                            id=generate_task_id(),
                            name=f"Service Banner Grab: {service_name}:{port}",
                            description=f"Banner grabbing for {service_name} on port {port}",
                            phase=PentestPhase.ENUMERATION,
                            status=TaskStatus.AVAILABLE.value,
                            parent_id=task.id,
                            tool_required="nc",
                            estimated_duration_seconds=120,
                            priority_score=0.5
                        ))
        
        return new_tasks
    
    def _expand_from_scanning(
        self, 
        task: TaskNode, 
        result: TaskResult
    ) -> List[TaskNode]:
        """스캐닝 단계 완료 후 취약점 평가 작업 생성"""
        new_tasks = []
        
        # 발견된 서비스별 취약점 스캔 생성
        for service in result.new_services:
            service_name = service.get('service')
            port = service.get('port')
            
            if service_name in ['http', 'https']:
                new_tasks.append(TaskNode(
                    id=generate_task_id(),
                    name=f"Web Vulnerability Scan: {port}",
                    description=f"Web vulnerability assessment on port {port}",
                    phase=PentestPhase.VULNERABILITY_ASSESSMENT,
                    status=TaskStatus.AVAILABLE.value,
                    parent_id=task.id,
                    tool_required="nuclei",
                    estimated_duration_seconds=900,
                    priority_score=0.9,
                    risk_level=RiskLevel.MEDIUM
                ))
        
        return new_tasks
    
    def _expand_from_enumeration(
        self, 
        task: TaskNode, 
        result: TaskResult
    ) -> List[TaskNode]:
        """열거 단계 완료 후 세부 분석 작업 생성"""
        new_tasks = []
        
        # 발견된 취약점에 대한 상세 분석
        for finding in result.findings:
            if finding.severity.value in ['high', 'critical']:
                new_tasks.append(TaskNode(
                    id=generate_task_id(),
                    name=f"Exploit Analysis: {finding.title[:50]}",
                    description=f"Analyze exploitability of {finding.title}",
                    phase=PentestPhase.VULNERABILITY_ASSESSMENT,
                    status=TaskStatus.AVAILABLE.value,
                    parent_id=task.id,
                    tool_required="metasploit",
                    estimated_duration_seconds=1200,
                    priority_score=0.95,
                    risk_level=RiskLevel.HIGH,
                    requires_approval=True
                ))
        
        return new_tasks
    
    def _expand_from_vulnerability_assessment(
        self, 
        task: TaskNode, 
        result: TaskResult
    ) -> List[TaskNode]:
        """취약점 평가 완료 후 익스플로잇 작업 생성"""
        new_tasks = []
        
        # 익스플로잇 가능한 취약점에 대한 실제 익스플로잇 작업
        for finding in result.findings:
            if (finding.severity.value == 'critical' and 
                hasattr(finding, 'exploit_available') and 
                finding.exploit_available):
                
                new_tasks.append(TaskNode(
                    id=generate_task_id(),
                    name=f"Exploit Execution: {finding.title[:50]}",
                    description=f"Execute exploit for {finding.title}",
                    phase=PentestPhase.EXPLOITATION,
                    status=TaskStatus.NEEDS_APPROVAL.value,
                    parent_id=task.id,
                    tool_required="metasploit",
                    estimated_duration_seconds=1800,
                    priority_score=1.0,
                    risk_level=RiskLevel.CRITICAL,
                    requires_approval=True
                ))
        
        return new_tasks
    
    async def _calculate_priority_score(self, task: TaskNode) -> float:
        """
        작업 우선순위 점수 계산
        
        고려 요소:
        - 기본 우선순위 점수
        - 페이즈별 가중치
        - 발견사항 기반 가중치
        - 시간 경과에 따른 감점
        """
        base_score = task.priority_score
        
        # 페이즈별 가중치
        phase_weights = {
            PentestPhase.RECONNAISSANCE: 1.0,
            PentestPhase.SCANNING: 0.9,
            PentestPhase.ENUMERATION: 0.8,
            PentestPhase.VULNERABILITY_ASSESSMENT: 1.2,
            PentestPhase.EXPLOITATION: 1.5,
            PentestPhase.POST_EXPLOITATION: 0.7
        }
        
        phase_weight = phase_weights.get(task.phase, 1.0)
        
        # 발견사항 기반 가중치
        findings_boost = 0.0
        if self.findings:
            recent_findings = [
                f for f in self.findings 
                if f.discovered_at > datetime.utcnow() - timedelta(minutes=30)
            ]
            if recent_findings:
                findings_boost = 0.2 * len(recent_findings)
        
        # 위험도 가중치
        risk_weights = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MEDIUM: 1.1,
            RiskLevel.HIGH: 1.3,
            RiskLevel.CRITICAL: 1.5
        }
        risk_weight = risk_weights.get(task.risk_level, 1.0)
        
        final_score = base_score * phase_weight * risk_weight + findings_boost
        
        return min(final_score, 2.0)  # 최대 2.0으로 제한
    
    async def _validate_task_scope(self, task: TaskNode) -> bool:
        """작업이 스코프 내인지 검증"""
        # 기본적인 스코프 검사
        if task.tool_required and task.tool_required in self.scope.prohibited_methods:
            return False
        
        # TODO: 더 상세한 스코프 검증 로직
        return True
    
    def _generate_reasoning(
        self, 
        selected_task: TaskNode, 
        scored_tasks: List[Tuple[TaskNode, float]]
    ) -> str:
        """작업 선택 이유 생성"""
        score = scored_tasks[0][1] if scored_tasks else 0.0
        
        reasoning = [
            f"Selected '{selected_task.name}' (score: {score:.2f})"
        ]
        
        if selected_task.phase == PentestPhase.VULNERABILITY_ASSESSMENT:
            reasoning.append("High priority: vulnerability assessment phase")
        
        if selected_task.risk_level == RiskLevel.HIGH:
            reasoning.append("High-risk task with potential for significant findings")
        
        if len(self.execution_history) > 0:
            last_task = self.execution_history[-1]
            reasoning.append(f"Follows logically from {last_task.name}")
        
        return "; ".join(reasoning)
    
    def _identify_prerequisites(self, task: TaskNode) -> List[str]:
        """작업 전제조건 식별"""
        prerequisites = []
        
        if task.tool_required == "gobuster":
            prerequisites.append("Target web service must be accessible")
        elif task.tool_required == "nuclei":
            prerequisites.append("Port scan results required")
        elif task.tool_required == "metasploit":
            prerequisites.append("Vulnerability confirmed")
            
        return prerequisites
    
    def _assess_risks(self, task: TaskNode) -> List[str]:
        """작업 위험 요소 평가"""
        risks = []
        
        if task.phase == PentestPhase.EXPLOITATION:
            risks.append("Service disruption possible")
            risks.append("Target system impact")
        
        if task.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            risks.append("High-impact security testing")
        
        if task.requires_approval:
            risks.append("Requires human approval")
            
        return risks
    
    def _predict_outcomes(self, task: TaskNode) -> List[str]:
        """예상 결과 예측"""
        outcomes = []
        
        if task.tool_required == "nmap":
            outcomes.extend([
                "Open ports identification",
                "Service version detection",
                "Potential attack surface mapping"
            ])
        elif task.tool_required == "gobuster":
            outcomes.extend([
                "Hidden directories discovery",
                "Sensitive file exposure",
                "Web application structure mapping"
            ])
        elif task.tool_required == "nuclei":
            outcomes.extend([
                "Vulnerability detection",
                "Security misconfigurations",
                "Known CVE identification"
            ])
            
        return outcomes
    
    def _get_available_tasks(self) -> List[TaskNode]:
        """실행 가능한 작업 목록 반환"""
        return [
            task for task in self.nodes.values()
            if task.status == TaskStatus.AVAILABLE.value
        ]
    
    def _update_completion_stats(self):
        """완료율 및 통계 업데이트"""
        completed = len([
            t for t in self.nodes.values() 
            if t.status == TaskStatus.COMPLETED.value
        ])
        self.completion_rate = completed / self.task_count if self.task_count > 0 else 0.0
        
        # 평균 작업 시간 계산
        completed_durations = []
        for task in self.execution_history:
            if task.completed_at and task.started_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                completed_durations.append(duration)
        
        if completed_durations:
            self.avg_task_duration = sum(completed_durations) / len(completed_durations)
    
    def get_context_summary(self, max_length: int = 2000) -> str:
        """
        LLM에 전달할 컨텍스트 요약 생성
        
        Args:
            max_length: 최대 문자 길이
            
        Returns:
            str: 컨텍스트 요약
        """
        summary_parts = []
        
        # 기본 정보
        summary_parts.append(f"=== PTT Context: {self.target} ===")
        summary_parts.append(f"Tree ID: {self.tree_id}")
        summary_parts.append(f"Tasks: {self.task_count} total, {self.completion_rate:.1%} complete")
        
        # 현재 페이즈
        current_phases = set(
            task.phase for task in self.nodes.values()
            if task.status == TaskStatus.AVAILABLE.value
        )
        if current_phases:
            summary_parts.append(f"Active phases: {', '.join(p.value for p in current_phases)}")
        
        # 최근 발견사항
        recent_findings = [
            f for f in self.findings
            if f.discovered_at > datetime.utcnow() - timedelta(hours=2)
        ]
        if recent_findings:
            high_severity = [f for f in recent_findings if f.severity.value in ['high', 'critical']]
            summary_parts.append(f"Recent findings: {len(recent_findings)} total")
            if high_severity:
                summary_parts.append(f"High-severity findings: {len(high_severity)}")
        
        # 실행 기록 (최근 3개)
        if self.execution_history:
            summary_parts.append("Recent completions:")
            for task in self.execution_history[-3:]:
                status_emoji = "✅" if task.status == TaskStatus.COMPLETED.value else "❌"
                summary_parts.append(f"  {status_emoji} {task.name}")
        
        # 다음 작업 (상위 3개)
        available = self._get_available_tasks()
        if available:
            summary_parts.append("Available tasks:")
            for task in sorted(available, key=lambda t: t.priority_score, reverse=True)[:3]:
                summary_parts.append(f"  📋 {task.name} (priority: {task.priority_score:.1f})")
        
        # 발견된 자산
        if self.discovered_assets:
            assets_list = list(self.discovered_assets)[:5]  # 최대 5개
            summary_parts.append(f"Discovered assets: {', '.join(assets_list)}")
            if len(self.discovered_assets) > 5:
                summary_parts.append(f"... and {len(self.discovered_assets) - 5} more")
        
        summary = "\n".join(summary_parts)
        
        # 길이 제한
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def get_state(self) -> PTTState:
        """현재 PTT 상태 반환"""
        return PTTState(
            tree_id=self.tree_id,
            engagement_scope=self.scope,
            root_node=self.root,
            current_node=self.current_node,
            all_nodes=self.nodes.copy(),
            completed_tasks=[
                t.id for t in self.nodes.values()
                if t.status == TaskStatus.COMPLETED.value
            ],
            failed_tasks=[
                t.id for t in self.nodes.values()
                if t.status == TaskStatus.FAILED.value
            ],
            findings=self.findings.copy(),
            discovered_assets=self.discovered_assets.copy(),
            expansion_strategy=self.expansion_strategy,
            last_updated=datetime.utcnow()
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """PTT 통계 정보 반환"""
        phase_distribution = {}
        status_distribution = {}
        
        for task in self.nodes.values():
            # 페이즈별 분포
            phase = task.phase.value
            phase_distribution[phase] = phase_distribution.get(phase, 0) + 1
            
            # 상태별 분포
            status = task.status
            status_distribution[status] = status_distribution.get(status, 0) + 1
        
        return {
            "tree_id": self.tree_id,
            "target": self.target,
            "task_count": self.task_count,
            "completion_rate": self.completion_rate,
            "findings_count": len(self.findings),
            "critical_findings": len([
                f for f in self.findings if f.severity.value == 'critical'
            ]),
            "discovered_assets": len(self.discovered_assets),
            "avg_task_duration_seconds": self.avg_task_duration,
            "phase_distribution": phase_distribution,
            "status_distribution": status_distribution,
            "expansion_strategy": self.expansion_strategy.value
        }