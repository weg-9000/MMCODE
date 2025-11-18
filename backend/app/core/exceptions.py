from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

class DevStrategistException(Exception):
    """Base exception for DevStrategist AI application"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AgentTimeoutException(DevStrategistException):
    """Raised when agent execution times out"""
    def __init__(self, agent_name: str):
        super().__init__(f"Agent '{agent_name}' execution timed out", 408)

class KnowledgeBaseException(DevStrategistException):
    """Raised when knowledge base operations fail"""
    def __init__(self, message: str):
        super().__init__(f"Knowledge base error: {message}", 500)

class ValidationException(DevStrategistException):
    """Raised when input validation fails"""
    def __init__(self, message: str):
        super().__init__(f"Validation error: {message}", 422)

async def dev_strategist_exception_handler(request: Request, exc: DevStrategistException):
    logger.error(f"DevStrategist exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "type": exc.__class__.__name__
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )