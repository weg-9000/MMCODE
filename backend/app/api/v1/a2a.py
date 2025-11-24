"""
A2A Communication API Endpoints
Agent-to-Agent task processing, status monitoring, and communication management
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import uuid
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.models import Task, Agent
from app.agents.shared.models.a2a_models import (
    A2ATask, TaskStatus
)
from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient
from app.agents.shared.a2a_client.client import A2AClient

logger = logging.getLogger(__name__)
router = APIRouter()

# Global A2A clients
_memory_client: Optional[InMemoryA2AClient] = None
_http_client: Optional[A2AClient] = None

class A2ATaskResult(BaseModel):
    """Task execution result"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0

class A2ATaskUpdate(BaseModel):
    """Task status update"""
    status: str
    progress: float = 0.0
    message: Optional[str] = None
    
def get_memory_client() -> InMemoryA2AClient:
    """Get or create in-memory A2A client"""
    global _memory_client
    if _memory_client is None:
        _memory_client = InMemoryA2AClient()
    return _memory_client


def get_http_client() -> A2AClient:
    """Get or create HTTP A2A client"""
    global _http_client
    if _http_client is None:
        _http_client = A2AClient()
    return _http_client


@router.post("/tasks", response_model=Dict[str, Any])
async def create_a2a_task(
    task_request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new A2A task"""
    try:
        # Validate required fields
        required_fields = ["agent_url", "task_type", "context"]
        missing_fields = [field for field in required_fields if field not in task_request]
        
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {missing_fields}"
            )
        
        # Extract task information
        agent_url = task_request["agent_url"]
        task_type = task_request["task_type"]
        context = task_request["context"]
        correlation_id = task_request.get("correlation_id")
        priority = task_request.get("priority", "normal")
        
        # Determine client type based on URL
        use_http = agent_url.startswith("http://") or agent_url.startswith("https://")
        client = get_http_client() if use_http else get_memory_client()
        
        # Create A2A task
        if use_http:
            task = await client.create_task(
                agent_url=agent_url,
                task_type=task_type,
                context=context,
                correlation_id=correlation_id
            )
        else:
            task = await client.create_task(
                agent_url=agent_url,
                task_type=task_type,
                context=context,
                correlation_id=correlation_id
            )
        
        # Create database record
        db_task = Task(
            id=task.task_id,
            session_id=context.get("session_id", str(uuid.uuid4())),
            agent_id=_extract_agent_id_from_url(agent_url),
            task_type=task_type,
            priority=priority,
            input_data=context,
            status="pending"
        )
        
        db.add(db_task)
        await db.commit()
        await db.refresh(db_task)
        
        logger.info(f"Created A2A task {task.task_id} for agent {agent_url}")
        
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "agent_url": agent_url,
            "task_type": task_type,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create A2A task: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_a2a_task_status(
    task_id: str,
    agent_url: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get A2A task status and details"""
    try:
        # Get from database first
        result = await db.execute(select(Task).where(Task.id == task_id))
        db_task = result.scalar_one_or_none()
        
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # If agent URL provided, query the agent directly
        if agent_url:
            use_http = agent_url.startswith("http://") or agent_url.startswith("https://")
            client = get_http_client() if use_http else get_memory_client()
            
            try:
                a2a_task = await client.get_task_status(agent_url, task_id)
                
                # Update database with latest info
                db_task.status = a2a_task.status.value
                if a2a_task.result:
                    db_task.output_data = a2a_task.result
                if a2a_task.error:
                    db_task.error_message = a2a_task.error
                
                await db.commit()
                
                return {
                    "task_id": task_id,
                    "status": a2a_task.status.value,
                    "result": a2a_task.result,
                    "error": a2a_task.error,
                    "created_at": a2a_task.created_at.isoformat() if a2a_task.created_at else None,
                    "started_at": a2a_task.started_at.isoformat() if a2a_task.started_at else None,
                    "completed_at": a2a_task.completed_at.isoformat() if a2a_task.completed_at else None
                }
                
            except Exception as e:
                logger.warning(f"Failed to query agent directly: {e}")
                # Fall back to database record
        
        # Return database record
        return {
            "task_id": task_id,
            "status": db_task.status,
            "result": db_task.output_data,
            "error": db_task.error_message,
            "created_at": db_task.created_at.isoformat(),
            "started_at": db_task.started_at.isoformat() if db_task.started_at else None,
            "completed_at": db_task.completed_at.isoformat() if db_task.completed_at else None,
            "quality_score": db_task.quality_score,
            "confidence_score": db_task.confidence_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task status")


@router.put("/tasks/{task_id}")
async def update_a2a_task(
    task_id: str,
    task_update: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update A2A task status and results"""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        db_task = result.scalar_one_or_none()
        
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update fields
        if "status" in task_update:
            db_task.status = task_update["status"]
            
            if task_update["status"] == "processing" and not db_task.started_at:
                db_task.started_at = datetime.now(timezone.utc)
            elif task_update["status"] in ["completed", "failed"] and not db_task.completed_at:
                db_task.completed_at = datetime.now(timezone.utc)
        
        if "result" in task_update:
            db_task.output_data = task_update["result"]
        
        if "error" in task_update:
            db_task.error_message = task_update["error"]
        
        if "quality_score" in task_update:
            db_task.quality_score = task_update["quality_score"]
        
        if "confidence_score" in task_update:
            db_task.confidence_score = task_update["confidence_score"]
        
        # Calculate processing time if completed
        if db_task.status in ["completed", "failed"] and db_task.started_at:
            processing_time = (datetime.now(timezone.utc) - db_task.started_at).total_seconds()
            db_task.processing_time = processing_time
        
        await db.commit()
        await db.refresh(db_task)
        
        logger.info(f"Updated A2A task {task_id} status to {db_task.status}")
        
        return {
            "task_id": task_id,
            "status": db_task.status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update task")


@router.post("/tasks/{task_id}/cancel")
async def cancel_a2a_task(
    task_id: str,
    agent_url: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Cancel an A2A task"""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        db_task = result.scalar_one_or_none()
        
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if db_task.status in ["completed", "failed", "cancelled"]:
            return {"message": f"Task is already {db_task.status}"}
        
        # Try to cancel at agent level if URL provided
        if agent_url:
            # This would require implementing cancellation in the A2A clients
            # For now, just update database
            pass
        
        # Update database
        db_task.status = "cancelled"
        db_task.completed_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"Cancelled A2A task {task_id}")
        return {"message": "Task cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.post("/tasks/{task_id}/retry")
async def retry_a2a_task(
    task_id: str,
    agent_url: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed A2A task"""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        db_task = result.scalar_one_or_none()
        
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if db_task.status not in ["failed", "cancelled"]:
            raise HTTPException(status_code=400, detail="Only failed or cancelled tasks can be retried")
        
        # Reset task status
        db_task.status = "pending"
        db_task.error_message = None
        db_task.started_at = None
        db_task.completed_at = None
        db_task.processing_time = None
        
        await db.commit()
        
        # Re-create the A2A task
        use_http = agent_url.startswith("http://") or agent_url.startswith("https://")
        client = get_http_client() if use_http else get_memory_client()
        
        background_tasks.add_task(
            _retry_task_execution,
            client,
            agent_url,
            task_id,
            db_task.task_type,
            db_task.input_data or {}
        )
        
        logger.info(f"Retrying A2A task {task_id}")
        return {"message": "Task retry initiated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry task {task_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to retry task")


@router.get("/agents/{agent_id}/tasks")
async def list_agent_tasks(
    agent_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List tasks for a specific agent"""
    try:
        query = select(Task).where(Task.agent_id == agent_id)
        
        if status:
            query = query.where(Task.status == status)
        
        query = query.order_by(desc(Task.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        return [
            {
                "task_id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "session_id": task.session_id,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "processing_time": task.processing_time,
                "quality_score": task.quality_score
            }
            for task in tasks
        ]
        
    except Exception as e:
        logger.error(f"Failed to list tasks for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks")


@router.get("/tasks")
async def list_all_tasks(
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all A2A tasks with filtering"""
    try:
        query = select(Task)
        
        conditions = []
        if status:
            conditions.append(Task.status == status)
        if agent_id:
            conditions.append(Task.agent_id == agent_id)
        if session_id:
            conditions.append(Task.session_id == session_id)
        
        if conditions:
            query = query.where(*conditions)
        
        query = query.order_by(desc(Task.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        return [
            {
                "task_id": task.id,
                "agent_id": task.agent_id,
                "task_type": task.task_type,
                "status": task.status,
                "session_id": task.session_id,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "processing_time": task.processing_time,
                "quality_score": task.quality_score,
                "confidence_score": task.confidence_score
            }
            for task in tasks
        ]
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks")


# Utility functions
def _extract_agent_id_from_url(agent_url: str) -> str:
    """Extract agent ID from agent URL"""
    if agent_url.startswith("local://"):
        return agent_url.replace("local://", "")
    elif "localhost" in agent_url:
        # Map ports to agent IDs
        port_mapping = {
            "8001": "architect",
            "8002": "stack-recommender", 
            "8003": "documenter"
        }
        for port, agent_id in port_mapping.items():
            if f":{port}" in agent_url:
                return agent_id
    
    # Fallback: use last part of URL
    return agent_url.split("/")[-1].rstrip("/")


async def _retry_task_execution(
    client: Any,
    agent_url: str,
    task_id: str,
    task_type: str,
    context: Dict[str, Any]
):
    """Background task execution retry"""
    from app.db.session import AsyncSessionLocal
    
    try:
        # Re-create A2A task
        task = await client.create_task(
            agent_url=agent_url,
            task_type=task_type,
            context=context,
            correlation_id=task_id
        )
        
        # Wait for completion (with timeout)
        if hasattr(client, 'create_task_with_wait'):
            completed_task = await client.create_task_with_wait(
                agent_url=agent_url,
                task_type=task_type,
                context=context,
                correlation_id=task_id,
                max_wait_time=300.0
            )
            
            # Update database
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Task).where(Task.id == task_id))
                db_task = result.scalar_one_or_none()
                
                if db_task:
                    db_task.status = completed_task.status.value
                    db_task.output_data = completed_task.result
                    if completed_task.error:
                        db_task.error_message = completed_task.error
                    db_task.completed_at = datetime.now(timezone.utc)
                    
                    await db.commit()
        
        logger.info(f"Task retry completed for {task_id}")
        
    except Exception as e:
        logger.error(f"Task retry failed for {task_id}: {e}")
        
        # Update database with failure
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Task).where(Task.id == task_id))
                db_task = result.scalar_one_or_none()
                
                if db_task:
                    db_task.status = "failed"
                    db_task.error_message = f"Retry failed: {str(e)}"
                    db_task.completed_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update retry failure status: {db_error}")