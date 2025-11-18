# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
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
from .database.session import init_db
from .api.routes import (
    sessions,
    agents,
    knowledge,
    auth
)

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
        from .database.session import validate_db_setup
        db_validation = await validate_db_setup()
        if not db_validation:
            logger.error("Database setup validation failed")
        else:
            await init_db()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    
    # Initialize schedulers
    scheduler = None
    try:
        from .workers.crawl_scheduler import init_scheduler
        scheduler = init_scheduler()
        if scheduler and not scheduler.running:
            scheduler.start()
            logger.info("Crawl scheduler started")
    except Exception as e:
        logger.error(f"Scheduler initialization failed: {str(e)}")
    
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler shutdown completed")
    except Exception as e:
        logger.error(f"Scheduler shutdown error: {str(e)}")
    
    logger.info("Application shutdown completed")

app = FastAPI(
    title="DevStrategist AI API",
    version="0.1.0",
    debug=settings.DEBUG,
    description="AI-powered development strategy automation platform",
    docs_url="/docs",
    redoc_url="/redoc",
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

# Security middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Exception handlers
app.add_exception_handler(DevStrategistException, dev_strategist_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

@app.get("/")
async def root():
    return {
        "message": "DevStrategist AI API",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    try:
        from .database.session import AsyncSessionLocal
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
api_prefix = settings.API_PREFIX
app.include_router(sessions.router, prefix=api_prefix, tags=["sessions"])
app.include_router(agents.router, prefix=api_prefix, tags=["agents"])
app.include_router(knowledge.router, prefix=api_prefix, tags=["knowledge"])
app.include_router(auth.router, prefix=api_prefix, tags=["authentication"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )