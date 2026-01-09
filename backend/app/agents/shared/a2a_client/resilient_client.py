"""
Resilient A2A Client with Timeout, Retry, and Circuit Breaker Support

This module provides enhanced A2A client capabilities with:
- Configurable timeout handling
- Exponential backoff retry logic
- Circuit breaker pattern for fault tolerance
- Task cancellation support
- Resource limit configuration
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from functools import wraps

from ..models.a2a_models import A2ATask, TaskStatus


# Type variable for generic return types
T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0     # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
    )


@dataclass
class TimeoutConfig:
    """Configuration for timeout behavior"""
    default_timeout: float = 30.0       # seconds
    connect_timeout: float = 10.0       # seconds
    read_timeout: float = 60.0          # seconds
    task_timeout: float = 300.0         # seconds for task completion


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # failures before opening
    recovery_timeout: float = 60.0      # seconds before half-open
    success_threshold: int = 2          # successes to close from half-open


@dataclass
class ResourceLimits:
    """Resource limits for task execution"""
    max_concurrent_tasks: int = 10
    max_memory_mb: int = 512
    max_execution_time: float = 300.0   # seconds
    max_retries_per_task: int = 3


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Check if request can be executed based on circuit state"""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self.last_failure_time:
                    elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                    if elapsed >= self.config.recovery_timeout:
                        self.state = CircuitState.HALF_OPEN
                        self.success_count = 0
                        self.logger.info("Circuit breaker transitioning to HALF_OPEN")
                        return True
                return False

            # HALF_OPEN state
            return True

    async def record_success(self):
        """Record a successful operation"""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.logger.info("Circuit breaker CLOSED after successful recovery")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    async def record_failure(self):
        """Record a failed operation"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.logger.warning("Circuit breaker OPEN after failure in HALF_OPEN")
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.logger.warning(
                        f"Circuit breaker OPEN after {self.failure_count} failures"
                    )


class TaskTimeoutError(Exception):
    """Exception raised when a task times out"""
    def __init__(self, task_id: str, timeout: float, message: str = None):
        self.task_id = task_id
        self.timeout = timeout
        self.message = message or f"Task {task_id} timed out after {timeout} seconds"
        super().__init__(self.message)


class CircuitOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    def __init__(self, agent_url: str):
        self.agent_url = agent_url
        super().__init__(f"Circuit breaker is open for {agent_url}")


class MaxRetriesExceededError(Exception):
    """Exception raised when max retries are exceeded"""
    def __init__(self, operation: str, attempts: int, last_error: Exception):
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Max retries ({attempts}) exceeded for {operation}: {last_error}"
        )


@dataclass
class ResilientClientConfig:
    """Combined configuration for resilient client"""
    retry: RetryConfig = field(default_factory=RetryConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)


class ResilientA2AClientMixin:
    """
    Mixin providing resilience features for A2A clients.

    Features:
    - Timeout handling with configurable limits
    - Exponential backoff retry with jitter
    - Circuit breaker pattern
    - Task cancellation
    - Resource limits
    """

    def __init__(self, config: Optional[ResilientClientConfig] = None):
        self.config = config or ResilientClientConfig()
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_semaphore = asyncio.Semaphore(
            self.config.resource_limits.max_concurrent_tasks
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_circuit_breaker(self, agent_url: str) -> CircuitBreaker:
        """Get or create circuit breaker for agent"""
        if agent_url not in self._circuit_breakers:
            self._circuit_breakers[agent_url] = CircuitBreaker(
                self.config.circuit_breaker
            )
        return self._circuit_breakers[agent_url]

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter"""
        delay = min(
            self.config.retry.initial_delay * (
                self.config.retry.exponential_base ** attempt
            ),
            self.config.retry.max_delay
        )

        if self.config.retry.jitter:
            delay = delay * (0.5 + random.random())

        return delay

    async def _execute_with_timeout(
        self,
        coro: Any,
        timeout: float,
        operation_name: str = "operation"
    ) -> Any:
        """Execute coroutine with timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.error(f"{operation_name} timed out after {timeout}s")
            raise

    async def _execute_with_retry(
        self,
        operation: Callable[[], Any],
        operation_name: str = "operation"
    ) -> Any:
        """Execute operation with retry logic"""
        last_exception = None

        for attempt in range(self.config.retry.max_attempts):
            try:
                return await operation()
            except self.config.retry.retryable_exceptions as e:
                last_exception = e

                if attempt < self.config.retry.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(
                        f"{operation_name} failed (attempt {attempt + 1}/"
                        f"{self.config.retry.max_attempts}), retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"{operation_name} failed after {self.config.retry.max_attempts} "
                        f"attempts: {e}"
                    )
            except Exception as e:
                # Non-retryable exception
                self.logger.error(f"{operation_name} failed with non-retryable error: {e}")
                raise

        raise MaxRetriesExceededError(
            operation_name,
            self.config.retry.max_attempts,
            last_exception
        )

    async def _execute_with_circuit_breaker(
        self,
        agent_url: str,
        operation: Callable[[], Any],
        operation_name: str = "operation"
    ) -> Any:
        """Execute operation with circuit breaker protection"""
        circuit_breaker = self._get_circuit_breaker(agent_url)

        if not await circuit_breaker.can_execute():
            raise CircuitOpenError(agent_url)

        try:
            result = await operation()
            await circuit_breaker.record_success()
            return result
        except Exception as e:
            await circuit_breaker.record_failure()
            raise

    async def execute_resilient(
        self,
        agent_url: str,
        operation: Callable[[], Any],
        operation_name: str = "operation",
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute operation with full resilience stack:
        1. Resource limit (semaphore)
        2. Circuit breaker
        3. Timeout
        4. Retry with exponential backoff
        """
        timeout = timeout or self.config.timeout.default_timeout

        async with self._task_semaphore:
            async def wrapped_operation():
                return await self._execute_with_timeout(
                    operation(),
                    timeout,
                    operation_name
                )

            return await self._execute_with_circuit_breaker(
                agent_url,
                lambda: self._execute_with_retry(
                    wrapped_operation,
                    operation_name
                ),
                operation_name
            )

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: The ID of the task to cancel

        Returns:
            True if task was cancelled, False if not found
        """
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._active_tasks[task_id]
            self.logger.info(f"Task {task_id} cancelled")
            return True
        return False

    async def cancel_all_tasks(self):
        """Cancel all active tasks"""
        for task_id in list(self._active_tasks.keys()):
            await self.cancel_task(task_id)

    def get_circuit_breaker_status(self, agent_url: str) -> Dict[str, Any]:
        """Get circuit breaker status for an agent"""
        if agent_url not in self._circuit_breakers:
            return {"state": "unknown", "agent_url": agent_url}

        cb = self._circuit_breakers[agent_url]
        return {
            "agent_url": agent_url,
            "state": cb.state.value,
            "failure_count": cb.failure_count,
            "success_count": cb.success_count,
            "last_failure_time": cb.last_failure_time.isoformat() if cb.last_failure_time else None
        }

    def get_all_circuit_breaker_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get all circuit breaker statuses"""
        return {
            url: self.get_circuit_breaker_status(url)
            for url in self._circuit_breakers
        }

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        return {
            "active_tasks": len(self._active_tasks),
            "max_concurrent_tasks": self.config.resource_limits.max_concurrent_tasks,
            "available_slots": self._task_semaphore._value,
            "circuit_breakers": len(self._circuit_breakers)
        }


