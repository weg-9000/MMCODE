import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.agents.shared.models.a2a_models import A2ATask, TaskStatus

class InMemoryA2AClient:
    """
    A2A-호환 에이전트 인메모리 테스트 클라이언트.
    agent_url(local://agent-name) 기준으로 로컬 에이전트를 찾아 직접 함수 호출.
    """
    def __init__(self):
        self._agents: Dict[str, Any] = {}        # agent_name: agent_instance
        self._tasks: Dict[str, A2ATask] = {}     
        self.logger = logging.getLogger(self.__class__.__name__)

    def register(self, agent_name: str, agent_instance: Any):
        """로컬 호출할 에이전트 객체를 등록. agent_name은 예: architect-agent"""
        self._agents[agent_name] = agent_instance

    def is_registered(self, agent_name: str) -> bool:
        """Check if an agent is registered in the client."""
        return agent_name in self._agents

    def get_registered_agents(self) -> list:
        """Get list of all registered agent names."""
        return list(self._agents.keys())

    def _extract_agent_name_from_url(self, agent_url: str) -> str:
        """Extract agent name from various URL formats"""
        if agent_url.startswith("local://"):
            return agent_url.replace("local://", "")
        elif "localhost" in agent_url:
            # Map HTTP localhost URLs to agent names based on port
            port = agent_url.split(":")[-1].rstrip("/")
            port_to_name = {
                "8001": "architect", 
                "8002": "stack_recommender", 
                "8003": "documenter"
            }
            return port_to_name.get(port, f"agent_port_{port}")
        else:
            # Fallback: use the last part of the URL
            return agent_url.split("/")[-1].rstrip("/")

    async def create_task(
        self,
        agent_url: str,
        task_type: str,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: int = 0,
    ) -> A2ATask:
        """Create task on target agent, supporting both local:// and HTTP URLs"""
        agent_name = self._extract_agent_name_from_url(agent_url)
        self.logger.info(f"Extracted agent name '{agent_name}' from URL '{agent_url}'")
        
        agent = self._agents.get(agent_name)
        if not agent:
            self.logger.error(f"Agent [{agent_name}] not registered. Available: {list(self._agents.keys())}")
            raise RuntimeError(f"Agent [{agent_name}] not registered. Available: {list(self._agents.keys())}")

        task_id = str(uuid.uuid4())
        task = A2ATask(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            context=context,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._tasks[task_id] = task

        asyncio.create_task(self._safe_execute(agent, task))
        return task

    async def _safe_execute(self, agent, task: A2ATask):
        try:
            task.status = TaskStatus.IN_PROGRESS
            task.updated_at = datetime.now(timezone.utc)
            handler = getattr(agent, "handle_task", None) or getattr(agent, "process_task", None)
            if not handler:
                raise AttributeError(f"{agent} has no handle_task or process_task method")
            result = await handler(task)   # 실제 에이전트 처리
            task.status = TaskStatus.COMPLETED
            task.updated_at = datetime.now(timezone.utc)
            task.result = getattr(result, "content", None) if hasattr(result, "content") else result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.now(timezone.utc)
            self.logger.exception(f"Task {task.task_id} failed: {e}")

    async def get_task_status(self, agent_url: str, task_id: str) -> A2ATask:
        """메모리에서 Task 객체 상태를 반환."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"No such task: {task_id}")
        return task

    async def send_message(self, agent_url: str, message: Any) -> Dict[str, Any]:
        """agent_url로 메시지를 직접 함수 호출(테스트용 단순화)."""
        return {"status": "sent", "timestamp": datetime.now(timezone.utc).isoformat()}

    async def create_task_with_wait(self, 
                                   agent_url: str,
                                   task_type: str, 
                                   context: Dict[str, Any],
                                   correlation_id: Optional[str] = None,
                                   max_wait_time: float = 300.0) -> A2ATask:
        """Create task and wait for completion (mock implementation)"""
        task = await self.create_task(agent_url, task_type, context, correlation_id)
        
        # Wait for task completion with timeout
        start_time = datetime.now(timezone.utc)
        while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            if (datetime.now(timezone.utc) - start_time).total_seconds() > max_wait_time:
                task.status = TaskStatus.FAILED
                task.error = f"Task timeout after {max_wait_time} seconds"
                break
            await asyncio.sleep(0.1)  # Short polling interval for tests
        
        return task

    async def get_agent_capabilities(self, agent_url: str) -> Dict[str, Any]:
        """Get agent capabilities (mock implementation)"""
        agent_name = self._extract_agent_name_from_url(agent_url)
        if agent_name in self._agents:
            return {
                "agent_id": agent_name,
                "capabilities": ["mock_capability"],
                "status": "healthy"
            }
        else:
            raise RuntimeError(f"Agent [{agent_name}] not registered")

    async def close(self):
        """Close client connection (mock - no-op)"""
        pass
