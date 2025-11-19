"""A2A Server Base Implementation"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..models.a2a_models import AgentCard, A2AMessage, A2ATask, Artifact, TaskStatus


class A2ATaskRequest(BaseModel):
    """A2A Task request model"""
    task_type: str
    context: Dict[str, Any]
    correlation_id: Optional[str] = None


class A2ATaskResponse(BaseModel):
    """A2A Task response model"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    artifact: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TaskHandler:
    """Decorator for A2A task handlers"""
    def __init__(self, task_type: Optional[str] = None):
        self.task_type = task_type
    
    def __call__(self, func: Callable) -> Callable:
        func._is_task_handler = True
        func._task_type = self.task_type or func.__name__
        return func


class A2AServer(ABC):
    """Base class for A2A Server agents"""
    
    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.task_handlers: Dict[str, Callable] = {}
        self.current_tasks: Dict[str, A2ATask] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Discover task handlers
        self._discover_handlers()
    
    def _discover_handlers(self):
        """Discover task handler methods"""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_is_task_handler'):
                task_type = attr._task_type
                self.task_handlers[task_type] = attr
                self.logger.info(f"Registered handler for task type: {task_type}")
    
    async def handle_task_request(self, request: A2ATaskRequest) -> A2ATaskResponse:
        """Handle incoming A2A task request"""
        task = A2ATask(
            task_type=request.task_type,
            context=request.context,
            assigned_agent=self.agent_card.agent_id
        )
        
        self.current_tasks[task.task_id] = task
        
        try:
            # Find and execute handler
            if request.task_type not in self.task_handlers:
                raise ValueError(f"No handler for task type: {request.task_type}")
            
            handler = self.task_handlers[request.task_type]
            task.status = TaskStatus.IN_PROGRESS
            task.updated_at = datetime.utcnow()
            
            # Execute task handler
            result = await handler(task)
            
            # Process result
            if isinstance(result, Artifact):
                task.result = {"artifact_id": result.artifact_id}
                task.status = TaskStatus.COMPLETED
                response_artifact = {
                    "artifact_id": result.artifact_id,
                    "type": result.artifact_type,
                    "content": result.content,
                    "metadata": result.metadata,
                    "quality_score": result.quality_score
                }
            else:
                task.result = result
                task.status = TaskStatus.COMPLETED
                response_artifact = None
            
            task.updated_at = datetime.utcnow()
            
            return A2ATaskResponse(
                task_id=task.task_id,
                status=task.status.value,
                result=task.result,
                artifact=response_artifact
            )
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.utcnow()
            
            self.logger.error(f"Task {task.task_id} failed: {e}")
            
            return A2ATaskResponse(
                task_id=task.task_id,
                status=task.status.value,
                error=str(e)
            )
    
    async def get_task_status(self, task_id: str) -> A2ATaskResponse:
        """Get current task status"""
        if task_id not in self.current_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = self.current_tasks[task_id]
        return A2ATaskResponse(
            task_id=task.task_id,
            status=task.status.value,
            result=task.result,
            error=task.error
        )
    
    def create_agent_card(self) -> AgentCard:
        """Create agent card - to be implemented by subclasses"""
        return self.agent_card
    
    def create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application with A2A endpoints"""
        app = FastAPI(
            title=f"{self.agent_card.agent_name} A2A Server",
            version=self.agent_card.version
        )
        
        @app.post("/a2a/tasks", response_model=A2ATaskResponse)
        async def create_task(request: A2ATaskRequest):
            return await self.handle_task_request(request)
        
        @app.get("/a2a/tasks/{task_id}", response_model=A2ATaskResponse)
        async def get_task(task_id: str):
            return await self.get_task_status(task_id)
        
        @app.get("/a2a/agent-card")
        async def get_agent_card():
            return self.agent_card.to_dict()
        
        @app.get("/a2a/capabilities")
        async def get_capabilities():
            return {
                "capabilities": self.agent_card.capabilities,
                "task_types": list(self.task_handlers.keys())
            }
        
        return app