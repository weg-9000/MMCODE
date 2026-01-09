"""
Unit Tests: Resilient A2A Client
================================

Tests for the resilient A2A client including:
1. Timeout handling
2. Retry logic with exponential backoff
3. Circuit breaker pattern
4. Task cancellation
5. Resource limits
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
import uuid

from app.agents.shared.a2a_client.resilient_client import (
    ResilientA2AClient,
    ResilientClientConfig,
    RetryConfig,
    TimeoutConfig,
    CircuitBreakerConfig,
    ResourceLimits,
    CircuitBreaker,
    CircuitState,
    TaskTimeoutError,
    CircuitOpenError,
    MaxRetriesExceededError,
    create_resilient_client,
)
from app.agents.shared.models.a2a_models import A2ATask, TaskStatus


class TestRetryConfig:
    """Tests for RetryConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test custom configuration values"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=120.0,
            jitter=False
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
        assert config.jitter is False


class TestTimeoutConfig:
    """Tests for TimeoutConfig"""

    def test_default_values(self):
        """Test default timeout values"""
        config = TimeoutConfig()
        assert config.default_timeout == 30.0
        assert config.connect_timeout == 10.0
        assert config.read_timeout == 60.0
        assert config.task_timeout == 300.0


class TestCircuitBreaker:
    """Tests for CircuitBreaker"""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker with test config"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short for testing
            success_threshold=2
        )
        return CircuitBreaker(config)

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, circuit_breaker):
        """Test circuit breaker starts in closed state"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert await circuit_breaker.can_execute() is True

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self, circuit_breaker):
        """Test circuit opens after reaching failure threshold"""
        # Record failures up to threshold
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN
        assert await circuit_breaker.can_execute() is False

    @pytest.mark.asyncio
    async def test_transitions_to_half_open(self, circuit_breaker):
        """Test circuit transitions to half-open after recovery timeout"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Should transition to half-open
        assert await circuit_breaker.can_execute() is True
        assert circuit_breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_after_success_in_half_open(self, circuit_breaker):
        """Test circuit closes after successes in half-open state"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure()

        # Wait for recovery
        await asyncio.sleep(1.1)
        await circuit_breaker.can_execute()

        # Record successes
        await circuit_breaker.record_success()
        await circuit_breaker.record_success()

        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self, circuit_breaker):
        """Test circuit reopens on failure in half-open state"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure()

        # Wait for recovery
        await asyncio.sleep(1.1)
        await circuit_breaker.can_execute()

        # Fail in half-open
        await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN


