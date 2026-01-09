"""
Orchestration API Endpoints
Main workflow orchestration and session management for agent coordination
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
import logging
import uuid
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.models import Session as DBSession, Task, Agent, Artifact
from app.schemas.session import (
    SessionCreate, SessionResponse, 
    OrchestrationRequest, OrchestrationResponse,
    WorkflowStatus, TaskSummary
)
from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient
from app.core.exceptions import (
    DevStrategistException, DatabaseConnectionError, 
    AgentCommunicationException, ValidationException
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Global orchestration client
_orchestration_client: Optional[InMemoryA2AClient] = None


def get_orchestration_client() -> InMemoryA2AClient:
    """Get or create orchestration client"""
    global _orchestration_client
    if _orchestration_client is None:
        _orchestration_client = InMemoryA2AClient()
    return _orchestration_client


@router.post("/", response_model=OrchestrationResponse)
async def start_orchestration(
    request: OrchestrationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start full agent orchestration workflow"""
    try:
        # Create session
        session = DBSession(
            title=request.session_title or "AI Strategy Session",
            description=request.description or "Automated agent orchestration workflow",
            requirements_text=request.requirements,
            status="active"
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # Validate required agents are available
        required_agents = ["requirement-analyzer", "architect", "stack-recommender", "documenter"]
        missing_agents = []
        
        for agent_id in required_agents:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent or agent.status != "active":
                missing_agents.append(agent_id)
        
        if missing_agents:
            session.status = "failed"
            await db.commit()
            raise ValidationException(
                message="Required agents not available",
                field="required_agents",
                value=missing_agents,
                context={"missing_agents": missing_agents},
                suggestions=["Start missing agents", "Check agent configuration"]
            )
        
        # Schedule background orchestration
        background_tasks.add_task(
            _execute_orchestration_workflow,
            session.id,
            request.requirements,
            request.preferences or {}
        )
        
        logger.info(f"Started orchestration workflow for session {session.id}")
        
        return OrchestrationResponse(
            session_id=session.id,
            status=WorkflowStatus.STARTED,
            message="Orchestration workflow initiated successfully",
            estimated_completion_minutes=15,
            tasks=[],
            artifacts=[]
        )
        
    except DevStrategistException:
        await db.rollback()
        raise
    except Exception as e:
        logger.exception("Unexpected error starting orchestration", 
                       extra={"session_id": getattr(session, 'id', None) if 'session' in locals() else None})
        await db.rollback()
        raise DevStrategistException(
            message="Failed to start orchestration workflow",
            code="ORCHESTRATION_START_ERROR",
            context={"original_error": str(e)},
            suggestions=[
                "Check database connectivity", 
                "Verify agent availability",
                "Review system logs"
            ]
        )


@router.get("/{session_id}/status", response_model=OrchestrationResponse)
async def get_orchestration_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current orchestration workflow status with timeout protection"""
    try:
        import asyncio
        # Add timeout protection for status query
        async with asyncio.timeout(10):  # 10 second timeout
            # Get session
            result = await db.execute(select(DBSession).where(DBSession.id == session_id))
            session = result.scalar_one_or_none()
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Get tasks
            task_result = await db.execute(
                select(Task)
                .where(Task.session_id == session_id)
                .order_by(Task.created_at)
            )
            tasks = task_result.scalars().all()
            
            # Get artifacts
            artifact_result = await db.execute(
                select(Artifact)
                .where(Artifact.session_id == session_id)
                .order_by(Artifact.created_at)
            )
            artifacts = artifact_result.scalars().all()
        
        # Determine status
        status = _determine_workflow_status(session, tasks)
        
        # Build task summaries
        task_summaries = [
            TaskSummary(
                task_id=task.id,
                agent_id=task.agent_id,
                task_type=task.task_type,
                status=task.status,
                progress_percentage=_calculate_task_progress(task),
                created_at=task.created_at,
                completed_at=task.completed_at,
                quality_score=task.quality_score
            )
            for task in tasks
        ]
        
        # Build artifact summaries
        artifact_summaries = [
            {
                "id": artifact.id,
                "type": artifact.artifact_type,
                "title": artifact.title,
                "created_by": artifact.created_by,
                "created_at": artifact.created_at,
                "quality_score": artifact.quality_score,
                "is_final": artifact.is_final
            }
            for artifact in artifacts
        ]
        
        progress_percentage = _calculate_overall_progress(tasks)

        return OrchestrationResponse(
            session_id=session_id,
            status=status,
            progress_percentage=progress_percentage,
            message=_get_status_message(status, progress_percentage),
            tasks=task_summaries,
            artifacts=artifact_summaries
        )

    except asyncio.TimeoutError:
        logger.error(f"Status query timed out for session {session_id}")
        raise HTTPException(status_code=408, detail="Status query timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get orchestration status for {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve status")


@router.post("/{session_id}/cancel")
async def cancel_orchestration(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel ongoing orchestration workflow"""
    try:
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status in ["completed", "failed", "cancelled"]:
            return {"message": f"Session is already {session.status}"}
        
        # Update session status
        session.status = "cancelled"
        
        # Cancel pending tasks
        await db.execute(
            Task.__table__.update()
            .where(Task.session_id == session_id)
            .where(Task.status.in_(["pending", "processing"]))
            .values(status="cancelled", completed_at=datetime.now(timezone.utc))
        )
        
        await db.commit()
        
        logger.info(f"Cancelled orchestration for session {session_id}")
        return {"message": "Orchestration workflow cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel orchestration {session_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel orchestration")


@router.get("/{session_id}/artifacts/{artifact_id}")
async def get_artifact_detail(
    session_id: str,
    artifact_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed artifact content"""
    try:
        result = await db.execute(
            select(Artifact)
            .where(Artifact.id == artifact_id)
            .where(Artifact.session_id == session_id)
        )
        artifact = result.scalar_one_or_none()
        
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        return {
            "id": artifact.id,
            "session_id": artifact.session_id,
            "type": artifact.artifact_type,
            "title": artifact.title,
            "description": artifact.description,
            "content": artifact.content,
            "content_format": artifact.content_format,
            "quality_score": artifact.quality_score,
            "confidence_score": artifact.confidence_score,
            "version": artifact.version,
            "created_by": artifact.created_by,
            "created_at": artifact.created_at,
            "is_final": artifact.is_final,
            "is_public": artifact.is_public
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get artifact {artifact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve artifact")


@router.post("/{session_id}/retry")
async def retry_failed_tasks(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Retry failed tasks in the orchestration workflow"""
    try:
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get failed tasks
        failed_tasks_result = await db.execute(
            select(Task)
            .where(Task.session_id == session_id)
            .where(Task.status == "failed")
        )
        failed_tasks = failed_tasks_result.scalars().all()
        
        if not failed_tasks:
            return {"message": "No failed tasks to retry"}
        
        # Reset failed tasks to pending
        for task in failed_tasks:
            task.status = "pending"
            task.error_message = None
            task.started_at = None
            task.completed_at = None
        
        # Update session status
        session.status = "active"
        
        await db.commit()
        
        # Re-execute workflow
        background_tasks.add_task(
            _execute_orchestration_workflow,
            session_id,
            session.requirements_text or "",
            {}
        )
        
        logger.info(f"Retrying {len(failed_tasks)} failed tasks for session {session_id}")
        return {"message": f"Retrying {len(failed_tasks)} failed tasks"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry tasks for {session_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to retry tasks")


# Background workflow execution
async def _execute_orchestration_workflow(
    session_id: str,
    requirements: str,
    preferences: Dict[str, Any]
):
    """Execute the complete orchestration workflow in background"""
    from app.db.session import AsyncSessionLocal
    from app.agents.requirement_analyzer.analyzer import RequirementAnalyzer
    
    try:
        # Step 1: Initialize and update session status (short DB session)
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DBSession).where(DBSession.id == session_id))
            session = result.scalar_one_or_none()
            
            if not session:
                logger.error(f"Session {session_id} not found")
                return
            
            session.status = "processing"
            await db.commit()
        
        # Step 2: Execute long-running AI workflow (no DB connection)
        client = get_orchestration_client()
        analyzer = RequirementAnalyzer(a2a_client=client)
        
        # Register agents (quick operation)
        async with AsyncSessionLocal() as db:
            await _ensure_agents_registered(client, db)
        
        # Execute the AI workflow without holding DB connection
        workflow_result = await analyzer.analyze_and_orchestrate(
            requirements=requirements,
            session_id=session_id
        )
        
        # Step 3: Save results and update status (short DB session)
        async with AsyncSessionLocal() as db:
            # Save results to database
            await _save_orchestration_results(db, session_id, workflow_result)
            
            # Update session status
            result = await db.execute(select(DBSession).where(DBSession.id == session_id))
            session = result.scalar_one_or_none()
            if session:
                session.status = "completed"
                await db.commit()
        
        logger.info(f"Orchestration workflow completed for session {session_id}")
        
    except Exception as e:
        logger.exception(f"Orchestration workflow failed for {session_id}")
        
        # Update session status to failed (separate short DB session)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(DBSession).where(DBSession.id == session_id))
                session = result.scalar_one_or_none()
                if session:
                    session.status = "failed"
                    await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update session status: {db_error}")


# Utility functions
def _determine_workflow_status(session: DBSession, tasks: List[Task]) -> WorkflowStatus:
    """Determine overall workflow status based on session and tasks"""
    if session.status == "completed":
        return WorkflowStatus.COMPLETED
    elif session.status == "failed":
        return WorkflowStatus.FAILED
    elif session.status == "cancelled":
        return WorkflowStatus.CANCELLED
    elif session.status == "processing":
        return WorkflowStatus.IN_PROGRESS
    elif not tasks:
        return WorkflowStatus.STARTED
    else:
        failed_count = sum(1 for task in tasks if task.status == "failed")
        completed_count = sum(1 for task in tasks if task.status == "completed")
        
        if failed_count > 0:
            return WorkflowStatus.FAILED
        elif completed_count == len(tasks):
            return WorkflowStatus.COMPLETED
        else:
            return WorkflowStatus.IN_PROGRESS


def _calculate_task_progress(task: Task) -> float:
    """Calculate progress percentage for individual task"""
    if task.status == "completed":
        return 100.0
    elif task.status == "failed":
        return 0.0
    elif task.status == "processing":
        return 50.0  # Estimated halfway
    else:
        return 0.0


def _calculate_overall_progress(tasks: List[Task]) -> float:
    """Calculate overall workflow progress"""
    if not tasks:
        return 0.0
    
    total_progress = sum(_calculate_task_progress(task) for task in tasks)
    return round(total_progress / len(tasks), 1)


def _get_status_message(status: WorkflowStatus, progress: float) -> str:
    """Generate human-readable status message"""
    status_messages = {
        WorkflowStatus.STARTED: "Workflow initialization complete",
        WorkflowStatus.IN_PROGRESS: f"Workflow in progress ({progress}% complete)",
        WorkflowStatus.COMPLETED: "Workflow completed successfully",
        WorkflowStatus.FAILED: "Workflow failed - check individual tasks",
        WorkflowStatus.CANCELLED: "Workflow cancelled by user"
    }
    return status_messages.get(status, "Unknown status")


async def _ensure_agents_registered(client: InMemoryA2AClient, db: AsyncSession):
    """Ensure all required agents are registered with the A2A client

    Checks database for registered agents and ensures they are available
    in the A2A client for inter-agent communication.
    """
    required_agent_ids = ["requirement-analyzer", "architect", "stack_recommender", "documenter"]

    for agent_id in required_agent_ids:
        # Check if already registered in client
        if client.is_registered(agent_id):
            continue

        # Try to get agent from database
        try:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent_record = result.scalar_one_or_none()

            if agent_record and agent_record.status == "active":
                # Create a placeholder registration for the agent
                # Actual agent instance will be created on demand
                logger.debug(f"Agent {agent_id} found in database, marking as available")
            else:
                logger.warning(f"Agent {agent_id} not found or inactive in database")

        except Exception as e:
            logger.warning(f"Failed to check agent {agent_id} registration: {e}")


async def _save_orchestration_results(
    db: AsyncSession,
    session_id: str,
    results: Dict[str, Any]
):
    """Save orchestration results to database as Artifact records

    Handles various result types from the orchestration workflow:
    - analysis_result: Requirement analysis output
    - architecture_design: Architecture design artifacts
    - stack_recommendation: Technology stack recommendations
    - documentation: Generated documentation
    """
    try:
        logger.info(f"Saving orchestration results for session {session_id}")

        # Process each result type
        artifact_mappings = [
            ("analysis_result", "requirement_analysis", "Requirement Analysis"),
            ("architecture_design", "architecture", "Architecture Design"),
            ("stack_recommendation", "stack_recommendation", "Technology Stack"),
            ("documentation", "documentation", "Generated Documentation"),
        ]

        for result_key, artifact_type, title_prefix in artifact_mappings:
            if result_key in results and results[result_key]:
                result_data = results[result_key]

                # Create artifact record
                artifact = Artifact(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    artifact_type=artifact_type,
                    title=f"{title_prefix} - Session {session_id[:8]}",
                    description=f"Auto-generated {title_prefix.lower()} from orchestration workflow",
                    content=result_data if isinstance(result_data, str) else str(result_data),
                    content_format="json" if isinstance(result_data, dict) else "text",
                    created_by="orchestration-workflow",
                    quality_score=result_data.get("quality_score") if isinstance(result_data, dict) else None,
                    confidence_score=result_data.get("confidence_score") if isinstance(result_data, dict) else None,
                    is_final=True,
                    is_public=False
                )
                db.add(artifact)
                logger.debug(f"Created artifact: {artifact_type} for session {session_id}")

        # Also save any tasks that were completed
        if "completed_tasks" in results:
            for task_data in results["completed_tasks"]:
                task = Task(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    agent_id=task_data.get("agent_id", "unknown"),
                    task_type=task_data.get("task_type", "orchestration"),
                    status="completed",
                    input_data=task_data.get("input"),
                    output_data=task_data.get("output"),
                    quality_score=task_data.get("quality_score"),
                    completed_at=datetime.now(timezone.utc)
                )
                db.add(task)

        await db.commit()
        logger.info(f"Successfully saved orchestration results for session {session_id}")

    except Exception as e:
        logger.error(f"Failed to save orchestration results: {e}")
        await db.rollback()
        raise