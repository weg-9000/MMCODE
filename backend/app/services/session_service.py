"""
Session Service Module

Handles session lifecycle management for MMCODE workflow sessions.
Provides CRUD operations, state management, and session utilities.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

from sqlalchemy import select, delete, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Session as DBSession, Task, Artifact
from app.schemas.session import (
    SessionCreate, SessionUpdate, SessionResponse,
    SessionStatus, TaskSummary, ArtifactSummary
)

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service class for managing workflow sessions.

    Provides complete CRUD operations and session lifecycle management
    with support for related entities (tasks, artifacts).
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize SessionService with database session.

        Args:
            db: SQLAlchemy async database session
        """
        self.db = db

    async def create_session(
        self,
        data: SessionCreate,
        user_id: Optional[str] = None
    ) -> SessionResponse:
        """
        Create a new workflow session.

        Args:
            data: Session creation data
            user_id: Optional user ID for session ownership

        Returns:
            Created session response

        Raises:
            Exception: If database operation fails
        """
        try:
            session = DBSession(
                id=str(uuid.uuid4()),
                title=data.title,
                description=data.description,
                requirements_text=data.requirements_text,
                status="active"
            )

            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

            logger.info(f"Created session {session.id}: {session.title}")

            return self._to_response(session)

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            await self.db.rollback()
            raise

    async def get_session(
        self,
        session_id: str,
        include_tasks: bool = False,
        include_artifacts: bool = False
    ) -> Optional[SessionResponse]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session UUID
            include_tasks: Whether to include related tasks
            include_artifacts: Whether to include related artifacts

        Returns:
            Session response or None if not found
        """
        try:
            query = select(DBSession).where(DBSession.id == session_id)

            # Optionally load relationships
            if include_tasks:
                query = query.options(selectinload(DBSession.tasks))
            if include_artifacts:
                query = query.options(selectinload(DBSession.artifacts))

            result = await self.db.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                logger.debug(f"Session not found: {session_id}")
                return None

            return self._to_response(
                session,
                include_tasks=include_tasks,
                include_artifacts=include_artifacts
            )

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise

    async def update_session(
        self,
        session_id: str,
        data: SessionUpdate
    ) -> Optional[SessionResponse]:
        """
        Update session data.

        Args:
            session_id: Session UUID
            data: Update data (partial update supported)

        Returns:
            Updated session response or None if not found
        """
        try:
            # Get existing session
            result = await self.db.execute(
                select(DBSession).where(DBSession.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                logger.debug(f"Session not found for update: {session_id}")
                return None

            # Apply updates (only non-None fields)
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if value is not None:
                    setattr(session, field, value.value if hasattr(value, 'value') else value)

            # Update timestamp
            session.updated_at = datetime.now(timezone.utc)

            await self.db.commit()
            await self.db.refresh(session)

            logger.info(f"Updated session {session_id}")

            return self._to_response(session)

        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all related entities.

        Args:
            session_id: Session UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            # Check if session exists
            result = await self.db.execute(
                select(DBSession).where(DBSession.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                logger.debug(f"Session not found for deletion: {session_id}")
                return False

            # Delete session (cascade will handle tasks and artifacts)
            await self.db.delete(session)
            await self.db.commit()

            logger.info(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SessionResponse]:
        """
        List sessions with optional filtering.

        Args:
            user_id: Filter by user ID (if implemented)
            status: Filter by session status
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of session responses
        """
        try:
            query = select(DBSession).order_by(DBSession.created_at.desc())

            # Apply filters
            if status:
                query = query.where(DBSession.status == status.value)

            # Apply pagination
            query = query.limit(limit).offset(offset)

            result = await self.db.execute(query)
            sessions = result.scalars().all()

            return [self._to_response(s) for s in sessions]

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise

    async def get_session_count(
        self,
        status: Optional[SessionStatus] = None
    ) -> int:
        """
        Get total count of sessions.

        Args:
            status: Optional status filter

        Returns:
            Count of sessions
        """
        try:
            query = select(func.count(DBSession.id))

            if status:
                query = query.where(DBSession.status == status.value)

            result = await self.db.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Failed to count sessions: {e}")
            raise

    async def cleanup_expired_sessions(
        self,
        max_age_days: int = 30,
        statuses: Optional[List[str]] = None
    ) -> int:
        """
        Remove expired or stale sessions.

        Args:
            max_age_days: Maximum age in days for sessions
            statuses: Only cleanup sessions with these statuses

        Returns:
            Count of deleted sessions
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)

            # Build query conditions
            conditions = [DBSession.updated_at < cutoff_date]

            if statuses:
                conditions.append(DBSession.status.in_(statuses))
            else:
                # Default: only cleanup completed or archived
                conditions.append(DBSession.status.in_(["completed", "archived"]))

            # Get sessions to delete (for logging)
            select_query = select(DBSession.id).where(and_(*conditions))
            result = await self.db.execute(select_query)
            session_ids = [row[0] for row in result.fetchall()]

            if not session_ids:
                logger.info("No expired sessions to cleanup")
                return 0

            # Delete sessions (cascade will handle related entities)
            delete_query = delete(DBSession).where(DBSession.id.in_(session_ids))
            await self.db.execute(delete_query)
            await self.db.commit()

            logger.info(f"Cleaned up {len(session_ids)} expired sessions")
            return len(session_ids)

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            await self.db.rollback()
            raise

    async def update_session_status(
        self,
        session_id: str,
        status: SessionStatus
    ) -> bool:
        """
        Update only the session status.

        Args:
            session_id: Session UUID
            status: New status

        Returns:
            True if updated, False if not found
        """
        try:
            result = await self.db.execute(
                update(DBSession)
                .where(DBSession.id == session_id)
                .values(
                    status=status.value,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            if result.rowcount == 0:
                return False

            await self.db.commit()
            logger.info(f"Updated session {session_id} status to {status.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update session status: {e}")
            await self.db.rollback()
            raise

    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session.

        Args:
            session_id: Session UUID

        Returns:
            Dictionary with session statistics
        """
        try:
            # Get session with relationships
            result = await self.db.execute(
                select(DBSession)
                .where(DBSession.id == session_id)
                .options(
                    selectinload(DBSession.tasks),
                    selectinload(DBSession.artifacts)
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                return {}

            tasks = session.tasks or []
            artifacts = session.artifacts or []

            # Calculate statistics
            task_stats = {
                "total": len(tasks),
                "pending": sum(1 for t in tasks if t.status == "pending"),
                "processing": sum(1 for t in tasks if t.status == "processing"),
                "completed": sum(1 for t in tasks if t.status == "completed"),
                "failed": sum(1 for t in tasks if t.status == "failed"),
            }

            # Calculate average quality score
            quality_scores = [t.quality_score for t in tasks if t.quality_score is not None]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

            # Calculate total processing time
            processing_times = [t.processing_time for t in tasks if t.processing_time is not None]
            total_processing_time = sum(processing_times) if processing_times else 0

            return {
                "session_id": session_id,
                "status": session.status,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "tasks": task_stats,
                "artifacts_count": len(artifacts),
                "average_quality_score": round(avg_quality, 2) if avg_quality else None,
                "total_processing_time_seconds": round(total_processing_time, 2),
                "completion_percentage": round(
                    (task_stats["completed"] / task_stats["total"] * 100)
                    if task_stats["total"] > 0 else 0, 1
                )
            }

        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            raise

    def _to_response(
        self,
        session: DBSession,
        include_tasks: bool = False,
        include_artifacts: bool = False
    ) -> SessionResponse:
        """
        Convert database model to response schema.

        Args:
            session: Database session model
            include_tasks: Include task summaries
            include_artifacts: Include artifact summaries

        Returns:
            SessionResponse schema
        """
        tasks = None
        artifacts = None

        if include_tasks and session.tasks:
            tasks = [
                TaskSummary(
                    id=t.id,
                    task_type=t.task_type,
                    agent_id=t.agent_id,
                    status=t.status,
                    priority=t.priority,
                    created_at=t.created_at,
                    quality_score=t.quality_score
                )
                for t in session.tasks
            ]

        if include_artifacts and session.artifacts:
            artifacts = [
                ArtifactSummary(
                    id=a.id,
                    artifact_type=a.artifact_type,
                    title=a.title,
                    quality_score=a.quality_score,
                    created_at=a.created_at,
                    is_final=a.is_final
                )
                for a in session.artifacts
            ]

        return SessionResponse(
            id=session.id,
            title=session.title,
            description=session.description,
            requirements_text=session.requirements_text,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            tasks=tasks,
            artifacts=artifacts
        )


# Factory function for dependency injection
async def get_session_service(db: AsyncSession) -> SessionService:
    """
    Factory function to create SessionService instance.

    Usage with FastAPI:
        @router.get("/sessions/{session_id}")
        async def get_session(
            session_id: str,
            service: SessionService = Depends(get_session_service)
        ):
            return await service.get_session(session_id)
    """
    return SessionService(db)
