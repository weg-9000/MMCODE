"""
Agent Management API Endpoints
Comprehensive agent registration, status monitoring, and capability management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import List, Optional, Dict, Any
import logging
import uuid
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.models import Agent, Task, Session as DBSession
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse, AgentStatus,
    AgentCapability, AgentCard, TaskRequest, TaskResponse
)
from app.agents.shared.models.a2a_models import A2ATask, TaskStatus as A2ATaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# Agent registry for in-memory access
_agent_registry: Dict[str, Any] = {}


@router.post("/register", response_model=AgentResponse)
async def register_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new agent in the system"""
    try:
        # Check if agent already exists
        result = await db.execute(select(Agent).where(Agent.id == agent_data.id))
        existing_agent = result.scalar_one_or_none()
        
        if existing_agent:
            # Update existing agent
            for field, value in agent_data.model_dump(exclude_unset=True).items():
                setattr(existing_agent, field, value)
            existing_agent.last_seen = datetime.now(timezone.utc)
            existing_agent.status = agent_data.status.value
            
            await db.commit()
            await db.refresh(existing_agent)
            
            logger.info(f"Updated agent registration: {agent_data.id}")
            return existing_agent
        
        # Create new agent
        new_agent = Agent(
            id=agent_data.id,
            name=agent_data.name,
            role=agent_data.id.replace("-", "_"),  # Convert to role format
            description=agent_data.description,
            endpoint_url=agent_data.endpoint_url,
            capabilities=agent_data.capabilities,
            status=agent_data.status.value,
            version=agent_data.version,
            last_seen=datetime.now(timezone.utc)
        )
        
        db.add(new_agent)
        await db.commit()
        await db.refresh(new_agent)
        
        logger.info(f"Registered new agent: {agent_data.id}")
        return new_agent
        
    except Exception as e:
        logger.error(f"Failed to register agent {agent_data.id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Agent registration failed: {str(e)}")


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    status: Optional[AgentStatus] = None,
    capability: Optional[AgentCapability] = None,
    limit: int = Query(default=50, le=100),
    skip: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List all registered agents with optional filtering"""
    try:
        query = select(Agent)
        
        # Apply filters
        conditions = []
        if status:
            conditions.append(Agent.status == status.value)
        if capability:
            conditions.append(Agent.capabilities.contains([capability.value]))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(Agent.last_seen)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        agents = result.scalars().all()
        
        return agents
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agents")


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    include_tasks: bool = Query(default=False),
    db: AsyncSession = Depends(get_db)
):
    """Get agent details by ID with optional task history"""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent_data = AgentResponse.model_validate(agent)
        
        if include_tasks:
            # Get recent tasks for this agent
            task_result = await db.execute(
                select(Task)
                .where(Task.agent_id == agent_id)
                .order_by(desc(Task.created_at))
                .limit(10)
            )
            agent_data.recent_tasks = [
                {
                    "id": task.id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "session_id": task.session_id,
                    "created_at": task.created_at,
                    "quality_score": task.quality_score
                }
                for task in task_result.scalars().all()
            ]
        
        return agent_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent")


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update agent information"""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Update fields
        update_data = agent_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status" and hasattr(value, 'value'):
                value = value.value
            setattr(agent, field, value)
        
        agent.last_seen = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(agent)
        
        logger.info(f"Updated agent {agent_id}")
        return agent
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update agent")


@router.delete("/{agent_id}")
async def deregister_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Deregister agent from the system"""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Set status to inactive instead of deleting
        agent.status = AgentStatus.INACTIVE.value
        agent.last_seen = datetime.now(timezone.utc)
        
        await db.commit()
        
        # Remove from in-memory registry
        if agent_id in _agent_registry:
            del _agent_registry[agent_id]
        
        logger.info(f"Deregistered agent {agent_id}")
        return {"message": f"Agent {agent_id} deregistered successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deregister agent {agent_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to deregister agent")


@router.get("/{agent_id}/capabilities")
async def get_agent_capabilities(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed agent capabilities and schemas"""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get agent instance for detailed capabilities
        agent_instance = _agent_registry.get(agent_id)
        
        capabilities_detail = {
            "agent_id": agent_id,
            "capabilities": agent.capabilities or [],
            "status": agent.status,
            "version": agent.version,
            "endpoint_url": agent.endpoint_url
        }
        
        # If agent instance is available, get more details
        if agent_instance and hasattr(agent_instance, 'get_capabilities'):
            try:
                detailed_caps = await agent_instance.get_capabilities()
                capabilities_detail.update(detailed_caps)
            except Exception as e:
                logger.warning(f"Failed to get detailed capabilities from {agent_id}: {e}")
        
        return capabilities_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get capabilities for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve capabilities")


