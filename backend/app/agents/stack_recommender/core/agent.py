"""
A2A Server core implementation for StackRecommender agent.
Handles task reception, processing, and response generation.
"""

from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import uuid
import time
from datetime import datetime
import logging

from ..models.task_models import (
    A2ATask, A2ATaskUpdate, A2ATaskResult, TaskStatus, TaskArtifact,
    AgentCard, StackRecommendationRequest, TaskProgress, TaskError
)
from ..models.stack_models import StackArtifact, ArchitectureContext
from ..config.settings import settings
from ..capabilities.stack_analysis import StackAnalysisEngine
from ..utils.quality_scorer import QualityScorer

# Setup logging
logger = logging.getLogger(__name__)


class A2AStackRecommenderServer:
    """A2A Server implementation for Stack Recommendation Agent"""
    
    def __init__(self):
        self.app = FastAPI(
            title=settings.agent_name,
            description=settings.agent_description,
            version=settings.agent_version
        )
        
        # Core components
        self.analysis_engine = StackAnalysisEngine()
        self.quality_scorer = QualityScorer()
        
        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_results: Dict[str, A2ATaskResult] = {}
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes for A2A protocol"""
        
        @self.app.get("/")
        async def health_check():
            """Health check endpoint"""
            return {
                "agent": settings.agent_name,
                "version": settings.agent_version,
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.get("/a2a/agent-card", response_model=AgentCard)
        async def get_agent_card():
            """Return agent card for A2A discovery"""
            return AgentCard(**settings.agent_card_data)
        
        @self.app.post("/a2a/tasks", response_model=Dict[str, str])
        async def create_task(
            task_request: StackRecommendationRequest,
            background_tasks: BackgroundTasks
        ):
            """Create and execute A2A task"""
            
            task_id = str(uuid.uuid4())
            
            # Create task record
            task = A2ATask(
                id=task_id,
                agent_name=settings.agent_name,
                skill_id="stack-recommendation",
                context={
                    "session_id": task_request.session_id,
                    "architecture": task_request.architecture_context,
                    "requirements": task_request.requirements,
                    "constraints": task_request.constraints,
                    "user_preferences": task_request.preferences
                },
                created_by="requirement-analyzer"
            )
            
            # Track task
            self.active_tasks[task_id] = {
                "task": task,
                "status": TaskStatus.SUBMITTED,
                "created_at": datetime.utcnow(),
                "progress": TaskProgress(percentage=0.0, current_step="Submitted")
            }
            
            # Execute task in background
            background_tasks.add_task(self._execute_task, task_id, task)
            
            logger.info(f"Created task {task_id} for session {task_request.session_id}")
            
            return {"task_id": task_id, "status": "submitted"}
        
        @self.app.get("/a2a/tasks/{task_id}", response_model=A2ATaskUpdate)
        async def get_task_status(task_id: str):
            """Get task execution status"""
            
            if task_id not in self.active_tasks and task_id not in self.task_results:
                raise HTTPException(status_code=404, detail="Task not found")
            
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                return A2ATaskUpdate(
                    task_id=task_id,
                    status=task_info["status"],
                    progress=task_info.get("progress"),
                    error=task_info.get("error"),
                    message=task_info.get("message", "")
                )
            else:
                result = self.task_results[task_id]
                return A2ATaskUpdate(
                    task_id=task_id,
                    status=result.status,
                    message="Task completed"
                )
        
        @self.app.get("/a2a/tasks/{task_id}/result", response_model=A2ATaskResult)
        async def get_task_result(task_id: str):
            """Get task execution result"""
            
            if task_id not in self.task_results:
                if task_id in self.active_tasks:
                    status = self.active_tasks[task_id]["status"]
                    if status in [TaskStatus.SUBMITTED, TaskStatus.WORKING]:
                        raise HTTPException(status_code=202, detail="Task still processing")
                    elif status == TaskStatus.FAILED:
                        raise HTTPException(status_code=500, detail="Task failed")
                raise HTTPException(status_code=404, detail="Task result not found")
            
            return self.task_results[task_id]
        
        @self.app.delete("/a2a/tasks/{task_id}")
        async def cancel_task(task_id: str):
            """Cancel active task"""
            
            if task_id not in self.active_tasks:
                raise HTTPException(status_code=404, detail="Task not found or already completed")
            
            self.active_tasks[task_id]["status"] = TaskStatus.CANCELLED
            self.active_tasks[task_id]["message"] = "Task cancelled by request"
            
            return {"message": "Task cancelled"}
    
    async def _execute_task(self, task_id: str, task: A2ATask):
        """Execute stack recommendation task"""
        
        start_time = time.time()
        
        try:
            # Update status to working
            self._update_task_status(
                task_id, 
                TaskStatus.WORKING,
                TaskProgress(percentage=10.0, current_step="Initializing analysis")
            )
            
            # Parse architecture context
            arch_context = ArchitectureContext(**task.context["architecture"])
            
            # Update progress
            self._update_task_status(
                task_id,
                TaskStatus.WORKING, 
                TaskProgress(percentage=30.0, current_step="Analyzing architecture")
            )
            
            # Perform stack analysis
            recommendation = await self.analysis_engine.analyze_and_recommend(
                architecture=arch_context,
                requirements=task.context.get("requirements", {}),
                constraints=task.context.get("constraints", {})
            )
            
            # Update progress
            self._update_task_status(
                task_id,
                TaskStatus.WORKING,
                TaskProgress(percentage=70.0, current_step="Calculating quality scores")
            )
            
            # Calculate quality scores
            quality_score = await self.quality_scorer.evaluate_recommendation(
                recommendation, arch_context
            )
            
            # Create artifact
            artifact = StackArtifact(
                recommendation=recommendation,
                quality_score=quality_score,
                rationale=f"Recommended stack for {arch_context.domain} application with {arch_context.scale} scale",
                implementation_notes=[
                    "Consider team expertise when implementing",
                    "Start with MVP features and scale gradually", 
                    "Implement monitoring and logging early",
                    "Plan for security and compliance requirements"
                ],
                next_steps=[
                    "Review recommendation with team",
                    "Validate technology choices against constraints",
                    "Create implementation timeline",
                    "Setup development environment"
                ]
            )
            
            # Update progress
            self._update_task_status(
                task_id,
                TaskStatus.WORKING,
                TaskProgress(percentage=95.0, current_step="Finalizing results")
            )
            
            # Create task result
            execution_time = time.time() - start_time
            result = A2ATaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                artifacts=[TaskArtifact(
                    type="stack-recommendation",
                    content=artifact.dict(),
                    metadata={
                        "quality_score": quality_score.overall_score,
                        "execution_time": execution_time,
                        "agent_version": settings.agent_version
                    }
                )],
                execution_time=execution_time,
                quality_metrics={
                    "overall_score": quality_score.overall_score,
                    "suitability": quality_score.suitability,
                    "completeness": quality_score.completeness,
                    "feasibility": quality_score.feasibility
                }
            )
            
            # Store result and cleanup
            self.task_results[task_id] = result
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            logger.info(f"Completed task {task_id} in {execution_time:.2f}s with quality score {quality_score.overall_score}")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            
            # Create error result
            error = TaskError(
                code="EXECUTION_ERROR",
                message=str(e),
                recoverable=True
            )
            
            self._update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=error
            )
            
            # Store failed result
            execution_time = time.time() - start_time
            self.task_results[task_id] = A2ATaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts=[],
                execution_time=execution_time
            )
            
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def _update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus,
        progress: Optional[TaskProgress] = None,
        error: Optional[TaskError] = None,
        message: str = ""
    ):
        """Update task status and progress"""
        
        if task_id in self.active_tasks:
            self.active_tasks[task_id].update({
                "status": status,
                "progress": progress,
                "error": error,
                "message": message,
                "updated_at": datetime.utcnow()
            })


# Global agent server instance
agent_server = A2AStackRecommenderServer()

# FastAPI app for deployment
app = agent_server.app