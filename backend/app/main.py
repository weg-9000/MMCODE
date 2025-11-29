# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from .core.config import settings
from .core.exceptions import (
    DevStrategistException,
    dev_strategist_exception_handler,
    validation_exception_handler,
    http_exception_handler
)
from .api.middleware import LoggingMiddleware, SecurityHeadersMiddleware
from .db.session import init_db, validate_db_setup
from .core.dependencies import initialize_agents, cleanup_agents

# Secure logging configuration
from .utils.logging_filter import setup_secure_logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Setup secure logging with sensitive data filtering
setup_secure_logging()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management with timeout protection"""
    import asyncio
    
    # Startup
    logger.info("Application starting...")
    
    # Database initialization with timeout
    try:
        async with asyncio.timeout(15):  # 15 second timeout for DB init
            db_validation = await validate_db_setup()
            if not db_validation:
                logger.warning("Database setup validation failed - continuing with limited functionality")
            else:
                await init_db()
                logger.info("Database initialized successfully")
    except asyncio.TimeoutError:
        logger.warning("Database initialization timed out - API will start with limited functionality")
    except Exception as e:
        logger.warning(f"Database initialization failed: {str(e)} - API will start with limited functionality")
    
    # Initialize agent registry with timeout and error handling
    try:
        async with asyncio.timeout(30):  # 30 second timeout for agent init
            await initialize_agents()
            logger.info("Agent registry initialized successfully")
    except asyncio.TimeoutError:
        logger.warning("Agent initialization timed out - agents will be initialized on first use")
    except Exception as e:
        logger.warning(f"Agent initialization failed: {str(e)} - agents will be initialized on first use")
    
    logger.info("Application startup completed - ready to accept requests")
    
    yield
    
    # Shutdown with timeout protection
    logger.info("Application shutting down...")
    
    try:
        async with asyncio.timeout(10):  # 10 second timeout for cleanup
            await cleanup_agents()
            logger.info("Agent cleanup completed")
            
            # Cleanup database connections
            from .db.session import cleanup_db_connections
            await cleanup_db_connections()
            
    except asyncio.TimeoutError:
        logger.warning("Cleanup timed out")
    except Exception as e:
        logger.warning(f"Cleanup error: {str(e)}")
    
    logger.info("Application shutdown completed")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="AI-powered development strategy automation platform with agent orchestration",
    docs_url=None,  # Using custom /docs endpoint with proper CSP
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Rate limiting (Redis will be optional fallback to in-memory)
try:
    import redis.asyncio as redis
    redis_client = redis.from_url(settings.REDIS_URL)
    logger.info("Redis client initialized for rate limiting")
except Exception as e:
    logger.warning(f"Redis not available, using in-memory rate limiter: {e}")
    redis_client = None

# Add rate limiting middleware
from .middleware.rate_limit import RateLimitMiddleware
app.add_middleware(
    RateLimitMiddleware,
    redis_client=redis_client,
    default_limit=settings.RATE_LIMIT_PER_MINUTE,
    default_window=60,
    endpoint_limits={
        "/api/v1/orchestrate": (10, 60),  # Orchestration: 10 per minute
        "/api/v1/orchestrate/": (10, 60),
        "/api/v1/sessions": (30, 60),     # Sessions: 30 per minute
        "/api/v1/agents": (100, 60),      # Agent endpoints: 100 per minute
    }
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Exception handlers
app.add_exception_handler(DevStrategistException, dev_strategist_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

@app.get("/")
async def root():
    """Root endpoint with API information and documentation links"""
    documentation_links = {}
    if settings.DEBUG:
        documentation_links = {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        }
    
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "status": "running",
        "api_base": settings.API_PREFIX,
        "documentation": documentation_links,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    try:
        from .db.session import AsyncSessionLocal
        from sqlalchemy import text
        import asyncio
        
        async with asyncio.timeout(5):  # 5 second timeout
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
        db_status = "connected"
    except asyncio.TimeoutError:
        db_status = "timeout"
    except Exception:
        db_status = "error"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with database performance metrics"""
    from .db.session import get_db_health_info, check_db_performance
    from .core.dependencies import system_health_check
    import psutil
    
    try:
        # Get database health
        db_health = await get_db_health_info()
        
        # Get database performance metrics
        db_performance = await check_db_performance()
        
        # Get system health
        system_health = await system_health_check()
        
        # Get memory usage
        memory_info = psutil.virtual_memory()
        
        return {
            "status": "healthy" if db_health.get("status") == "healthy" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "database": db_health,
            "performance": db_performance,
            "agents": system_health,
            "memory": {
                "total_gb": round(memory_info.total / (1024**3), 2),
                "available_gb": round(memory_info.available / (1024**3), 2),
                "percent_used": memory_info.percent,
                "status": "healthy" if memory_info.percent < 80 else "warning"
            },
            "recommendations": _get_health_recommendations(db_health, db_performance, system_health)
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _get_health_recommendations(db_health: dict, db_performance: dict, system_health: dict) -> list:
    """Generate health recommendations based on system status"""
    recommendations = []
    
    # Database recommendations
    if db_health.get("status") != "healthy":
        recommendations.append("Check database connectivity and configuration")
    
    if db_health.get("response_time_ms", 0) > 1000:
        recommendations.append("Database response time is slow - consider connection pool optimization")
    
    if db_performance.get("status") == "success":
        metrics = db_performance.get("metrics", {})
        if metrics.get("connection_pool_utilization", 0) > 80:
            recommendations.append("Connection pool utilization high - consider increasing pool size")
    
    # Agent system recommendations
    if system_health.get("system_status") != "healthy":
        recommendations.append("Agent system is degraded - check individual agent health")
    
    if system_health.get("healthy_agents", 0) < system_health.get("total_agents", 0):
        recommendations.append("Some agents are unhealthy - check agent initialization")
    
    if not recommendations:
        recommendations.append("All systems operating normally")
    
    return recommendations

# API router registration
from app.api.v1 import sessions, agents, orchestration, a2a

app.include_router(sessions.router, prefix=f"{settings.API_PREFIX}/sessions", tags=["sessions"])
app.include_router(agents.router, prefix=f"{settings.API_PREFIX}/agents", tags=["agents"])
app.include_router(orchestration.router, prefix=f"{settings.API_PREFIX}/orchestrate", tags=["orchestration"])
app.include_router(a2a.router, prefix=f"{settings.API_PREFIX}/a2a", tags=["a2a_communication"])

if settings.DEBUG:
    from fastapi.openapi.docs import get_swagger_ui_html
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Custom Swagger UI with explicit CSP headers for CDN resources"""
        logger.info("Serving custom Swagger UI with permissive CSP")
        
        # 1) 이 함수는 이미 HTMLResponse 객체를 반환함
        response = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )
        
        # 2) 반환된 response 는 그대로 사용하고, 여기에 헤더만 추가
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net blob:; "
            "script-src-elem 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net blob:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "style-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net blob:; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "connect-src 'self' https://cdn.jsdelivr.net blob:; "
            "worker-src 'self' blob:;"
        )
        
        logger.debug("Applied enhanced CSP policy for Swagger UI with element directives")
        return response



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )