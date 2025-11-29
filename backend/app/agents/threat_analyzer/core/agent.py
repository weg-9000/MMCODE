"""
ThreatAnalyzer Agent - Core Implementation
=========================================

PentestGPT 스타일 중앙 오케스트레이터
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from ....security import (
    EngagementScope,
    SecurityAction,
    ValidationResult,
    SecurityFinding,
    TaskNode,
    SecurityContext,
    HumanApproval,
    PentestPhase,
    RiskLevel,
    SeverityLevel,
    ScopeEnforcementEngine,
    SecurityAuditLogger,
    AuditEventType,
    generate_action_id,
    generate_task_id,
)

from ..models.threat_models import (
    TaskRecommendation,
    TaskResult,
    PentestingTaskTree,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class ThreatAnalyzer:
    """
    PentestGPT 스타일 중앙 오케스트레이터
    
    책임:
    - PTT (Pentesting Task Tree) 관리
    - 다음 작업 추천 (인간에게)
    - 작업 실행 조정
    - 발견사항 기반 동적 확장
    - MITRE ATT&CK 매핑
    """
    
    # 작업 우선순위 가중치
    PRIORITY_WEIGHTS = {
        "exploitability": 0.25,
        "information_gain": 0.20,
        "prerequisite_satisfaction": 0.20,
        "scope_compliance": 0.15,
        "resource_efficiency": 0.10,
        "phase_priority": 0.10,
    }
    
    # 페이즈별 기본 태스크 템플릿
    PHASE_TEMPLATES = {
        PentestPhase.RECONNAISSANCE: [
            {
                "name": "Passive DNS Enumeration",
                "description": "Collect DNS records without active probing",
                "tool": "amass",
                "risk": RiskLevel.LOW,
            },
            {
                "name": "WHOIS Information Gathering",
                "description": "Gather domain registration information",
                "tool": "whois",
                "risk": RiskLevel.LOW,
            },
            {
                "name": "Certificate Transparency Search",
                "description": "Search CT logs for subdomains",
                "tool": "crt.sh",
                "risk": RiskLevel.LOW,
            },
        ],
        PentestPhase.SCANNING: [
            {
                "name": "Port Discovery",
                "description": "Identify open ports on target hosts",
                "tool": "nmap",
                "risk": RiskLevel.LOW,
            },
            {
                "name": "Service Detection",
                "description": "Identify services running on open ports",
                "tool": "nmap",
                "risk": RiskLevel.LOW,
            },
            {
                "name": "OS Detection",
                "description": "Fingerprint target operating systems",
                "tool": "nmap",
                "risk": RiskLevel.LOW,
            },
        ],
        PentestPhase.ENUMERATION: [
            {
                "name": "Web Directory Enumeration",
                "description": "Discover hidden directories and files",
                "tool": "gobuster",
                "risk": RiskLevel.LOW,
            },
            {
                "name": "Service Banner Grabbing",
                "description": "Collect service version information",
                "tool": "nmap",
                "risk": RiskLevel.LOW,
            },
        ],
        PentestPhase.VULNERABILITY_ASSESSMENT: [
            {
                "name": "Automated Vulnerability Scan",
                "description": "Run automated vulnerability scanner",
                "tool": "nuclei",
                "risk": RiskLevel.MEDIUM,
            },
            {
                "name": "Web Application Scan",
                "description": "Scan web applications for vulnerabilities",
                "tool": "zap",
                "risk": RiskLevel.MEDIUM,
            },
        ],
    }
    
    def __init__(
        self,
        scope_enforcer: ScopeEnforcementEngine,
        audit_logger: SecurityAuditLogger,
        llm_client = None  # Optional LLM for enhanced recommendations
    ):
        self.scope_enforcer = scope_enforcer
        self.audit_logger = audit_logger
        self.llm_client = llm_client
        
        self.ptt: Optional[PentestingTaskTree] = None
        self._active_tasks: Dict[str, TaskNode] = {}
        
        # 통계
        self._recommendations_made = 0
        self._tasks_completed = 0
        self._findings_total = 0
    
    async def initialize_engagement(
        self,
        scope: EngagementScope,
        objectives: List[str]
    ) -> PentestingTaskTree:
        """
        펜테스팅 세션 초기화
        
        Args:
            scope: 엔게이지먼트 범위
            objectives: 테스트 목표
            
        Returns:
            초기화된 PTT
        """
        logger.info(f"Initializing engagement: {scope.engagement_name}")
        
        # PTT 생성
        primary_target = scope.domains[0] if scope.domains else scope.ip_ranges[0]
        self.ptt = PentestingTaskTree(
            target=primary_target,
            scope=scope,
            objectives=objectives
        )
        
        # 초기 정찰 태스크 생성
        initial_tasks = await self._generate_initial_tasks(scope, objectives)
        for task in initial_tasks:
            self.ptt.add_task(task)
        
        # 감사 로그
        await self.audit_logger.log_session_event(
            event_type=AuditEventType.SESSION_STARTED,
            details={
                "tree_id": self.ptt.tree_id,
                "target": primary_target,
                "objectives": objectives,
                "initial_tasks": len(initial_tasks)
            }
        )
        
        return self.ptt
    
    async def get_next_recommendation(self) -> TaskRecommendation:
        """
        다음 수행 작업 추천
        
        Returns:
            TaskRecommendation: 추천 작업과 가이드
        """
        if not self.ptt:
            raise ValueError("Engagement not initialized. Call initialize_engagement first.")
        
        self._recommendations_made += 1
        
        # 사용 가능한 태스크 조회
        available_tasks = self.ptt.get_available_tasks()
        
        if not available_tasks:
            # 페이즈 전환 확인
            can_advance, reason = self.ptt.can_advance_phase()
            
            if can_advance:
                next_phase = self._get_next_phase()
                return TaskRecommendation(
                    task=None,
                    guidance=f"Current phase ({self.ptt.current_phase.value}) is complete.",
                    tools_required=[],
                    estimated_duration_seconds=0,
                    risk_level=RiskLevel.LOW,
                    requires_approval=True,
                    is_phase_transition=True,
                    suggested_next_phase=next_phase,
                    phase_completion_summary=self._generate_phase_summary(),
                    rationale=reason
                )
            else:
                return TaskRecommendation(
                    task=None,
                    guidance="All available tasks are in progress or blocked.",
                    tools_required=[],
                    estimated_duration_seconds=0,
                    risk_level=RiskLevel.LOW,
                    requires_approval=False,
                    rationale=reason,
                    warnings=["No actionable tasks available"]
                )
        
        # 최고 점수 태스크 선택
        best_task = max(available_tasks, key=lambda t: t.priority_score)
        
        # 상세 가이드 생성
        guidance = await self._generate_task_guidance(best_task)
        
        # 대안 태스크 (상위 3개)
        alternatives = []
        for alt_task in available_tasks[1:4]:
            alt_guidance = await self._generate_task_guidance(alt_task)
            alternatives.append(TaskRecommendation(
                task=alt_task,
                guidance=alt_guidance,
                tools_required=[alt_task.tool_required] if alt_task.tool_required else [],
                estimated_duration_seconds=alt_task.estimated_duration_seconds,
                risk_level=alt_task.risk_level,
                requires_approval=alt_task.requires_approval
            ))
        
        return TaskRecommendation(
            task=best_task,
            guidance=guidance,
            tools_required=[best_task.tool_required] if best_task.tool_required else [],
            estimated_duration_seconds=best_task.estimated_duration_seconds,
            risk_level=best_task.risk_level,
            requires_approval=best_task.requires_approval,
            rationale=self._generate_task_rationale(best_task),
            suggested_commands=self._generate_suggested_commands(best_task),
            alternatives=alternatives
        )
    
    async def execute_approved_task(
        self,
        task: TaskNode,
        approval: HumanApproval,
        tool_executor = None
    ) -> TaskResult:
        """
        승인된 태스크 실행
        
        Args:
            task: 실행할 태스크
            approval: 인간 승인 정보
            tool_executor: 도구 실행기 (옵션)
            
        Returns:
            TaskResult: 실행 결과
        """
        if not approval.is_valid():
            raise ValueError("Approval is not valid or has expired")
        
        logger.info(f"Executing approved task: {task.id} - {task.name}")
        
        # 스코프 검증
        action = SecurityAction(
            action_id=generate_action_id(),
            action_type=task.name.lower().replace(" ", "_"),
            target=self.ptt.target if self.ptt else None,
            tool_name=task.tool_required,
            phase=task.phase,
            risk_level=task.risk_level
        )
        
        validation = await self.scope_enforcer.validate_action(action)
        
        if not validation.valid:
            logger.error(f"Task {task.id} failed scope validation: {validation.all_violations}")
            await self.audit_logger.log_scope_validation(action, validation)
            
            self.ptt.update_task_status(task.id, "blocked")
            
            return TaskResult(
                task_id=task.id,
                status="blocked",
                findings=[],
                raw_output=None,
                execution_time_seconds=0,
                error_message="Scope validation failed",
                error_details={"violations": validation.all_violations}
            )
        
        # 태스크 상태 업데이트
        self.ptt.update_task_status(task.id, "in_progress")
        self._active_tasks[task.id] = task
        
        # 감사 로그
        await self.audit_logger.log_action_execution(
            action=action,
            approval=approval,
            status="started",
            result_details={"task_name": task.name}
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # 도구 실행 (실제 구현 시 tool_executor 사용)
            if tool_executor:
                result = await tool_executor.execute(task)
            else:
                # 모의 실행 (개발/테스트용)
                result = await self._mock_task_execution(task)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # 결과 처리
            self.ptt.update_task_status(task.id, "completed", result)
            self._tasks_completed += 1
            self._findings_total += len(result.findings)
            
            # 발견사항 기반 새 태스크 생성
            if result.findings:
                new_tasks = await self._expand_tree_from_findings(task, result.findings)
                for new_task in new_tasks:
                    self.ptt.add_task(new_task, parent_id=task.id)
            
            # 감사 로그
            await self.audit_logger.log_action_execution(
                action=action,
                approval=approval,
                status="completed",
                result_details={
                    "findings_count": len(result.findings),
                    "execution_time": execution_time
                }
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Task execution failed: {task.id}")
            
            self.ptt.update_task_status(task.id, "failed")
            
            await self.audit_logger.log_action_execution(
                action=action,
                approval=approval,
                status="failed",
                result_details={"error": str(e)}
            )
            
            return TaskResult(
                task_id=task.id,
                status="failed",
                findings=[],
                raw_output=None,
                execution_time_seconds=0,
                error_message=str(e)
            )
        finally:
            if task.id in self._active_tasks:
                del self._active_tasks[task.id]
    
    async def _generate_initial_tasks(
        self,
        scope: EngagementScope,
        objectives: List[str]
    ) -> List[TaskNode]:
        """초기 정찰 태스크 생성"""
        tasks = []
        
        # 정찰 페이즈 템플릿에서 태스크 생성
        for template in self.PHASE_TEMPLATES.get(PentestPhase.RECONNAISSANCE, []):
            task = TaskNode(
                id=generate_task_id(),
                name=template["name"],
                description=template["description"],
                phase=PentestPhase.RECONNAISSANCE,
                status="available",
                priority_score=self._calculate_priority_score(template, scope),
                tool_required=template.get("tool"),
                risk_level=template.get("risk", RiskLevel.LOW),
                requires_approval=template.get("risk", RiskLevel.LOW) in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            )
            tasks.append(task)
        
        return tasks
    
    async def _generate_task_guidance(self, task: TaskNode) -> str:
        """태스크 수행 가이드 생성"""
        guidance_parts = [
            f"**Task**: {task.name}",
            f"**Description**: {task.description}",
            f"**Phase**: {task.phase.value}",
            f"**Risk Level**: {task.risk_level.value}",
            f"**Estimated Duration**: {task.estimated_duration_seconds // 60} minutes",
        ]
        
        if task.tool_required:
            guidance_parts.append(f"**Tool Required**: {task.tool_required}")
        
        if task.requires_approval:
            guidance_parts.append("\n⚠️ **This task requires explicit human approval before execution.**")
        
        return "\n".join(guidance_parts)
    
    def _generate_task_rationale(self, task: TaskNode) -> str:
        """태스크 추천 이유 생성"""
        reasons = []
        
        if task.phase == PentestPhase.RECONNAISSANCE:
            reasons.append("Initial reconnaissance is essential for target profiling")
        elif task.phase == PentestPhase.SCANNING:
            reasons.append("Active scanning reveals attack surface details")
        elif task.phase == PentestPhase.VULNERABILITY_ASSESSMENT:
            reasons.append("Vulnerability assessment identifies potential entry points")
        
        reasons.append(f"Priority score: {task.priority_score:.2f}")
        
        return " | ".join(reasons)
    
    def _generate_suggested_commands(self, task: TaskNode) -> List[str]:
        """제안 명령어 생성"""
        commands = []
        
        if task.tool_required == "nmap":
            commands = [
                "nmap -sV -sC -O -p- <target>",
                "nmap -sV --top-ports 1000 <target>",
                "nmap -sS -T4 -A <target>"
            ]
        elif task.tool_required == "nuclei":
            commands = [
                "nuclei -u <target> -t cves/",
                "nuclei -u <target> -t vulnerabilities/",
                "nuclei -l targets.txt -t cves/ -json"
            ]
        elif task.tool_required == "gobuster":
            commands = [
                "gobuster dir -u <target> -w /path/to/wordlist.txt",
                "gobuster dns -d <domain> -w subdomains.txt"
            ]
        
        return commands
    
    def _calculate_priority_score(
        self,
        template: Dict[str, Any],
        scope: EngagementScope
    ) -> float:
        """태스크 우선순위 점수 계산"""
        # 간단한 휴리스틱 기반 점수
        score = 0.5
        
        # 리스크 레벨에 따른 조정
        risk = template.get("risk", RiskLevel.LOW)
        if risk == RiskLevel.LOW:
            score += 0.2
        elif risk == RiskLevel.MEDIUM:
            score += 0.1
        
        # 도구 가용성
        if template.get("tool") in ["nmap", "nuclei", "gobuster"]:
            score += 0.1
        
        return min(1.0, score)
    
    async def _mock_task_execution(self, task: TaskNode) -> TaskResult:
        """모의 태스크 실행 (개발/테스트용)"""
        await asyncio.sleep(0.1)  # 시뮬레이션
        
        return TaskResult(
            task_id=task.id,
            status="completed",
            findings=[],
            raw_output=f"Mock execution of {task.name}",
            execution_time_seconds=0.1
        )
    
    async def _expand_tree_from_findings(
        self,
        parent_task: TaskNode,
        findings: List[SecurityFinding]
    ) -> List[TaskNode]:
        """발견사항 기반 새 태스크 생성"""
        new_tasks = []
        
        for finding in findings:
            if finding.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
                # 고위험 취약점에 대한 추가 검증 태스크
                task = TaskNode(
                    id=generate_task_id(),
                    name=f"Verify: {finding.title[:50]}",
                    description=f"Verify and confirm vulnerability: {finding.description[:100]}",
                    phase=PentestPhase.VULNERABILITY_ASSESSMENT,
                    status="available",
                    priority_score=0.8 if finding.severity == SeverityLevel.CRITICAL else 0.7,
                    risk_level=RiskLevel.MEDIUM,
                    requires_approval=True
                )
                new_tasks.append(task)
        
        return new_tasks
    
    def _get_next_phase(self) -> Optional[PentestPhase]:
        """다음 페이즈 반환"""
        if not self.ptt:
            return None
        
        phases = [
            PentestPhase.RECONNAISSANCE,
            PentestPhase.SCANNING,
            PentestPhase.ENUMERATION,
            PentestPhase.VULNERABILITY_ASSESSMENT,
            PentestPhase.EXPLOITATION,
            PentestPhase.POST_EXPLOITATION,
            PentestPhase.REPORTING,
        ]
        
        try:
            current_idx = phases.index(self.ptt.current_phase)
            if current_idx < len(phases) - 1:
                return phases[current_idx + 1]
        except ValueError:
            pass
        
        return None
    
    def _generate_phase_summary(self) -> str:
        """현재 페이즈 요약 생성"""
        if not self.ptt:
            return ""
        
        tasks = self.ptt.get_tasks_by_phase(self.ptt.current_phase)
        completed = sum(1 for t in tasks if t.status == "completed")
        
        findings = [f for f in self.ptt.findings if any(
            t.phase == self.ptt.current_phase for t in tasks
        )]
        
        return (
            f"Phase: {self.ptt.current_phase.value}\n"
            f"Tasks completed: {completed}/{len(tasks)}\n"
            f"Findings: {len(findings)}"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        return {
            "recommendations_made": self._recommendations_made,
            "tasks_completed": self._tasks_completed,
            "findings_total": self._findings_total,
            "active_tasks": len(self._active_tasks),
            "ptt_summary": self.ptt.get_summary() if self.ptt else None
        }