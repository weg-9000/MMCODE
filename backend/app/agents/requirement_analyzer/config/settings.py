"""Configuration settings for Requirement Analyzer Agent"""

from pydantic import BaseSettings
from typing import Dict, Any, Optional


class RequirementAnalyzerSettings(BaseSettings):
    """Settings for Requirement Analyzer Agent"""
    
    # Agent Identity
    agent_id: str = "requirement-analyzer"
    agent_name: str = "Requirement Analyzer & Orchestrator"
    version: str = "1.0.0"
    
    # LLM Configuration
    openai_api_key: str
    openai_model: str = "gpt-3.5-turbo"
    temperature: float = 0.1
    max_tokens: int = 2000
    
    # A2A Configuration
    a2a_timeout: int = 300  # 5 minutes
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Agent Endpoints
    architect_url: str = "http://localhost:8001"
    stack_recommender_url: str = "http://localhost:8002"
    documenter_url: str = "http://localhost:8003"
    own_endpoint: str = "http://localhost:8000"
    
    # Redis Configuration (for task tracking)
    redis_url: str = "redis://localhost:6379"
    redis_task_ttl: int = 3600  # 1 hour
    
    # Analysis Configuration
    max_entities: int = 20
    max_use_cases: int = 15
    max_quality_attributes: int = 10
    complexity_threshold_high: float = 0.7
    complexity_threshold_low: float = 0.3
    
    # Coordination Configuration
    parallel_execution: bool = True
    task_timeout: int = 180  # 3 minutes per task
    quality_threshold: float = 0.7
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_prefix = "REQ_ANALYZER_"


def get_agent_config() -> Dict[str, Any]:
    """Get agent configuration as dictionary"""
    settings = RequirementAnalyzerSettings()
    return {
        "agent_id": settings.agent_id,
        "agent_name": settings.agent_name,
        "version": settings.version,
        "openai_api_key": settings.openai_api_key,
        "openai_model": settings.openai_model,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "a2a_timeout": settings.a2a_timeout,
        "max_retry_attempts": settings.max_retry_attempts,
        "retry_delay": settings.retry_delay,
        "architect_url": settings.architect_url,
        "stack_recommender_url": settings.stack_recommender_url,
        "documenter_url": settings.documenter_url,
        "own_endpoint": settings.own_endpoint,
        "redis_url": settings.redis_url,
        "redis_task_ttl": settings.redis_task_ttl,
        "max_entities": settings.max_entities,
        "max_use_cases": settings.max_use_cases,
        "max_quality_attributes": settings.max_quality_attributes,
        "complexity_threshold_high": settings.complexity_threshold_high,
        "complexity_threshold_low": settings.complexity_threshold_low,
        "parallel_execution": settings.parallel_execution,
        "task_timeout": settings.task_timeout,
        "quality_threshold": settings.quality_threshold,
        "log_level": settings.log_level,
        "log_format": settings.log_format
    }