class ResilientA2AClient(ResilientA2AClientMixin):
    """
    Standalone resilient A2A client with full feature set.

    This client wraps any base A2A client (mock or HTTP) with
    resilience features.
    """

    def __init__(
        self,
        base_client: Any,
        config: Optional[ResilientClientConfig] = None
    ):
        super().__init__(config)
        self._base_client = base_client

    async def create_task(
        self,
        agent_url: str,
        task_type: str,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> A2ATask:
        """Create task with resilience features"""
        async def operation():
            return await self._base_client.create_task(
                agent_url, task_type, context, correlation_id
            )

        return await self.execute_resilient(
            agent_url,
            operation,
            f"create_task({task_type})",
            timeout or self.config.timeout.default_timeout
        )

    async def get_task_status(
        self,
        agent_url: str,
        task_id: str,
        timeout: Optional[float] = None
    ) -> A2ATask:
        """Get task status with resilience features"""
        async def operation():
            return await self._base_client.get_task_status(agent_url, task_id)

        return await self.execute_resilient(
            agent_url,
            operation,
            f"get_task_status({task_id})",
            timeout or self.config.timeout.default_timeout
        )

    async def create_task_with_wait(
        self,
        agent_url: str,
        task_type: str,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        max_wait_time: Optional[float] = None,
        poll_interval: float = 1.0
    ) -> A2ATask:
        """Create task and wait for completion with resilience"""
        max_wait = max_wait_time or self.config.timeout.task_timeout

        # Create task
        task = await self.create_task(
            agent_url, task_type, context, correlation_id
        )

        # Store as active task
        self._active_tasks[task.task_id] = asyncio.current_task()

        try:
            # Poll for completion
            start_time = datetime.now(timezone.utc)
            while True:
                task = await self.get_task_status(agent_url, task.task_id)

                if task.status in [
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED
                ]:
                    return task

                # Check timeout
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= max_wait:
                    raise TaskTimeoutError(task.task_id, max_wait)

                await asyncio.sleep(poll_interval)
        finally:
            # Remove from active tasks
            self._active_tasks.pop(task.task_id, None)

    async def close(self):
        """Close the client and cleanup"""
        await self.cancel_all_tasks()
        if hasattr(self._base_client, 'close'):
            await self._base_client.close()


# Factory functions for easy client creation

def create_resilient_client(
    base_client: Any,
    max_retries: int = 3,
    default_timeout: float = 30.0,
    task_timeout: float = 300.0,
    max_concurrent_tasks: int = 10,
    circuit_breaker_threshold: int = 5
) -> ResilientA2AClient:
    """
    Factory function to create a resilient A2A client with custom settings.

    Args:
        base_client: The underlying A2A client (mock or HTTP)
        max_retries: Maximum retry attempts
        default_timeout: Default timeout for operations in seconds
        task_timeout: Timeout for task completion in seconds
        max_concurrent_tasks: Maximum concurrent tasks
        circuit_breaker_threshold: Failures before circuit opens

    Returns:
        Configured ResilientA2AClient instance
    """
    config = ResilientClientConfig(
        retry=RetryConfig(max_attempts=max_retries),
        timeout=TimeoutConfig(
            default_timeout=default_timeout,
            task_timeout=task_timeout
        ),
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=circuit_breaker_threshold
        ),
        resource_limits=ResourceLimits(
            max_concurrent_tasks=max_concurrent_tasks
        )
    )
    return ResilientA2AClient(base_client, config)
