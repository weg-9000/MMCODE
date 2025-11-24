"""A2A Client Implementation"""

import aiohttp
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone

from ..models.a2a_models import AgentCard, A2ATask, A2AMessage, Artifact, TaskStatus


class A2AClient:
    """A2A Client for agent-to-agent communication"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is available"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def create_task(self, 
                         agent_url: str, 
                         task_type: str, 
                         context: Dict[str, Any],
                         correlation_id: Optional[str] = None) -> A2ATask:
        """Create a new task on target agent"""
        await self._ensure_session()
        
        request_data = {
            "task_type": task_type,
            "context": context,
            "correlation_id": correlation_id
        }
        
        try:
            async with self.session.post(
                f"{agent_url}/a2a/tasks",
                json=request_data
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                return A2ATask(
                    task_id=data["task_id"],
                    task_type=task_type,
                    status=TaskStatus(data["status"]),
                    context=context,
                    result=data.get("result"),
                    error=data.get("error"),
                    assigned_agent=agent_url
                )
                
        except Exception as e:
            self.logger.error(f"Failed to create task on {agent_url}: {e}")
            raise
    
    async def get_task_status(self, agent_url: str, task_id: str) -> A2ATask:
        """Get task status from agent"""
        await self._ensure_session()
        
        try:
            async with self.session.get(
                f"{agent_url}/a2a/tasks/{task_id}"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                return A2ATask(
                    task_id=data["task_id"],
                    status=TaskStatus(data["status"]),
                    result=data.get("result"),
                    error=data.get("error")
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get task status from {agent_url}: {e}")
            raise
    
    async def wait_for_task(self, 
                           agent_url: str, 
                           task_id: str,
                           poll_interval: float = 1.0,
                           max_wait_time: float = 300.0) -> A2ATask:
        """Wait for task completion with polling"""
        start_time = datetime.now(timezone.utc)
        max_time = timedelta(seconds=max_wait_time)
        
        while True:
            task = await self.get_task_status(agent_url, task_id)
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return task
                
            # Check timeout
            if datetime.now(timezone.utc) - start_time > max_time:
                self.logger.warning(f"Task {task_id} timed out after {max_wait_time} seconds")
                raise TimeoutError(f"Task {task_id} did not complete within {max_wait_time} seconds")
            
            await asyncio.sleep(poll_interval)
    
    async def get_agent_capabilities(self, agent_url: str) -> Dict[str, Any]:
        """Get agent capabilities"""
        await self._ensure_session()
        
        try:
            async with self.session.get(
                f"{agent_url}/a2a/capabilities"
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except Exception as e:
            self.logger.error(f"Failed to get capabilities from {agent_url}: {e}")
            raise
    
    async def get_agent_card(self, agent_url: str) -> AgentCard:
        """Get agent card information"""
        await self._ensure_session()
        
        try:
            async with self.session.get(
                f"{agent_url}/a2a/agent-card"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                return AgentCard(
                    agent_id=data["agent_id"],
                    agent_name=data["agent_name"],
                    framework=data["framework"],
                    capabilities=data["capabilities"],
                    endpoint_url=data["endpoint_url"],
                    version=data["version"],
                    metadata=data.get("metadata", {})
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get agent card from {agent_url}: {e}")
            raise
    
    async def create_task_with_wait(self,
                                   agent_url: str,
                                   task_type: str,
                                   context: Dict[str, Any],
                                   correlation_id: Optional[str] = None,
                                   max_wait_time: float = 300.0) -> A2ATask:
        """Create task and wait for completion"""
        task = await self.create_task(agent_url, task_type, context, correlation_id)
        return await self.wait_for_task(agent_url, task.task_id, max_wait_time=max_wait_time)
    
    async def close(self):
        """Close the client session"""
        if self.session:
            await self.session.close()