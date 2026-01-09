"""
Unit Tests: Session Service
===========================

Tests for the SessionService class covering:
1. CRUD operations (create, read, update, delete)
2. Session listing and pagination
3. Session statistics
4. Expired session cleanup
5. Error handling
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.services.session_service import SessionService, get_session_service
from app.schemas.session import (
    SessionCreate, SessionUpdate, SessionResponse,
    SessionStatus, TaskSummary
)
from app.models.models import Session as DBSession, Task, Artifact


class TestSessionService:
    """Test suite for SessionService"""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def session_service(self, mock_db_session):
        """Create SessionService instance with mock db"""
        return SessionService(mock_db_session)

    @pytest.fixture
    def sample_db_session(self):
        """Create sample database session model"""
        return DBSession(
            id=str(uuid.uuid4()),
            title="Test Session",
            description="Test description",
            requirements_text="Test requirements",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    # ===================
    # Create Session Tests
    # ===================

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service, mock_db_session):
        """Test successful session creation"""
        # Arrange
        create_data = SessionCreate(
            title="New Session",
            description="A new test session",
            requirements_text="Build a REST API"
        )

        # Mock refresh to set the session attributes
        async def mock_refresh(obj):
            obj.id = str(uuid.uuid4())
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db_session.refresh = mock_refresh

        # Act
        result = await session_service.create_session(create_data)

        # Assert
        assert result is not None
        assert result.title == "New Session"
        assert result.description == "A new test session"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_with_user_id(self, session_service, mock_db_session):
        """Test session creation with user ID"""
        create_data = SessionCreate(
            title="User Session",
            requirements_text="User requirements"
        )

        async def mock_refresh(obj):
            obj.id = str(uuid.uuid4())
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db_session.refresh = mock_refresh

        result = await session_service.create_session(create_data, user_id="user-123")

        assert result is not None
        assert result.title == "User Session"

    @pytest.mark.asyncio
    async def test_create_session_db_error(self, session_service, mock_db_session):
        """Test session creation handles database errors"""
        create_data = SessionCreate(
            title="Error Session",
            requirements_text="Will fail"
        )

        mock_db_session.commit = AsyncMock(side_effect=Exception("Database error"))

        with pytest.raises(Exception) as exc_info:
            await session_service.create_session(create_data)

        assert "Database error" in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()

    # ===================
    # Get Session Tests
    # ===================

    @pytest.mark.asyncio
    async def test_get_session_found(self, session_service, mock_db_session, sample_db_session):
        """Test retrieving existing session"""
        # Mock execute to return the sample session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_db_session
        mock_db_session.execute.return_value = mock_result

        result = await session_service.get_session(sample_db_session.id)

        assert result is not None
        assert result.id == sample_db_session.id
        assert result.title == "Test Session"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_service, mock_db_session):
        """Test retrieving non-existent session"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await session_service.get_session("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_with_tasks(self, session_service, mock_db_session, sample_db_session):
        """Test retrieving session with related tasks"""
        # Add mock tasks
        sample_db_session.tasks = [
            Mock(
                id="task-1",
                task_type="analysis",
                agent_id="analyzer",
                status="completed",
                priority="high",
                created_at=datetime.now(timezone.utc),
                quality_score=0.95
            )
        ]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_db_session
        mock_db_session.execute.return_value = mock_result

        result = await session_service.get_session(
            sample_db_session.id,
            include_tasks=True
        )

        assert result is not None
        assert result.tasks is not None
        assert len(result.tasks) == 1

    # ===================
    # Update Session Tests
    # ===================

    @pytest.mark.asyncio
    async def test_update_session_success(self, session_service, mock_db_session, sample_db_session):
        """Test successful session update"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_db_session
        mock_db_session.execute.return_value = mock_result

        update_data = SessionUpdate(
            title="Updated Title",
            status=SessionStatus.COMPLETED
        )

        result = await session_service.update_session(sample_db_session.id, update_data)

        assert result is not None
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_session_not_found(self, session_service, mock_db_session):
        """Test updating non-existent session"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        update_data = SessionUpdate(title="New Title")

        result = await session_service.update_session("non-existent", update_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_session_partial(self, session_service, mock_db_session, sample_db_session):
        """Test partial session update (only some fields)"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_db_session
        mock_db_session.execute.return_value = mock_result

        # Only update description
        update_data = SessionUpdate(description="New description only")

        result = await session_service.update_session(sample_db_session.id, update_data)

        assert result is not None

    # ===================
    # Delete Session Tests
    # ===================

    @pytest.mark.asyncio
    async def test_delete_session_success(self, session_service, mock_db_session, sample_db_session):
        """Test successful session deletion"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_db_session
        mock_db_session.execute.return_value = mock_result

        result = await session_service.delete_session(sample_db_session.id)

        assert result is True
        mock_db_session.delete.assert_called_once_with(sample_db_session)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, session_service, mock_db_session):
        """Test deleting non-existent session"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await session_service.delete_session("non-existent")

        assert result is False

    # ===================
    # List Sessions Tests
    # ===================

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, session_service, mock_db_session):
        """Test listing sessions when none exist"""
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        result = await session_service.list_sessions()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_sessions_with_filter(self, session_service, mock_db_session, sample_db_session):
        """Test listing sessions with status filter"""
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_db_session]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        result = await session_service.list_sessions(status=SessionStatus.ACTIVE)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_sessions_pagination(self, session_service, mock_db_session):
        """Test listing sessions with pagination"""
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        result = await session_service.list_sessions(limit=10, offset=20)

        assert result == []
        # Verify execute was called (pagination is applied in query)
        mock_db_session.execute.assert_called_once()

    # ===================
    # Session Statistics Tests
    # ===================

    @pytest.mark.asyncio
    async def test_get_session_statistics(self, session_service, mock_db_session, sample_db_session):
        """Test getting session statistics"""
        # Add mock tasks with various statuses
        sample_db_session.tasks = [
            Mock(status="completed", quality_score=0.9, processing_time=10.5),
            Mock(status="completed", quality_score=0.8, processing_time=15.0),
            Mock(status="pending", quality_score=None, processing_time=None),
            Mock(status="failed", quality_score=None, processing_time=5.0),
        ]
        sample_db_session.artifacts = [Mock(), Mock()]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_db_session
        mock_db_session.execute.return_value = mock_result

        stats = await session_service.get_session_statistics(sample_db_session.id)

        assert stats["tasks"]["total"] == 4
        assert stats["tasks"]["completed"] == 2
        assert stats["tasks"]["pending"] == 1
        assert stats["tasks"]["failed"] == 1
        assert stats["artifacts_count"] == 2
        assert stats["average_quality_score"] == 0.85
        assert stats["completion_percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_get_session_statistics_not_found(self, session_service, mock_db_session):
        """Test getting statistics for non-existent session"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        stats = await session_service.get_session_statistics("non-existent")

        assert stats == {}

    # ===================
    # Cleanup Tests
    # ===================

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_service, mock_db_session):
        """Test cleanup of expired sessions"""
        # Mock finding expired sessions
        mock_result = Mock()
        mock_result.fetchall.return_value = [("session-1",), ("session-2",)]
        mock_db_session.execute.return_value = mock_result

        count = await session_service.cleanup_expired_sessions(max_age_days=30)

        assert count == 2
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_no_expired_sessions(self, session_service, mock_db_session):
        """Test cleanup when no sessions are expired"""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_result

        count = await session_service.cleanup_expired_sessions(max_age_days=30)

        assert count == 0

    # ===================
    # Status Update Tests
    # ===================

    @pytest.mark.asyncio
    async def test_update_session_status_success(self, session_service, mock_db_session):
        """Test updating session status"""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result

        result = await session_service.update_session_status(
            "session-123",
            SessionStatus.COMPLETED
        )

        assert result is True
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_session_status_not_found(self, session_service, mock_db_session):
        """Test updating status of non-existent session"""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db_session.execute.return_value = mock_result

        result = await session_service.update_session_status(
            "non-existent",
            SessionStatus.COMPLETED
        )

        assert result is False

    # ===================
    # Factory Function Tests
    # ===================

    @pytest.mark.asyncio
    async def test_get_session_service_factory(self, mock_db_session):
        """Test factory function creates service correctly"""
        service = await get_session_service(mock_db_session)

        assert isinstance(service, SessionService)
        assert service.db == mock_db_session