@router.post("/{agent_id}/health")
async def check_agent_health(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Perform health check on agent"""
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        health_status = {
            "agent_id": agent_id,
            "status": agent.status,
            "last_seen": agent.last_seen,
            "healthy": agent.status == AgentStatus.ACTIVE.value
        }
        
        # Try to ping agent instance
        agent_instance = _agent_registry.get(agent_id)
        if agent_instance and hasattr(agent_instance, 'health_check'):
            try:
                health_detail = await agent_instance.health_check()
                health_status.update(health_detail)
            except Exception as e:
                health_status["healthy"] = False
                health_status["error"] = str(e)
        
        # Update last_seen
        agent.last_seen = datetime.now(timezone.utc)
        await db.commit()
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.post("/{agent_id}/tasks", response_model=TaskResponse)
async def create_agent_task(
    agent_id: str,
    task_request: TaskRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new task for the specified agent"""
    try:
        # Verify agent exists and is active
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if agent.status != AgentStatus.ACTIVE.value:
            raise HTTPException(status_code=400, detail="Agent is not active")
        
        # Create task record
        task_id = str(uuid.uuid4())
        new_task = Task(
            id=task_id,
            session_id=task_request.session_id,
            agent_id=agent_id,
            task_type=task_request.task_type,
            priority=task_request.priority.value if task_request.priority else "medium",
            input_data=task_request.context,
            status="pending"
        )
        
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        
        # Schedule background task execution
        background_tasks.add_task(_execute_agent_task, agent_id, task_id, task_request.context)
        
        logger.info(f"Created task {task_id} for agent {agent_id}")
        
        return TaskResponse(
            task_id=task_id,
            agent_id=agent_id,
            status=A2ATaskStatus.PENDING,
            created_at=new_task.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task for agent {agent_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create task")


# Utility functions
def register_agent_instance(agent_id: str, agent_instance: Any):
    """Register agent instance for in-memory access"""
    _agent_registry[agent_id] = agent_instance
    logger.info(f"Agent instance registered: {agent_id}")


async def _execute_agent_task(agent_id: str, task_id: str, context: Dict[str, Any]):
    """Background task execution"""
    from app.db.session import AsyncSessionLocal
    
    try:
        agent_instance = _agent_registry.get(agent_id)
        if not agent_instance:
            logger.error(f"Agent instance not found: {agent_id}")
            return
        
        # Execute task
        if hasattr(agent_instance, 'handle_task'):
            # Create A2A task object
            a2a_task = A2ATask(
                task_id=task_id,
                task_type=context.get('task_type', 'default'),
                context=context,
                status=A2ATaskStatus.PENDING
            )
            
            # Execute
            result = await agent_instance.handle_task(a2a_task)
            
            # Update database
            async with AsyncSessionLocal() as db:
                db_result = await db.execute(select(Task).where(Task.id == task_id))
                task = db_result.scalar_one_or_none()
                
                if task:
                    task.status = "completed"
                    task.completed_at = datetime.now(timezone.utc)
                    task.output_data = getattr(result, 'content', result) if hasattr(result, 'content') else result
                    
                    await db.commit()
                    logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task execution failed for {task_id}: {e}")
        # Update task status to failed
        try:
            async with AsyncSessionLocal() as db:
                db_result = await db.execute(select(Task).where(Task.id == task_id))
                task = db_result.scalar_one_or_none()
                
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.completed_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update task status: {db_error}")