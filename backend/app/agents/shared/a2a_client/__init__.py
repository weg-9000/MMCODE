"""
A2A Client Module

Provides client implementations for Agent-to-Agent communication.

Available clients:
- InMemoryA2AClient: Local development/testing client
- A2AClient: HTTP-based production client
- ResilientA2AClient: Client wrapper with retry, timeout, and circuit breaker

Usage:
    # For development/testing
    from app.agents.shared.a2a_client import InMemoryA2AClient
    client = InMemoryA2AClient()

    # For production with resilience
    from app.agents.shared.a2a_client import (
        A2AClient,
        ResilientA2AClient,
        create_resilient_client
    )
    base_client = A2AClient()
    resilient_client = create_resilient_client(base_client)

    # Or with custom configuration
    from app.agents.shared.a2a_client import (
        ResilientA2AClient,
        ResilientClientConfig,
        RetryConfig,
        TimeoutConfig
    )
    config = ResilientClientConfig(
        retry=RetryConfig(max_attempts=5),
        timeout=TimeoutConfig(default_timeout=60.0)
    )
    resilient_client = ResilientA2AClient(base_client, config)
"""

from .mock_client import InMemoryA2AClient
from .client import A2AClient
from .resilient_client import (
    ResilientA2AClient,
    ResilientA2AClientMixin,
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

__all__ = [
    # Clients
    "InMemoryA2AClient",
    "A2AClient",
    "ResilientA2AClient",
    "ResilientA2AClientMixin",
    # Configuration
    "ResilientClientConfig",
    "RetryConfig",
    "TimeoutConfig",
    "CircuitBreakerConfig",
    "ResourceLimits",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    # Exceptions
    "TaskTimeoutError",
    "CircuitOpenError",
    "MaxRetriesExceededError",
    # Factory
    "create_resilient_client",
]