class TestSessionServiceIntegration:
    """Integration-style tests for SessionService (still using mocks but testing workflows)"""

    @pytest.fixture
    def mock_db_session(self):
        """Create comprehensive mock database session"""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, mock_db_session):
        """Test complete session lifecycle: create -> update -> complete -> delete"""
        service = SessionService(mock_db_session)

        # 1. Create session
        async def mock_refresh_create(obj):
            obj.id = "lifecycle-session-123"
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db_session.refresh = mock_refresh_create

        create_data = SessionCreate(
            title="Lifecycle Test",
            requirements_text="Test the full lifecycle"
        )
        created = await service.create_session(create_data)
        assert created.title == "Lifecycle Test"

        # 2. Update session
        sample_session = DBSession(
            id="lifecycle-session-123",
            title="Lifecycle Test",
            description=None,
            requirements_text="Test the full lifecycle",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_session
        mock_db_session.execute.return_value = mock_result

        update_data = SessionUpdate(description="Added description")
        updated = await service.update_session("lifecycle-session-123", update_data)
        assert updated is not None

        # 3. Update status to completed
        mock_result.rowcount = 1
        status_updated = await service.update_session_status(
            "lifecycle-session-123",
            SessionStatus.COMPLETED
        )
        assert status_updated is True

        # 4. Delete session
        mock_result.scalar_one_or_none.return_value = sample_session
        deleted = await service.delete_session("lifecycle-session-123")
        assert deleted is True
