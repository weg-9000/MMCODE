"""
Session management API endpoints
CRUD operations for user sessions and requirement analysis workflows
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone
from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient
from app.db.session import get_db
from app.models.models import Session, Task, Artifact
from app.schemas.session import (
    SessionCreate, SessionUpdate, SessionResponse, SessionStatus,
    RequirementAnalysisRequest, AnalysisResponse, OrchestrationRequest, OrchestrationResponse
)
from app.security.authentication import get_current_user, User, log_security_event, require_permission

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(require_permission("sessions:write")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new session with timeout protection"""
    try:
        import asyncio
        # Add timeout protection for session creation
        async with asyncio.timeout(10):  # 10 second timeout
            # Create new session with user context
            new_session = Session(
                title=session_data.title,
                description=session_data.description,
                requirements_text=session_data.requirements_text,
                user_id=current_user.id  # Add user context for RLS
            )
            
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            
            # Log security event
            await log_security_event(
                db=db, user=current_user, event_type="session_created",
                target=f"session:{new_session.id}", result="success"
            )
            
            logger.info(f"Created session {new_session.id}: {new_session.title}")
            return new_session
        
    except asyncio.TimeoutError:
        await db.rollback()
        logger.error("Session creation timed out")
        raise HTTPException(status_code=408, detail="Session creation timed out")
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Analyze requirements for a session using RequirementAnalyzer agent"""
    try:
        # Verify session exists
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session with requirements if provided
        if analysis_request.requirements:
            session.requirements_text = analysis_request.requirements
            session.status = "processing"
            await db.commit()
        
        # Create task record
        task = Task(
            session_id=session_id,
            agent_id="requirement-analyzer",
            task_type="requirement_analysis",
            input_data={
                "requirements": analysis_request.requirements or session.requirements_text,
                "preferences": analysis_request.preferences or {}
            },
            status="pending"
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # Schedule background analysis using RequirementAnalyzer
        background_tasks.add_task(
            _execute_requirement_analysis,
            session_id,
            task.id,
            analysis_request.requirements or session.requirements_text or "",
            analysis_request.preferences or {}
        )
        
        logger.info(f"Started requirement analysis task {task.id} for session {session_id}")
        
        return AnalysisResponse(
            session_id=session_id,
            task_id=task.id,
            status="processing",
            message="Requirement analysis started successfully"
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start full agent orchestration workflow with timeout protection"""
    try:
        import asyncio
        # Add timeout protection for session creation
        async with asyncio.timeout(5):  # 5 second timeout for session creation only
            # Create new session for orchestration
            session = Session(
                title=orchestration_request.session_title or "AI Strategy Session",
                description="Full agent orchestration workflow",
                requirements_text=orchestration_request.requirements,
                status="started"  # Changed from "processing" to "started"
            )
            
            db.add(session)
            await db.commit()
            await db.refresh(session)
        
        # Schedule background workflow - this should not block the response
        background_tasks.add_task(
            _execute_full_orchestration_safe,  # Use safe version
            session.id,
            orchestration_request.requirements,
            orchestration_request.preferences or {}
        )
        
        logger.info(f"Started full orchestration workflow for session {session.id}")
        
        # Return immediately without waiting for background task
        return OrchestrationResponse(
            session_id=session.id,
            status="STARTED",  # Use consistent status naming
            message="Orchestration workflow initiated successfully",
            estimated_completion_minutes=15,
            tasks=[],
            artifacts=[]
        )
        
    except asyncio.TimeoutError:
        await db.rollback()
        logger.error("Orchestration session creation timed out")
        raise HTTPException(status_code=408, detail="Session creation timed out")
    except Exception as e:
        logger.error(f"Failed to start orchestration: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to start orchestration")


# Background execution functions
async def _execute_requirement_analysis(
    session_id: str,
    task_id: str,
    requirements: str,
    preferences: Dict[str, Any]
):
    """Background task for requirement analysis execution"""
    from app.db.session import AsyncSessionLocal
    from app.agents.requirement_analyzer.core.agent import RequirementAnalyzer
    from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient
    
    try:
        # Initialize analyzer
        a2a_client = InMemoryA2AClient()
        analyzer = RequirementAnalyzer(a2a_client=a2a_client)
        
        # Execute analysis
        result = await analyzer.analyze_requirements(requirements)
        
        # Update database
        async with AsyncSessionLocal() as db:
            # Update task
            task_result = await db.execute(select(Task).where(Task.id == task_id))
            task = task_result.scalar_one_or_none()
            
            if task:
                task.status = "completed"
                task.completed_at = datetime.now(timezone.utc)
                task.output_data = result
                
                # Calculate processing time
                if task.started_at:
                    processing_time = (datetime.now(timezone.utc) - task.started_at).total_seconds()
                    task.processing_time = processing_time
                
                # Create artifact for analysis result
                artifact = Artifact(
                    session_id=session_id,
                    task_id=task_id,
                    artifact_type="requirement_analysis",
                    title="Requirement Analysis Report",
                    content=result,
                    created_by="requirement-analyzer",
                    is_final=True
                )
                
                db.add(artifact)
                await db.commit()
                
                logger.info(f"Requirement analysis completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Requirement analysis failed for session {session_id}: {e}")
        
        # Update task status to failed
        try:
            async with AsyncSessionLocal() as db:
                task_result = await db.execute(select(Task).where(Task.id == task_id))
                task = task_result.scalar_one_or_none()
                
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.completed_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update task status: {db_error}")


