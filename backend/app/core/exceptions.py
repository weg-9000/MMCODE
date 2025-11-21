"""
Standardized exception handling for DevStrategist AI agents
Provides consistent error types, formatting, and handling across all components
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse


class ErrorSeverity(str, Enum):
    """Error severity levels for consistent categorization"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for consistent classification"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    AGENT_COMMUNICATION = "agent_communication"
    LLM_SERVICE = "llm_service"
    PROCESSING = "processing"
    SYSTEM = "system"


class ErrorDetails(BaseModel):
    """Standardized error details structure"""
    code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    correlation_id: Optional[str] = None
    context: Dict[str, Any] = {}
    suggestions: List[str] = []
    recoverable: bool = True
    retry_after_seconds: Optional[int] = None


class DevStrategistException(Exception):
    """
    Base exception class for all DevStrategist AI errors
    Provides standardized error information and formatting
    """
    
    def __init__(
        self,
        message: str,
        code: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        recoverable: bool = True,
        retry_after_seconds: Optional[int] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(message)
        self.details = ErrorDetails(
            code=code,
            message=message,
            category=category,
            severity=severity,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            context=context or {},
            suggestions=suggestions or [],
            recoverable=recoverable,
            retry_after_seconds=retry_after_seconds
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": {
                "code": self.details.code,
                "message": self.details.message,
                "category": self.details.category.value,
                "severity": self.details.severity.value,
                "timestamp": self.details.timestamp.isoformat(),
                "correlation_id": self.details.correlation_id,
                "context": self.details.context,
                "suggestions": self.details.suggestions,
                "recoverable": self.details.recoverable,
                "retry_after_seconds": self.details.retry_after_seconds
            }
        }
    
    def to_log_dict(self) -> Dict[str, Any]:
        """Convert exception to structured logging format"""
        return {
            "error_code": self.details.code,
            "error_message": self.details.message,
            "error_category": self.details.category.value,
            "error_severity": self.details.severity.value,
            "correlation_id": self.details.correlation_id,
            "context": self.details.context,
            "recoverable": self.details.recoverable
        }


# Specific exception classes for different error scenarios

class ValidationException(DevStrategistException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: str, value: Any, **kwargs):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            context={"field": field, "value": str(value)},
            suggestions=["Check input format and try again", "Refer to API documentation"],
            **kwargs
        )


class AgentCommunicationException(DevStrategistException):
    """Raised when agent-to-agent communication fails"""
    
    def __init__(self, message: str, agent_id: str, endpoint: str, **kwargs):
        super().__init__(
            message=message,
            code="AGENT_COMMUNICATION_ERROR",
            category=ErrorCategory.AGENT_COMMUNICATION,
            severity=ErrorSeverity.HIGH,
            context={"agent_id": agent_id, "endpoint": endpoint},
            suggestions=[
                "Check agent availability",
                "Verify network connectivity",
                "Review agent configuration"
            ],
            retry_after_seconds=30,
            **kwargs
        )


class LLMServiceException(DevStrategistException):
    """Raised when LLM service operations fail"""
    
    def __init__(self, message: str, model: str, operation: str, **kwargs):
        super().__init__(
            message=message,
            code="LLM_SERVICE_ERROR",
            category=ErrorCategory.LLM_SERVICE,
            severity=ErrorSeverity.HIGH,
            context={"model": model, "operation": operation},
            suggestions=[
                "Check API key validity",
                "Verify model availability",
                "Review request parameters",
                "Consider using fallback strategies"
            ],
            retry_after_seconds=60,
            **kwargs
        )


class ProcessingException(DevStrategistException):
    """Raised when processing operations fail"""
    
    def __init__(self, message: str, process_step: str, **kwargs):
        super().__init__(
            message=message,
            code="PROCESSING_ERROR",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            context={"process_step": process_step},
            suggestions=[
                "Review input data quality",
                "Check processing parameters",
                "Try again with different inputs"
            ],
            **kwargs
        )


class DatabaseException(DevStrategistException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, operation: str, table: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            context={"operation": operation, "table": table},
            suggestions=[
                "Check database connectivity",
                "Verify data integrity",
                "Review query parameters"
            ],
            retry_after_seconds=10,
            **kwargs
        )


class ExternalServiceException(DevStrategistException):
    """Raised when external service calls fail"""
    
    def __init__(self, message: str, service: str, endpoint: str, **kwargs):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            context={"service": service, "endpoint": endpoint},
            suggestions=[
                "Check service availability",
                "Verify API credentials",
                "Review request format"
            ],
            retry_after_seconds=30,
            **kwargs
        )


class ConfigurationException(DevStrategistException):
    """Raised when configuration errors occur"""
    
    def __init__(self, message: str, config_key: str, **kwargs):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            context={"config_key": config_key},
            suggestions=[
                "Check environment variables",
                "Verify configuration file",
                "Review application settings"
            ],
            recoverable=False,
            **kwargs
        )


# Exception handlers for FastAPI

async def dev_strategist_exception_handler(request: Request, exc: DevStrategistException) -> JSONResponse:
    """
    Global exception handler for DevStrategist exceptions
    """
    logger = logging.getLogger("exception_handler")
    
    # Log the exception with structured data
    logger.error(
        f"DevStrategist exception occurred: {exc.details.code}",
        extra=exc.to_log_dict()
    )
    
    # Determine HTTP status code based on error category
    status_code = _get_status_code_for_category(exc.details.category)
    
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
        headers=_get_error_headers(exc.details)
    )


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    """
    Specific handler for validation exceptions
    """
    logger = logging.getLogger("validation_handler")
    logger.warning(f"Validation error: {exc.details.message}", extra=exc.to_log_dict())
    
    return JSONResponse(
        status_code=400,
        content=exc.to_dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler for standard HTTP exceptions, converting them to DevStrategist format
    """
    dev_exc = DevStrategistException(
        message=str(exc.detail),
        code="HTTP_ERROR",
        category=_get_category_for_status(exc.status_code),
        severity=_get_severity_for_status(exc.status_code),
        context={"status_code": exc.status_code, "path": request.url.path}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=dev_exc.to_dict()
    )


# Utility functions

def _get_status_code_for_category(category: ErrorCategory) -> int:
    """Map error categories to HTTP status codes"""
    category_status_map = {
        ErrorCategory.VALIDATION: 400,
        ErrorCategory.AUTHENTICATION: 401,
        ErrorCategory.AUTHORIZATION: 403,
        ErrorCategory.NOT_FOUND: 404,
        ErrorCategory.BUSINESS_LOGIC: 422,
        ErrorCategory.EXTERNAL_SERVICE: 502,
        ErrorCategory.DATABASE: 503,
        ErrorCategory.NETWORK: 503,
        ErrorCategory.CONFIGURATION: 500,
        ErrorCategory.AGENT_COMMUNICATION: 502,
        ErrorCategory.LLM_SERVICE: 502,
        ErrorCategory.PROCESSING: 500,
        ErrorCategory.SYSTEM: 500
    }
    return category_status_map.get(category, 500)


def _get_category_for_status(status_code: int) -> ErrorCategory:
    """Map HTTP status codes to error categories"""
    status_category_map = {
        400: ErrorCategory.VALIDATION,
        401: ErrorCategory.AUTHENTICATION,
        403: ErrorCategory.AUTHORIZATION,
        404: ErrorCategory.NOT_FOUND,
        422: ErrorCategory.BUSINESS_LOGIC,
        500: ErrorCategory.SYSTEM,
        502: ErrorCategory.EXTERNAL_SERVICE,
        503: ErrorCategory.DATABASE
    }
    return status_category_map.get(status_code, ErrorCategory.SYSTEM)


def _get_severity_for_status(status_code: int) -> ErrorSeverity:
    """Map HTTP status codes to error severities"""
    if status_code < 400:
        return ErrorSeverity.LOW
    elif status_code < 500:
        return ErrorSeverity.MEDIUM
    else:
        return ErrorSeverity.HIGH


def _get_error_headers(error_details: ErrorDetails) -> Dict[str, str]:
    """Generate appropriate headers for error responses"""
    headers = {
        "X-Error-Code": error_details.code,
        "X-Error-Category": error_details.category.value
    }
    
    if error_details.correlation_id:
        headers["X-Correlation-Id"] = error_details.correlation_id
    
    if error_details.retry_after_seconds:
        headers["Retry-After"] = str(error_details.retry_after_seconds)
    
    return headers


# Context managers for exception handling

class ExceptionContext:
    """Context manager for adding structured context to exceptions"""
    
    def __init__(self, correlation_id: Optional[str] = None, **context):
        self.correlation_id = correlation_id
        self.context = context
        self.logger = logging.getLogger("exception_context")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, DevStrategistException):
            # Add context to existing DevStrategist exception
            exc_val.details.correlation_id = self.correlation_id
            exc_val.details.context.update(self.context)
        elif exc_type:
            # Convert other exceptions to DevStrategist format
            dev_exc = DevStrategistException(
                message=str(exc_val),
                code="UNHANDLED_EXCEPTION",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context=self.context,
                correlation_id=self.correlation_id,
                suggestions=["Contact support if this persists"]
            )
            
            self.logger.error(
                f"Unhandled exception converted: {exc_type.__name__}",
                extra=dev_exc.to_log_dict()
            )
            
            # Replace the original exception
            raise dev_exc from exc_val
        
        return False  # Don't suppress the exception


# Agent-specific exception utilities

def create_agent_exception(
    agent_id: str,
    message: str,
    operation: str,
    **kwargs
) -> DevStrategistException:
    """Create a standardized exception for agent operations"""
    return DevStrategistException(
        message=f"Agent {agent_id} failed: {message}",
        code=f"AGENT_{agent_id.upper().replace('-', '_')}_ERROR",
        category=ErrorCategory.AGENT_COMMUNICATION,
        context={"agent_id": agent_id, "operation": operation},
        suggestions=[
            f"Check {agent_id} agent status",
            "Verify agent configuration",
            "Review input parameters"
        ],
        **kwargs
    )


def create_task_exception(
    task_id: str,
    task_type: str,
    message: str,
    **kwargs
) -> DevStrategistException:
    """Create a standardized exception for task operations"""
    return ProcessingException(
        message=f"Task {task_id} failed: {message}",
        process_step=f"task_{task_type}",
        context={"task_id": task_id, "task_type": task_type},
        **kwargs
    )


def create_quality_exception(
    component: str,
    quality_score: float,
    threshold: float,
    **kwargs
) -> DevStrategistException:
    """Create a standardized exception for quality threshold violations"""
    return ProcessingException(
        message=f"Quality score {quality_score:.2f} below threshold {threshold:.2f} for {component}",
        process_step="quality_validation",
        context={
            "component": component,
            "quality_score": quality_score,
            "threshold": threshold
        },
        suggestions=[
            "Review input parameters",
            "Adjust processing settings",
            "Lower quality threshold if acceptable"
        ],
        **kwargs
    )