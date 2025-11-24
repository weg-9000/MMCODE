"""
Database session management for MMCODE DevStrategist AI
Async SQLAlchemy setup with PostgreSQL/SQLite support
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import logging
import os

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


# Create async engine
DATABASE_URL = get_database_url()
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True,
    # SQLite specific settings
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session maker
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Simple connectivity test
            result = await conn.execute(text("SELECT 1"))
            logger.info("Database connectivity validated")
            return True
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return False