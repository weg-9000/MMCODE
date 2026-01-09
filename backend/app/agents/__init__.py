"""
Agent System Integration Module

This module provides integration between the new modular A2A agent architecture
and the existing FastAPI system for backward compatibility.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import logging

# Import new modular agents
from .requirement_analyzer.core.agent import RequirementAnalyzer
from .requirement_analyzer.config.settings import get_agent_config

# Import security agents
from .threat_analyzer.core.agent import ThreatAnalyzer

# Import shared A2A infrastructure
from .shared.models.a2a_models import AgentCard, A2ATask, Artifact
from .shared.a2a_client.client import A2AClient
from .shared.registry.agent_registry import AgentRegistry


@dataclass
class PentestingSession:
    """Pentesting session model"""
    session_id: str
    scope: Any
    requester_id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    findings: List[Any] = field(default_factory=list)


@dataclass
class TaskExecutionResult:
    """Task execution result model"""
    task_id: str
    execution_result: Any
    next_recommendations: List[Any] = field(default_factory=list)


class AgentSystemManager:
    """
    Manager for the entire agent system, providing both legacy and A2A interfaces
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize requirement analyzer (main orchestrator)
        self.requirement_analyzer = RequirementAnalyzer(get_agent_config())
        
        # Initialize security agents
        from ..security import ScopeEnforcementEngine, SecurityAuditLogger
        self.scope_enforcer = ScopeEnforcementEngine()
        self.audit_logger = SecurityAuditLogger()
        self.threat_analyzer = ThreatAnalyzer(
            scope_enforcer=self.scope_enforcer,
            audit_logger=self.audit_logger
        )
        
        # A2A infrastructure
        self.a2a_client = A2AClient()
        self.agent_registry: Optional[AgentRegistry] = None

        # Session management
        self.session_lock = asyncio.Lock()
        self.active_sessions: Dict[str, PentestingSession] = {}
        self.approval_integration = None
        
    async def initialize(self, redis_client=None):
        """Initialize the agent system"""
        if redis_client:
            self.agent_registry = AgentRegistry(redis_client)
            
        self.logger.info("Agent system initialized")
    
    # Legacy interface methods for backward compatibility
    async def analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        Legacy interface: Analyze requirements only
        """
        try:
            analysis_result = await self.requirement_analyzer.analyze_requirements_only(requirements)
            return analysis_result.to_dict()
        except Exception as e:
            self.logger.error(f"Requirement analysis failed: {e}")
            raise
    
    async def run_full_orchestration(self, requirements: str, session_id: str) -> Dict[str, Any]:
        """
        New A2A interface: Full analysis and orchestration
        """
        try:
            return await self.requirement_analyzer.analyze_and_orchestrate(requirements, session_id)
        except Exception as e:
            self.logger.error(f"Full orchestration failed: {e}")
            raise
    
    async def start_pentest_session(
        self,
        scope,  # EngagementScope
        requester_id: str,
        session_config: Optional[Dict[str, Any]] = None
    ) -> PentestingSession:
        """
        침투 테스트 세션 시작
        
        Args:
            scope: 테스트 범위 정의
            requester_id: 요청자 ID
            session_config: 세션 설정 (선택)
            
        Returns:
            PentestingSession: 생성된 세션
        """
        async with self.session_lock:
            # 1. 범위 검증
            validation = await self.scope_enforcer.validate_scope(scope)
            if not validation.valid:
                raise ValueError(f"Scope validation failed: {validation.all_violations}")
            
            # 2. 세션 생성
            session_id = self._generate_session_id()
            session = PentestingSession(
                session_id=session_id,
                scope=scope,
                requester_id=requester_id,
                status="INITIALIZING",
                created_at=datetime.now(timezone.utc)
            )
            
            # 3. ThreatAnalyzer 초기화
            await self.threat_analyzer.initialize_session(session)
            
            # 4. 감사 로그
            await self.audit_logger.log_session_start(session)
            
            # 5. 세션 저장
            self.active_sessions[session.session_id] = session
            session.status = "ACTIVE"
            
            self.logger.info(f"Started pentest session: {session_id}")
            return session
    
    async def execute_recommended_task(
        self,
        session_id: str,
        task_id: str,
        approver_info: Optional[Dict[str, str]] = None
    ) -> TaskExecutionResult:
        """
        추천된 작업 실행
        
        Args:
            session_id: 세션 ID
            task_id: 실행할 작업 ID
            approver_info: 승인자 정보 (필요시)
        """
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # 1. 작업 조회
        task = await self.threat_analyzer.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # 2. SecurityAction 생성
        from ..security.models import SecurityAction, generate_action_id
        action = SecurityAction(
            action_id=generate_action_id(),
            action_type=getattr(task, 'task_type', 'unknown'),
            target=getattr(task, 'target', ''),
            tool_name=getattr(task, 'tool', 'unknown'),
            command=getattr(task, 'command', ''),
            phase=getattr(task, 'phase', None),
            risk_level=getattr(task, 'risk_level', None),
            parameters={
                'session_id': session_id,
                'task_id': task_id
            }
        )
        
        # 3. 도구 실행기 선택
        tool_executor = self._get_tool_executor(getattr(task, 'tool', 'unknown'))
        
        # 4. 승인 통합 실행
        if self.approval_integration:
            result = await self.approval_integration.execute_with_approval(
                action=action,
                tool_executor=tool_executor,
                session_id=session_id
            )
        else:
            # 승인 없이 직접 실행 (개발 환경)
            self.logger.warning("No approval integration, executing directly")
            tool_result = await tool_executor.execute(action.target, action.parameters)
            result = self._convert_tool_result_to_execution_result(tool_result, action.action_id)
        
        # 5. PTT 업데이트
        await self.threat_analyzer.update_task_result(
            task_id=task_id,
            result=result
        )
        
        # 6. 다음 작업 추천 생성
        next_recommendations = await self.threat_analyzer.get_recommendations(
            session_id=session_id,
            limit=5
        )
        
        return TaskExecutionResult(
            task_id=task_id,
            execution_result=result,
            next_recommendations=next_recommendations
        )
    
    async def handle_approval_response(
        self,
        request_id: str,
        approved: bool,
        approver_id: str,
        reason: Optional[str] = None,
        conditions: Optional[List[str]] = None
    ):
        """
        승인 응답 처리 (외부 API에서 호출)
        
        Args:
            request_id: 승인 요청 ID
            approved: 승인 여부
            approver_id: 승인자 ID
            reason: 승인/거부 사유
            conditions: 승인 조건 (선택)
        """
        if not self.approval_integration:
            raise ValueError("Approval integration not available")
        
        result = await self.approval_integration.approval_workflow.process_approval(
            request_id=request_id,
            approved=approved,
            approver_id=approver_id,
            reason=reason,
            conditions_accepted=conditions
        )
        
        # 대기 중인 콜백 실행 (만약 있다면)
        if hasattr(self.approval_integration, '_approval_callbacks'):
            if request_id in self.approval_integration._approval_callbacks:
                callback = self.approval_integration._approval_callbacks[request_id]
                await callback(result)
                del self.approval_integration._approval_callbacks[request_id]
        
        return result
    
    async def end_session(self, session_id: str, reason: str = "Completed"):
        """세션 종료"""
        async with self.session_lock:
            session = self.active_sessions.get(session_id)
            if session:
                session.status = "COMPLETED"
                session.updated_at = datetime.now(timezone.utc)
                
                # 감사 로그
                try:
                    await self.audit_logger.log_session_end(session, reason)
                except Exception as e:
                    self.logger.error(f"Failed to log session end: {e}")
                
                # 세션 제거
                del self.active_sessions[session_id]
                
                self.logger.info(f"Ended session {session_id}: {reason}")
    
    async def execute_single_agent_task(self, 
                                      agent_name: str, 
                                      task_type: str, 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task on specific agent (A2A interface)
        """
        try:
            task_result = await self.requirement_analyzer.execute_agent_task(
                agent_name, task_type, context
            )
            return {
                "task_id": task_result.task_id,
                "status": task_result.status.value,
                "result": task_result.result,
                "error": task_result.error
            }
        except Exception as e:
            self.logger.error(f"Agent task execution failed: {e}")
            raise
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get health status of entire agent system
        """
        try:
            return await self.requirement_analyzer.health_check()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Clean up resources"""
        await self.requirement_analyzer.close()
        await self.a2a_client.close()
    
    # Security-specific methods
    async def analyze_security_threats(self, scope, objectives: list) -> Dict[str, Any]:
        """
        Initialize security threat analysis session
        """
        try:
            ptt = await self.threat_analyzer.initialize_engagement(scope, objectives)
            return {
                "tree_id": ptt.tree_id,
                "target": ptt.target,
                "status": "initialized",
                "summary": ptt.get_summary()
            }
        except Exception as e:
            self.logger.error(f"Security threat analysis failed: {e}")
            raise
    
    async def get_security_recommendation(self) -> Dict[str, Any]:
        """
        Get next security task recommendation
        """
        try:
            recommendation = await self.threat_analyzer.get_next_recommendation()
            return {
                "task": recommendation.task.to_dict() if recommendation.task else None,
                "guidance": recommendation.guidance,
                "tools_required": recommendation.tools_required,
                "risk_level": recommendation.risk_level.value,
                "requires_approval": recommendation.requires_approval,
                "rationale": recommendation.rationale,
                "suggested_commands": recommendation.suggested_commands
            }
        except Exception as e:
            self.logger.error(f"Security recommendation failed: {e}")
            raise
    
    async def execute_security_task(self, task, approval) -> Dict[str, Any]:
        """
        Execute approved security task
        """
        try:
            result = await self.threat_analyzer.execute_approved_task(task, approval)
            return {
                "task_id": result.task_id,
                "status": result.status,
                "findings_count": len(result.findings),
                "execution_time": result.execution_time_seconds,
                "error_message": result.error_message
            }
        except Exception as e:
            self.logger.error(f"Security task execution failed: {e}")
            raise
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session.session_id,
            "status": session.status,
            "requester_id": session.requester_id,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "active_tasks": await self._get_active_tasks(session_id)
        }
    
    async def _get_active_tasks(self, session_id: str) -> List[Dict[str, Any]]:
        """활성 작업 목록 조회"""
        try:
            # ThreatAnalyzer에서 세션 작업 조회
            if hasattr(self.threat_analyzer, 'get_session_tasks'):
                tasks = await self.threat_analyzer.get_session_tasks(session_id)
                return [{
                    "task_id": getattr(task, 'id', 'unknown'),
                    "name": getattr(task, 'name', 'unknown'),
                    "status": getattr(task, 'status', 'unknown'),
                    "phase": getattr(task, 'phase', {}).get('value', 'unknown') if hasattr(getattr(task, 'phase', None), 'value') else str(getattr(task, 'phase', 'unknown'))
                } for task in tasks]
            else:
                return []
        except Exception as e:
            self.logger.error(f"Failed to get active tasks: {e}")
            return []
    
    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        import uuid
        return f"sess_{uuid.uuid4().hex[:12]}"
    
    def _get_tool_executor(self, tool_name: str):
        """도구 실행기 팩토리"""
        try:
            from ..tools.network import NmapTool
            from ..tools.vulnerability import NucleiTool
            from ..tools.base import BaseSecurityTool
            
            executors = {
                "nmap": NmapTool,
                "nuclei": NucleiTool,
                # 추가 도구...
            }
            
            executor_class = executors.get(tool_name.lower())
            if not executor_class:
                # 기본 Mock 실행기 사용
                class MockExecutor(BaseSecurityTool):
                    def __init__(self):
                        self.tool_name = tool_name
                    
                    async def execute(self, target, params):
                        class MockResult:
                            success = True
                            output = f"Mock execution of {tool_name} on {target}"
                            findings = []
                            execution_time = 1.0
                        return MockResult()
                
                return MockExecutor()
            
            return executor_class(
                scope_enforcer=self.scope_enforcer,
                audit_logger=self.audit_logger
            )
        except Exception as e:
            self.logger.error(f"Failed to create tool executor for {tool_name}: {e}")
            # 에러 시 Mock 사용
            class ErrorMockExecutor:
                def __init__(self):
                    self.tool_name = tool_name
                
                async def execute(self, target, params):
                    class ErrorResult:
                        success = False
                        output = f"Error creating executor for {tool_name}: {e}"
                        findings = []
                        execution_time = 0.0
                    return ErrorResult()
            
            return ErrorMockExecutor()
    
    def _convert_tool_result_to_execution_result(self, tool_result, action_id):
        """ToolResult를 ExecutionResult로 변환"""
        try:
            from ..security.approval_integration import ExecutionResult
            
            return ExecutionResult(
                success=getattr(tool_result, 'success', False),
                action_id=action_id,
                status="completed" if getattr(tool_result, 'success', False) else "failed",
                message=getattr(tool_result, 'output', str(tool_result)),
                findings=getattr(tool_result, 'findings', []),
                execution_time=getattr(tool_result, 'execution_time', 0.0)
            )
        except Exception as e:
            self.logger.error(f"Failed to convert tool result: {e}")
            # 기본 ExecutionResult 반환
            from ..security.approval_integration import ExecutionResult
            return ExecutionResult(
                success=False,
                action_id=action_id,
                status="failed",
                message=f"Conversion error: {e}",
                findings=[],
                execution_time=0.0
            )


# Global agent system manager instance
_agent_manager: Optional[AgentSystemManager] = None


def get_agent_manager(config: Optional[Dict[str, Any]] = None) -> AgentSystemManager:
    """Get global agent manager instance"""
    global _agent_manager
    
    if _agent_manager is None:
        if config is None:
            config = get_agent_config()
        _agent_manager = AgentSystemManager(config)
    
    return _agent_manager


async def initialize_agent_system(config: Dict[str, Any], redis_client=None):
    """Initialize the global agent system"""
    global _agent_manager
    _agent_manager = AgentSystemManager(config)
    await _agent_manager.initialize(redis_client)


# Legacy interface functions for backward compatibility
async def analyze_requirements_legacy(requirements: str) -> Dict[str, Any]:
    """Legacy function for requirement analysis"""
    manager = get_agent_manager()
    return await manager.analyze_requirements(requirements)


# Export key classes and functions
__all__ = [
    'AgentSystemManager',
    'get_agent_manager', 
    'initialize_agent_system',
    'analyze_requirements_legacy',
    'RequirementAnalyzer',
    'ThreatAnalyzer',
    'AgentCard',
    'A2ATask', 
    'Artifact',
    'A2AClient',
    'AgentRegistry',
    'PentestingSession',
    'TaskExecutionResult'
]