import uuid
import asyncio
import logging
from datetime import datetime
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

    async def create_task(
        self,
        agent_url: str,
        task_type: str,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: int = 0,
    ) -> A2ATask:
        """agent_url이 local://로 시작해야 하며, 바로 해당 객체의 handle_task(task) 비동기 호출."""
        if not agent_url.startswith("local://"):
            raise ValueError(f"Only local:// URLs supported, got: {agent_url}")
        agent_name = agent_url.replace("local://", "")
        agent = self._agents.get(agent_name)
        if not agent:
            raise RuntimeError(f"Agent [{agent_name}] not registered. Available: {list(self._agents.keys())}")

        task_id = str(uuid.uuid4())
        task = A2ATask(
            task_id=task_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            task_type=task_type,
            status=TaskStatus.PENDING,
            context=context,
            created_at=datetime.utcnow(),
        )
        self._tasks[task_id] = task

        asyncio.create_task(self._safe_execute(agent, task))
        return task

    async def _safe_execute(self, agent, task: A2ATask):
        try:
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.utcnow()
            handler = getattr(agent, "handle_task", None) or getattr(agent, "process_task", None)
            if not handler:
                raise AttributeError(f"{agent} has no handle_task or process_task method")
            result = await handler(task)   # 실제 에이전트 처리
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = getattr(result, "content", None) if hasattr(result, "content") else result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.logger.exception(f"Task {task.task_id} failed: {e}")

    async def get_task_status(self, agent_url: str, task_id: str) -> A2ATask:
        """메모리에서 Task 객체 상태를 반환."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"No such task: {task_id}")
        return task

    async def send_message(self, agent_url: str, message: Any) -> Dict[str, Any]:
        """agent_url로 메시지를 직접 함수 호출(테스트용 단순화)."""
        return {"status": "sent", "timestamp": datetime.utcnow().isoformat()}
