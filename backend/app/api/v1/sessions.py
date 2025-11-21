"""
Session management API endpoints
CRUD operations for user sessions and requirement analysis workflows
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
import logging

from app.db.session import get_db
from app.models.models import Session, Task, Artifact
from app.schemas.session import (
    SessionCreate, SessionUpdate, SessionResponse, SessionStatus,
    RequirementAnalysisRequest, AnalysisResponse, OrchestrationRequest, OrchestrationResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new session"""
    try:
        # Create new session
        new_session = Session(
            title=session_data.title,
            description=session_data.description,
            requirements_text=session_data.requirements_text
        )
        
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        logger.info(f"Created session {new_session.id}: {new_session.title}")
        return new_session
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    status: Optional[SessionStatus] = None,
    limit: int = Query(default=50, le=100),
    skip: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List sessions with optional filtering"""
    try:
        # Build query
        query = select(Session)
        
        if status:
            query = query.where(Session.status == status.value)
        
        query = query.order_by(desc(Session.created_at)).offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        return sessions
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    include_tasks: bool = Query(default=False),
    include_artifacts: bool = Query(default=False),
    db: AsyncSession = Depends(get_db)
):
    """Get session by ID with optional related data"""
    try:
        # Get session
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Convert to response model
        session_data = SessionResponse.model_validate(session)
        
        # Include tasks if requested
        if include_tasks:
            task_result = await db.execute(
                select(Task).where(Task.session_id == session_id)
            )
            session_data.tasks = [
                {
                    "id": task.id,
                    "task_type": task.task_type,
                    "agent_id": task.agent_id,
                    "status": task.status,
                    "priority": task.priority,
                    "created_at": task.created_at,
                    "quality_score": task.quality_score
                }
                for task in task_result.scalars().all()
            ]
        
        # Include artifacts if requested
        if include_artifacts:
            artifact_result = await db.execute(
                select(Artifact).where(Artifact.session_id == session_id)
            )
            session_data.artifacts = [
                {
                    "id": artifact.id,
                    "artifact_type": artifact.artifact_type,
                    "title": artifact.title,
                    "quality_score": artifact.quality_score,
                    "created_at": artifact.created_at,
                    "is_final": artifact.is_final
                }
                for artifact in artifact_result.scalars().all()
            ]
        
        return session_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    session_update: SessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update session"""
    try:
        # Get existing session
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update fields
        update_data = session_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(session, field, value)
        
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"Updated session {session_id}")
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update session")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete session and all related data"""
    try:
        # Get session
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete session (cascades to tasks and artifacts)
        await db.delete(session)
        await db.commit()
        
        logger.info(f"Deleted session {session_id}")
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.post("/{session_id}/analyze", response_model=AnalysisResponse)
async def analyze_requirements(
    session_id: str,
    analysis_request: RequirementAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """Analyze requirements for a session"""
    try:
        # Verify session exists
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # TODO: Integrate with RequirementAnalyzer agent
        # For now, return a placeholder response
        
        # Create task record
        task = Task(
            session_id=session_id,
            agent_id="requirement-analyzer",
            task_type="requirement_analysis",
            input_data={"requirements": analysis_request.requirements},
            status="pending"
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Created analysis task {task.id} for session {session_id}")
        
        return AnalysisResponse(
            session_id=session_id,
            task_id=task.id,
            status="pending"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze requirements for session {session_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to start analysis")


@router.post("/orchestrate", response_model=OrchestrationResponse)
async def orchestrate_full_workflow(
    orchestration_request: OrchestrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start full agent orchestration workflow"""
    try:
        # Create new session for orchestration
        session = Session(
            title=orchestration_request.session_title or "AI Strategy Session",
            description="Full agent orchestration workflow",
            requirements_text=orchestration_request.requirements
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # TODO: Integrate with RequirementAnalyzer orchestration
        # For now, return a placeholder response
        
        logger.info(f"Started orchestration for session {session.id}")
        
        return OrchestrationResponse(
            session_id=session.id,
            status="started",
            tasks=[],
            artifacts=[]
        )
        
    except Exception as e:
        logger.error(f"Failed to start orchestration: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to start orchestration")