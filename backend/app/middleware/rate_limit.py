"""
Rate Limiting Middleware for DevStrategist AI
Prevents API abuse and ensures fair resource allocation
"""

import time
import logging
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Redis-based sliding window rate limiter
    
    Implements a precise sliding window algorithm using Redis sorted sets
    for distributed rate limiting across multiple application instances
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        identifier: str = "request"
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Unique identifier for the rate limit bucket (e.g., IP address)
            limit: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            identifier: Additional identifier for request tracking
            
        Returns:
            Tuple of (is_allowed, rate_info) where rate_info contains:
            - current_count: Current number of requests in window
            - limit: The limit value
            - window_seconds: Window duration
            - reset_time: When the current window resets
        """
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"rate_limit:{key}"
        
        try:
            async with self.redis.pipeline() as pipe:
                # Remove expired entries
                await pipe.zremrangebyscore(redis_key, 0, window_start)
                
                # Count current requests in window
                await pipe.zcount(redis_key, window_start, now)
                
                # Execute pipeline
                results = await pipe.execute()
                current_count = results[1]
                
                # Check if limit exceeded
                if current_count >= limit:
                    rate_info = {
                        "current_count": current_count,
                        "limit": limit,
                        "window_seconds": window_seconds,
                        "reset_time": int(now + window_seconds)
                    }
                    return False, rate_info
                
                # Add current request
                request_id = f"{identifier}:{now}:{id(self)}"
                await self.redis.zadd(redis_key, {request_id: now})
                
                # Set expiration for cleanup
                await self.redis.expire(redis_key, window_seconds + 1)
                
                # Clean up old entries (additional safety)
                await self.redis.zremrangebyscore(redis_key, 0, window_start)
                
                rate_info = {
                    "current_count": current_count + 1,
                    "limit": limit,
                    "window_seconds": window_seconds,
                    "reset_time": int(now + window_seconds)
                }
                
                return True, rate_info
                
        except Exception as e:
            # On Redis failure, allow request but log error
            self.logger.error(f"Rate limiter Redis error: {e}")
            rate_info = {
                "current_count": 0,
                "limit": limit,
                "window_seconds": window_seconds,
                "reset_time": int(now + window_seconds)
            }
            return True, rate_info
    
    async def get_current_usage(self, key: str, window_seconds: int) -> int:
        """Get current usage count for a key"""
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"rate_limit:{key}"
        
        try:
            return await self.redis.zcount(redis_key, window_start, now)
        except Exception as e:
            self.logger.error(f"Error getting rate limit usage: {e}")
            return 0


class InMemoryRateLimiter:
    """
    Fallback in-memory rate limiter
    
    Used when Redis is not available. Note: This is not distributed
    and will only work for single application instance
    """
    
    def __init__(self):
        self._buckets: Dict[str, Dict[str, float]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        identifier: str = "request"
    ) -> Tuple[bool, Dict[str, int]]:
        """Check if request is allowed (in-memory implementation)"""
        now = time.time()
        window_start = now - window_seconds
        
        # Initialize bucket if not exists
        if key not in self._buckets:
            self._buckets[key] = {}
        
        bucket = self._buckets[key]
        
        # Remove expired entries
        expired_keys = [k for k, timestamp in bucket.items() if timestamp < window_start]
        for k in expired_keys:
            del bucket[k]
        
        current_count = len(bucket)
        
        if current_count >= limit:
            rate_info = {
                "current_count": current_count,
                "limit": limit,
                "window_seconds": window_seconds,
                "reset_time": int(now + window_seconds)
            }
            return False, rate_info
        
        # Add current request
        bucket[f"{identifier}:{now}"] = now
        
        rate_info = {
            "current_count": current_count + 1,
            "limit": limit,
            "window_seconds": window_seconds,
            "reset_time": int(now + window_seconds)
        }
        
        return True, rate_info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI applications
    
    Provides configurable rate limiting with different limits
    for different endpoint patterns
    """
    
    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        default_limit: int = 60,
        default_window: int = 60,
        endpoint_limits: Optional[Dict[str, Tuple[int, int]]] = None
    ):
        """
        Initialize rate limit middleware
        
        Args:
            app: FastAPI application instance
            redis_client: Redis client for distributed rate limiting
            default_limit: Default requests per window
            default_window: Default window size in seconds
            endpoint_limits: Dict mapping endpoint patterns to (limit, window) tuples
        """
        super().__init__(app)
        
        if redis_client:
            self.limiter = RedisRateLimiter(redis_client)
        else:
            self.limiter = InMemoryRateLimiter()
            logger.warning("Using in-memory rate limiter - not suitable for production with multiple instances")
        
        self.default_limit = default_limit
        self.default_window = default_window
        self.endpoint_limits = endpoint_limits or {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting"""
        
        # Skip rate limiting for certain endpoints
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Get rate limit for this endpoint
        limit, window = self._get_rate_limit_for_endpoint(request.url.path)
        
        # Check rate limit
        is_allowed, rate_info = await self.limiter.is_allowed(
            key=client_id,
            limit=limit,
            window_seconds=window,
            identifier=request.url.path
        )
        
        if not is_allowed:
            # Log rate limit exceeded
            self._log_rate_limit_exceeded(request, client_id, rate_info)
            
            # Return rate limit exceeded response
            headers = {
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": str(max(0, rate_info["limit"] - rate_info["current_count"])),
                "X-RateLimit-Reset": str(rate_info["reset_time"]),
                "Retry-After": str(rate_info["window_seconds"])
            }
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {rate_info['limit']} per {rate_info['window_seconds']} seconds",
                    "retry_after": rate_info["window_seconds"],
                    "reset_time": rate_info["reset_time"]
                },
                headers=headers
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(max(0, rate_info["limit"] - rate_info["current_count"]))
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset_time"])
        
        return response
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Determine if rate limiting should be skipped for this request"""
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/ping"
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier for rate limiting"""
        # Try to get real IP from headers (for reverse proxy scenarios)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Add user agent to make identifier more specific
        user_agent = request.headers.get("User-Agent", "unknown")
        user_agent_hash = str(abs(hash(user_agent)) % 10000)
        
        return f"{client_ip}:{user_agent_hash}"
    
    def _get_rate_limit_for_endpoint(self, path: str) -> Tuple[int, int]:
        """Get rate limit configuration for specific endpoint"""
        
        # Check for exact matches first
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Check for pattern matches
        for pattern, (limit, window) in self.endpoint_limits.items():
            if path.startswith(pattern):
                return limit, window
        
        # Return default
        return self.default_limit, self.default_window
    
    def _log_rate_limit_exceeded(
        self, 
        request: Request, 
        client_id: str, 
        rate_info: Dict[str, int]
    ):
        """Log rate limit exceeded event"""
        self.logger.warning(
            f"Rate limit exceeded for client {client_id}",
            extra={
                "event_type": "rate_limit_exceeded",
                "client_id": client_id,
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("User-Agent", "unknown"),
                "current_count": rate_info["current_count"],
                "limit": rate_info["limit"],
                "window_seconds": rate_info["window_seconds"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


def create_rate_limit_middleware(
    redis_client: Optional[redis.Redis] = None,
    config: Optional[Dict] = None
) -> RateLimitMiddleware:
    """
    Create rate limit middleware with DevStrategist AI specific configuration
    
    Args:
        redis_client: Redis client for distributed rate limiting
        config: Optional configuration override
        
    Returns:
        Configured RateLimitMiddleware instance
    """
    
    # Default configuration for DevStrategist AI
    default_config = {
        "default_limit": 60,  # 60 requests per minute
        "default_window": 60,  # 1 minute window
        "endpoint_limits": {
            "/api/v1/orchestrate": (10, 60),  # Orchestration: 10 per minute
            "/api/v1/orchestrate/": (10, 60),
            "/api/v1/sessions": (30, 60),     # Sessions: 30 per minute
            "/api/v1/agents": (100, 60),      # Agent endpoints: 100 per minute
        }
    }
    
    if config:
        default_config.update(config)
    
    return RateLimitMiddleware(
        app=None,  # Will be set when added to FastAPI
        redis_client=redis_client,
        **default_config
    )