async def _execute_full_orchestration_safe(
    session_id: str,
    requirements: str,
    preferences: Dict[str, Any]
):
    """Background task for full orchestration workflow execution with timeout protection"""
    from app.db.session import AsyncSessionLocal
    from app.core.dependencies import get_agent_registry
    
    try:
        import asyncio
        
        # Set overall timeout for orchestration
        async with asyncio.timeout(300):  # 5 minute timeout for full orchestration
            async with AsyncSessionLocal() as db:
                # Update session status to processing
                session_result = await db.execute(select(Session).where(Session.id == session_id))
                session = session_result.scalar_one_or_none()
                
                if not session:
                    logger.error(f"Session {session_id} not found")
                    return
                
                session.status = "IN_PROGRESS"
                await db.commit()
            
            # Get agent registry with timeout protection
            try:
                registry = get_agent_registry()
                requirement_analyzer = registry.requirement_analyzer
                
                if not requirement_analyzer:
                    raise RuntimeError("Requirement analyzer not available")
                
                # Execute orchestration with smaller timeout
                async with asyncio.timeout(240):  # 4 minute timeout for actual work
                    orchestration_result = await requirement_analyzer.analyze_and_orchestrate(
                        requirements=requirements,
                        session_id=session_id
                    )
                
                # Save results with timeout
                async with asyncio.timeout(30):  # 30 second timeout for saving
                    async with AsyncSessionLocal() as db:
                        await _save_orchestration_results_safe(db, session_id, orchestration_result)
                        
                        # Update session status
                        session_result = await db.execute(select(Session).where(Session.id == session_id))
                        session = session_result.scalar_one_or_none()
                        if session:
                            session.status = "COMPLETED"
                            await db.commit()
                
                logger.info(f"Full orchestration completed for session {session_id}")
                
            except Exception as agent_error:
                logger.error(f"Agent orchestration error for session {session_id}: {agent_error}")
                await _update_session_status_safe(session_id, "FAILED", str(agent_error))
                
    except asyncio.TimeoutError:
        logger.error(f"Full orchestration timed out for session {session_id}")
        await _update_session_status_safe(session_id, "FAILED", "Orchestration timed out")
    except Exception as e:
        logger.error(f"Full orchestration failed for session {session_id}: {e}")
        await _update_session_status_safe(session_id, "FAILED", str(e))


async def _update_session_status_safe(session_id: str, status: str, error_message: str = None):
    """Safely update session status with timeout protection"""
    try:
        import asyncio
        from app.db.session import AsyncSessionLocal
        
        async with asyncio.timeout(5):  # 5 second timeout
            async with AsyncSessionLocal() as db:
                session_result = await db.execute(select(Session).where(Session.id == session_id))
                session = session_result.scalar_one_or_none()
                
                if session:
                    session.status = status
                    if error_message and hasattr(session, 'error_message'):
                        session.error_message = error_message
                    await db.commit()
    except Exception as db_error:
        logger.error(f"Failed to update session status: {db_error}")


# Keep original function for backward compatibility
async def _execute_full_orchestration(
    session_id: str,
    requirements: str,
    preferences: Dict[str, Any]
):
    """Legacy function - redirects to safe version"""
    await _execute_full_orchestration_safe(session_id, requirements, preferences)


async def _register_test_agents(client: InMemoryA2AClient):
    """Register test agents for orchestration"""
    try:
        # Import agent classes
        from app.agents.architect_agent.core.agent import ArchitectAgent
        from app.agents.stack_recommender.core.agent import StackRecommenderAgent
        from app.agents.document_agent.core.agent import DocumentAgent
        
        # Create and register agent instances
        architect = ArchitectAgent()
        stack_recommender = StackRecommenderAgent() 
        documenter = DocumentAgent()
        
        client.register("architect", architect)
        client.register("stack_recommender", stack_recommender)
        client.register("documenter", documenter)
        
        logger.info("Test agents registered successfully")
        
    except Exception as e:
        logger.warning(f"Failed to register some agents: {e}")


async def _save_orchestration_results_safe(
    db: AsyncSession,
    session_id: str,
    results: Dict[str, Any]
):
    """Save orchestration results as artifacts with timeout protection"""
    try:
        import asyncio
        artifacts_created = 0
        
        # Save different types of results as separate artifacts with individual timeouts
        artifact_types = [
            ("analysis", "requirement_analysis", "Requirements Analysis", "requirement-analyzer"),
            ("architecture", "architecture_design", "System Architecture Design", "architect"),
            ("stack", "stack_recommendation", "Technology Stack Recommendation", "stack-recommender"),
            ("documentation", "documentation", "Project Documentation", "documenter")
        ]
        
        for result_key, artifact_type, title, created_by in artifact_types:
            if result_key in results:
                try:
                    # Create artifact with timeout protection
                    async with asyncio.timeout(5):  # 5 second timeout per artifact
                        artifact = Artifact(
                            session_id=session_id,
                            artifact_type=artifact_type,
                            title=title,
                            content=results[result_key],
                            created_by=created_by,
                            is_final=True
                        )
                        db.add(artifact)
                        artifacts_created += 1
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout saving artifact {result_key} for session {session_id}")
                except Exception as artifact_error:
                    logger.error(f"Failed to save artifact {result_key}: {artifact_error}")
        
        await db.commit()
        logger.info(f"Saved {artifacts_created} artifacts for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to save orchestration results: {e}")
        try:
            await db.rollback()
        except:
            pass  # Ignore rollback errors


# Keep original function for backward compatibility
async def _save_orchestration_results(
    db: AsyncSession,
    session_id: str,
    results: Dict[str, Any]
):
    """Legacy function - redirects to safe version"""
    await _save_orchestration_results_safe(db, session_id, results)