"""
Database session management for MMCODE DevStrategist AI
Async SQLAlchemy setup with PostgreSQL/SQLite support
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import logging
import os
import asyncio

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


# Database configuration
def get_database_url() -> str:
    """Get database URL from environment or default to SQLite"""
    # Try to get from environment
    database_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL")
    
    if database_url:
        # Convert PostgreSQL URL to async version if needed
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        return database_url
    
    # Default to SQLite for development
    return "sqlite+aiosqlite:///./devstrategist.db"


# Create optimized async engine with connection pool settings
DATABASE_URL = get_database_url()

# Determine if we're using PostgreSQL or SQLite for different configurations
is_postgres = "postgresql" in DATABASE_URL.lower()

if is_postgres:
    # PostgreSQL optimized configuration with improved performance settings
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Disable SQL logging for performance
        future=True,
        # Enhanced connection pool optimization for PostgreSQL
        pool_size=10,          # Increased from 5 to handle more concurrent requests
        max_overflow=5,        # Allow overflow for peak loads
        pool_timeout=3,        # Reduced from 5s for faster failure detection
        pool_recycle=3600,     # 1 hour - balance connection freshness with performance
        pool_pre_ping=True,    # Validate connections before use
        # Enhanced connection-level optimizations
        connect_args={
            "command_timeout": 30,        # Increased timeout for complex operations
            "connect_timeout": 5,         # Quick connection establishment
            "server_settings": {
                "application_name": "devstrategist_ai",
                "jit": "off",                    # Disable JIT for consistent performance
                "statement_timeout": "30s",      # Increased for complex queries
                "shared_preload_libraries": "",  # Optimize for basic usage
                "work_mem": "4MB",              # Memory for sorting/hash operations
                "maintenance_work_mem": "64MB",  # Memory for maintenance operations
                "checkpoint_completion_target": "0.9"  # Optimize checkpoint performance
            }
        }
    )
else:
    # SQLite configuration (for development)
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Disable SQL logging for performance
        future=True,
        # SQLite specific settings
        connect_args={
            "check_same_thread": False,
            "timeout": 10,  # 10 second timeout for SQLite operations
            "isolation_level": None  # Autocommit mode for better concurrency
        }
    )

logger.info(f"Database engine created for {'PostgreSQL' if is_postgres else 'SQLite'} with optimized connection pool")

# Create optimized session maker
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    # Session-level optimizations
    autoflush=False,  # Don't auto-flush for better performance
    autocommit=False  # Explicit transaction control
)


async def get_db() -> AsyncSession:
    """Optimized dependency to get database session with timeout protection and retry mechanism"""
    import asyncio
    from sqlalchemy.exc import DisconnectionError, OperationalError
    
    max_retries = 3
    retry_delay = 1.0  # seconds
    
    for attempt in range(max_retries + 1):
        try:
            # Add timeout protection for session creation and operations
            async with asyncio.timeout(15):  # Increased to 15 seconds for complex operations
                async with AsyncSessionLocal() as session:
                    try:
                        # Test connection with a simple query
                        await session.execute(text("SELECT 1"))
                        yield session
                        break  # Success, exit retry loop
                    except Exception as e:
                        logger.warning(f"Database session error: {e}")
                        await session.rollback()
                        raise
                    finally:
                        await session.close()
                        
        except (DisconnectionError, OperationalError, ConnectionRefusedError) as e:
            if attempt < max_retries:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                logger.error(f"Database connection failed after {max_retries + 1} attempts")
                raise RuntimeError("Database connection failed after multiple attempts")
                
        except asyncio.TimeoutError:
            if attempt < max_retries:
                logger.warning(f"Database session timeout on attempt {attempt + 1}. Retrying...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                logger.error("Database session operation timed out after multiple attempts")
                raise RuntimeError("Database session operation timed out after multiple attempts")


async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from app.models.models import Session, Task, Agent
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def validate_db_setup() -> bool:
    """Validate database setup and connectivity"""
    try:
        import asyncio
        from sqlalchemy import text
        
        async with asyncio.timeout(10):  # 10 second timeout for validation
            async with engine.begin() as conn:
                # Simple connectivity test
                result = await conn.execute(text("SELECT 1"))
                logger.info("Database connectivity validated")
                return True
    except asyncio.TimeoutError:
        logger.error("Database validation timed out")
        return False
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return False


async def get_db_health_info() -> dict:
    """Get detailed database health information"""
    try:
        import asyncio
        from sqlalchemy import text
        import time
        
        start_time = time.time()
        
        async with asyncio.timeout(5):  # 5 second timeout for health check
            async with AsyncSessionLocal() as session:
                # Test basic connectivity
                await session.execute(text("SELECT 1"))
                
                # Get connection pool status
                pool = engine.pool
                pool_status = {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalidated": pool.invalidated()
                }
                
                # Test response time
                response_time = (time.time() - start_time) * 1000  # ms
                
                return {
                    "status": "healthy",
                    "database_type": "postgresql" if is_postgres else "sqlite",
                    "response_time_ms": round(response_time, 2),
                    "pool_status": pool_status,
                    "engine_echo": engine.echo,
                    "connection_timeout": "10s"
                }
                
    except asyncio.TimeoutError:
        return {
            "status": "unhealthy",
            "error": "Health check timed out",
            "response_time_ms": 5000  # Timeout value
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "response_time_ms": None
        }


async def check_db_performance() -> dict:
    """Check database performance metrics"""
    try:
        import asyncio
        import time
        from sqlalchemy import text
        
        performance_metrics = {}
        
        # Test query performance
        async with asyncio.timeout(10):  # 10 second timeout
            async with AsyncSessionLocal() as session:
                # Simple query test
                start = time.time()
                await session.execute(text("SELECT 1"))
                simple_query_time = (time.time() - start) * 1000
                
                # Complex query test (if tables exist)
                try:
                    start = time.time()
                    result = await session.execute(text(
                        "SELECT COUNT(*) as session_count FROM sessions" if is_postgres 
                        else "SELECT COUNT(*) as session_count FROM sessions"
                    ))
                    complex_query_time = (time.time() - start) * 1000
                    session_count = result.scalar()
                except:
                    complex_query_time = None
                    session_count = "table_not_found"
                
                performance_metrics = {
                    "simple_query_ms": round(simple_query_time, 2),
                    "complex_query_ms": round(complex_query_time, 2) if complex_query_time else None,
                    "session_count": session_count,
                    "connection_pool_utilization": (engine.pool.checkedout() / engine.pool.size()) * 100
                }
                
        return {"status": "success", "metrics": performance_metrics}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Database caching layer
_query_cache = {}
_cache_ttl = 300  # 5 minutes default TTL
_cache_lock = asyncio.Lock()

async def get_cached_query_result(query_key: str, query_func, ttl: int = None):
    """Execute query with caching support"""
    import time
    
    if ttl is None:
        ttl = _cache_ttl
    
    async with _cache_lock:
        # Check if we have a cached result
        if query_key in _query_cache:
            result, timestamp = _query_cache[query_key]
            if time.time() - timestamp < ttl:
                logger.debug(f"Cache hit for query: {query_key}")
                return result
        
        # Execute query and cache result
        logger.debug(f"Cache miss for query: {query_key}, executing...")
        try:
            result = await query_func()
            _query_cache[query_key] = (result, time.time())
            return result
        except Exception as e:
            logger.error(f"Query execution failed for {query_key}: {e}")
            raise

async def clear_query_cache(pattern: str = None):
    """Clear query cache, optionally by pattern"""
    async with _cache_lock:
        if pattern:
            keys_to_remove = [key for key in _query_cache.keys() if pattern in key]
            for key in keys_to_remove:
                del _query_cache[key]
            logger.info(f"Cleared {len(keys_to_remove)} cache entries matching pattern: {pattern}")
        else:
            _query_cache.clear()
            logger.info("Cleared entire query cache")

async def get_cache_stats() -> dict:
    """Get cache statistics"""
    async with _cache_lock:
        return {
            "cache_size": len(_query_cache),
            "cache_keys": list(_query_cache.keys()),
            "ttl_seconds": _cache_ttl
        }

async def cleanup_db_connections():
    """Clean up database connections and pool"""
    try:
        logger.info("Cleaning up database connections...")
        
        # Clear cache
        await clear_query_cache()
        
        # Dispose engine
        await engine.dispose()
        logger.info("Database connections cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up database connections: {e}")