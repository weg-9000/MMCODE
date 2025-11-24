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

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger.info("Application starting...")
    
    # Database initialization
    try:
        db_validation = await validate_db_setup()
        if not db_validation:
            logger.error("Database setup validation failed")
        else:
            await init_db()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    
    # Initialize agent registry
    try:
        await initialize_agents()
        logger.info("Agent registry initialized successfully")
    except Exception as e:
        logger.error(f"Agent initialization failed: {str(e)}")
    
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    
    try:
        # Cleanup agents and connections
        await cleanup_agents()
        logger.info("Agent cleanup completed")
    except Exception as e:
        logger.error(f"Agent cleanup error: {str(e)}")
    
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
    try:
        from .db.session import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

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