class TestResilientA2AClient:
    """Tests for ResilientA2AClient"""

    @pytest.fixture
    def mock_base_client(self):
        """Create mock base client"""
        client = Mock()
        client.create_task = AsyncMock()
        client.get_task_status = AsyncMock()
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def resilient_client(self, mock_base_client):
        """Create resilient client with mock base"""
        config = ResilientClientConfig(
            retry=RetryConfig(max_attempts=3, initial_delay=0.1, jitter=False),
            timeout=TimeoutConfig(default_timeout=5.0, task_timeout=10.0),
            circuit_breaker=CircuitBreakerConfig(failure_threshold=3),
            resource_limits=ResourceLimits(max_concurrent_tasks=5)
        )
        return ResilientA2AClient(mock_base_client, config)

    @pytest.mark.asyncio
    async def test_create_task_success(self, resilient_client, mock_base_client):
        """Test successful task creation"""
        expected_task = A2ATask(
            task_id=str(uuid.uuid4()),
            task_type="test_task",
            status=TaskStatus.PENDING,
            context={"key": "value"}
        )
        mock_base_client.create_task.return_value = expected_task

        task = await resilient_client.create_task(
            agent_url="http://test-agent:8000",
            task_type="test_task",
            context={"key": "value"}
        )

        assert task.task_id == expected_task.task_id
        assert task.task_type == "test_task"
        mock_base_client.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_timeout(self, resilient_client, mock_base_client):
        """Test task creation timeout - should raise MaxRetriesExceededError after retries"""
        async def slow_create(*args, **kwargs):
            await asyncio.sleep(10)
            return A2ATask(task_id="test", task_type="test", status=TaskStatus.PENDING)

        mock_base_client.create_task = slow_create

        # Timeout errors trigger retries, so we get MaxRetriesExceededError
        with pytest.raises(MaxRetriesExceededError):
            await resilient_client.create_task(
                agent_url="http://test-agent:8000",
                task_type="test_task",
                context={},
                timeout=0.1
            )

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, resilient_client, mock_base_client):
        """Test retry on connection errors"""
        call_count = 0

        async def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return A2ATask(
                task_id="test",
                task_type="test_task",
                status=TaskStatus.PENDING
            )

        mock_base_client.create_task = failing_then_success

        task = await resilient_client.create_task(
            agent_url="http://test-agent:8000",
            task_type="test_task",
            context={}
        )

        assert task is not None
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, resilient_client, mock_base_client):
        """Test max retries exceeded error"""
        mock_base_client.create_task = AsyncMock(
            side_effect=ConnectionError("Always fails")
        )

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            await resilient_client.create_task(
                agent_url="http://test-agent:8000",
                task_type="test_task",
                context={}
            )

        assert exc_info.value.attempts == 3
        assert "Always fails" in str(exc_info.value.last_error)

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, resilient_client, mock_base_client):
        """Test circuit breaker opens after failures"""
        mock_base_client.create_task = AsyncMock(
            side_effect=ConnectionError("Connection failed")
        )

        # Trigger multiple failures to open circuit
        for _ in range(3):
            try:
                await resilient_client.create_task(
                    agent_url="http://test-agent:8000",
                    task_type="test_task",
                    context={}
                )
            except (MaxRetriesExceededError, CircuitOpenError):
                pass

        # Circuit should be open now
        with pytest.raises(CircuitOpenError):
            await resilient_client.create_task(
                agent_url="http://test-agent:8000",
                task_type="test_task",
                context={}
            )

    @pytest.mark.asyncio
    async def test_task_cancellation(self, resilient_client, mock_base_client):
        """Test task cancellation"""
        task_id = str(uuid.uuid4())

        # Start a long-running task
        async def long_task(*args, **kwargs):
            await asyncio.sleep(100)
            return A2ATask(task_id=task_id, task_type="test", status=TaskStatus.COMPLETED)

        mock_base_client.create_task = long_task

        # Start task in background
        task_future = asyncio.create_task(
            resilient_client.create_task(
                agent_url="http://test-agent:8000",
                task_type="test_task",
                context={}
            )
        )

        # Give it time to start
        await asyncio.sleep(0.1)

        # Cancel (note: this tests the internal task tracking)
        await resilient_client.cancel_all_tasks()

        # The future should be cancelled
        task_future.cancel()
        try:
            await task_future
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_resource_usage(self, resilient_client):
        """Test resource usage reporting"""
        usage = resilient_client.get_resource_usage()

        assert "active_tasks" in usage
        assert "max_concurrent_tasks" in usage
        assert "available_slots" in usage
        assert usage["max_concurrent_tasks"] == 5

    @pytest.mark.asyncio
    async def test_circuit_breaker_status(self, resilient_client, mock_base_client):
        """Test circuit breaker status reporting"""
        # Make a successful call to register the circuit breaker
        mock_base_client.create_task.return_value = A2ATask(
            task_id="test",
            task_type="test",
            status=TaskStatus.PENDING
        )

        await resilient_client.create_task(
            agent_url="http://test-agent:8000",
            task_type="test_task",
            context={}
        )

        status = resilient_client.get_circuit_breaker_status("http://test-agent:8000")

        assert status["state"] == "closed"
        assert status["failure_count"] == 0


class TestCreateResilientClient:
    """Tests for factory function"""

    def test_create_with_defaults(self):
        """Test factory with default values"""
        mock_client = Mock()
        resilient_client = create_resilient_client(mock_client)

        assert resilient_client is not None
        assert resilient_client.config.retry.max_attempts == 3
        assert resilient_client.config.timeout.default_timeout == 30.0

    def test_create_with_custom_values(self):
        """Test factory with custom values"""
        mock_client = Mock()
        resilient_client = create_resilient_client(
            mock_client,
            max_retries=5,
            default_timeout=60.0,
            task_timeout=600.0,
            max_concurrent_tasks=20,
            circuit_breaker_threshold=10
        )

        assert resilient_client.config.retry.max_attempts == 5
        assert resilient_client.config.timeout.default_timeout == 60.0
        assert resilient_client.config.timeout.task_timeout == 600.0
        assert resilient_client.config.resource_limits.max_concurrent_tasks == 20
        assert resilient_client.config.circuit_breaker.failure_threshold == 10


class TestIntegrationWithMockClient:
    """Integration tests with InMemoryA2AClient"""

    @pytest.mark.asyncio
    async def test_resilient_mock_client_integration(self):
        """Test resilient client wrapping mock client"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        # Create mock client and register a test agent
        mock_client = InMemoryA2AClient()

        test_agent = Mock()
        test_agent.handle_task = AsyncMock(return_value={"result": "success"})
        mock_client.register("test-agent", test_agent)

        # Wrap with resilient client
        resilient_client = create_resilient_client(
            mock_client,
            max_retries=2,
            default_timeout=5.0
        )

        # Create task
        task = await resilient_client.create_task(
            agent_url="local://test-agent",
            task_type="test_task",
            context={"input": "test"}
        )

        assert task is not None
        assert task.task_type == "test_task"

        # Wait a bit for async execution
        await asyncio.sleep(0.2)

        # Check task status
        status = await resilient_client.get_task_status(
            "local://test-agent",
            task.task_id
        )

        assert status.status in [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS]

    @pytest.mark.asyncio
    async def test_resilient_client_with_wait(self):
        """Test resilient client create_task_with_wait"""
        from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient

        mock_client = InMemoryA2AClient()

        test_agent = Mock()
        test_agent.handle_task = AsyncMock(return_value={"result": "completed"})
        mock_client.register("test-agent", test_agent)

        resilient_client = create_resilient_client(
            mock_client,
            task_timeout=5.0
        )

        # Create task and wait for completion
        task = await resilient_client.create_task_with_wait(
            agent_url="local://test-agent",
            task_type="test_task",
            context={"input": "test"},
            max_wait_time=5.0,
            poll_interval=0.1
        )

        assert task.status == TaskStatus.COMPLETED


class TestExceptionTypes:
    """Tests for custom exception types"""

    def test_task_timeout_error(self):
        """Test TaskTimeoutError"""
        error = TaskTimeoutError("task-123", 30.0)
        assert error.task_id == "task-123"
        assert error.timeout == 30.0
        assert "task-123" in str(error)
        assert "30" in str(error)

    def test_task_timeout_error_custom_message(self):
        """Test TaskTimeoutError with custom message"""
        error = TaskTimeoutError("task-123", 30.0, "Custom timeout message")
        assert error.message == "Custom timeout message"

    def test_circuit_open_error(self):
        """Test CircuitOpenError"""
        error = CircuitOpenError("http://test:8000")
        assert error.agent_url == "http://test:8000"
        assert "http://test:8000" in str(error)

    def test_max_retries_exceeded_error(self):
        """Test MaxRetriesExceededError"""
        original_error = ConnectionError("Connection refused")
        error = MaxRetriesExceededError("create_task", 3, original_error)
        assert error.operation == "create_task"
        assert error.attempts == 3
        assert error.last_error == original_error
        assert "3" in str(error)
        assert "create_task" in str(error)
