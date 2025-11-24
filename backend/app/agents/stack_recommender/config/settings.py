"""
Configuration settings for StackRecommender agent.
Manages environment variables, default values, and validation.
"""
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict
import os


class StackRecommenderSettings(BaseSettings):
    """StackRecommender agent configuration"""
    
    # Agent Identity
    agent_name: str = Field(default="stack-recommender", description="Agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")
    agent_description: str = Field(
        default="AI agent for technology stack recommendation based on architecture analysis",
        description="Agent description"
    )
    
    # A2A Configuration
    a2a_server_host: str = Field(default="localhost", description="A2A server host")
    a2a_server_port: int = Field(default=8080, description="A2A server port") 
    a2a_auth_type: str = Field(default="OAuth2", description="Authentication type")
    a2a_auth_token: Optional[str] = Field(None, description="Authentication token", alias="A2A_AUTH_TOKEN")
    
    # Unified LLM Configuration (Primary)
    llm_api_key: Optional[str] = Field(default=None, description="Unified LLM API key", alias="LLM_API_KEY")
    llm_provider: Optional[str] = Field(default=None, description="LLM provider", alias="LLM_PROVIDER")
    llm_model: Optional[str] = Field(default=None, description="LLM model", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM temperature", alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, description="Maximum tokens", alias="LLM_MAX_TOKENS")
    llm_timeout: int = Field(default=30, description="LLM timeout", alias="LLM_TIMEOUT")
    
    # Legacy LLM Configuration (Backward Compatibility)
    openai_api_key: Optional[str] = Field(default=None, description="Legacy OpenAI API key", alias="OPENAI_API_KEY")
    openai_model: Optional[str] = Field(default=None, description="Legacy OpenAI model")
    openai_temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Legacy LLM temperature")
    openai_max_tokens: Optional[int] = Field(default=None, description="Legacy maximum tokens")
    
    # Computed properties for backward compatibility
    @property
    def effective_api_key(self) -> str:
        """Get effective API key (unified or legacy)"""
        return self.llm_api_key or self.openai_api_key or ""
    
    @property
    def effective_model(self) -> str:
        """Get effective model (unified or legacy)"""
        return self.llm_model or self.openai_model or "gpt-4"
    
    @property
    def effective_temperature(self) -> float:
        """Get effective temperature (unified or legacy)"""
        return self.llm_temperature if self.llm_temperature is not None else (self.openai_temperature or 0.3)
    
    @property
    def effective_max_tokens(self) -> int:
        """Get effective max tokens (unified or legacy)"""
        return self.llm_max_tokens if self.llm_max_tokens is not None else (self.openai_max_tokens or 2000)
    
    # Database Configuration  
    supabase_url: str = Field(..., description="Supabase URL", alias="SUPABASE_URL")
    supabase_key: str = Field(..., description="Supabase API key", alias="SUPABASE_KEY")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL", alias="REDIS_URL")
    redis_task_ttl: int = Field(default=3600, description="Task TTL in seconds")
    
    # pgvector Search Configuration
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")
    vector_search_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Vector similarity threshold")
    vector_search_limit: int = Field(default=5, description="Maximum search results")
    
    # Quality Assessment Configuration
    quality_thresholds: Dict[str, float] = Field(
        default={
            "min_overall_score": 0.7,
            "min_suitability": 0.6,
            "min_completeness": 0.7,
            "min_feasibility": 0.8,
            "min_scalability": 0.6,
            "min_maintainability": 0.6
        },
        description="Quality score thresholds"
    )
    
    # Stack Templates Configuration
    default_templates: List[str] = Field(
        default=[
            "web_application",
            "api_service",
            "data_pipeline",
            "mobile_backend",
            "microservices",
            "serverless"
        ],
        description="Available stack templates"
    )
    
    # Performance Configuration
    task_timeout: int = Field(default=300, description="Default task timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    concurrent_requests: int = Field(default=10, description="Maximum concurrent requests")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Knowledge Base Configuration
    knowledge_cache_ttl: int = Field(default=7200, description="Knowledge cache TTL in seconds")
    update_knowledge_interval: int = Field(default=86400, description="Knowledge update interval in seconds")
    
    @field_validator('quality_thresholds')
    @classmethod
    def validate_quality_thresholds(cls, v):
        """Validate all quality thresholds are between 0 and 1"""
        for key, value in v.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Quality threshold {key} must be between 0.0 and 1.0")
        return v
    
    @field_validator('openai_temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v is not None:
            return round(v, 2)
        return v
    
    @property
    def a2a_server_url(self) -> str:
        """Complete A2A server URL"""
        return f"http://{self.a2a_server_host}:{self.a2a_server_port}"
    
    @property
    def agent_card_data(self) -> Dict:
        """Agent card data for A2A registration"""
        return {
            "name": self.agent_name,
            "description": self.agent_description,
            "url": f"{self.a2a_server_url}/a2a",
            "version": self.agent_version,
            "skills": [
                {
                    "id": "stack-recommendation",
                    "description": "Analyzes architecture and recommends technology stack",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "architecture_context": {"type": "object"},
                            "requirements": {"type": "object"},
                            "constraints": {"type": "object"}
                        },
                        "required": ["architecture_context"]
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "recommendation": {"type": "object"},
                            "quality_score": {"type": "object"},
                            "rationale": {"type": "string"}
                        }
                    }
                }
            ],
            "authentication": {
                "type": self.a2a_auth_type,
                "required": bool(self.a2a_auth_token)
            }
        }
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True
    )


class StackTemplatesConfig(BaseSettings):
    """Stack templates configuration"""
    
    # Template categories
    web_templates: List[str] = Field(
        default=[
            "react_fastapi_postgres",
            "vue_django_mysql", 
            "nextjs_express_mongodb",
            "svelte_flask_sqlite"
        ],
        description="Web application templates"
    )
    
    api_templates: List[str] = Field(
        default=[
            "fastapi_postgres_redis",
            "express_postgres_redis",
            "django_postgres_celery",
            "golang_gin_postgres"
        ],
        description="API service templates"
    )
    
    microservice_templates: List[str] = Field(
        default=[
            "kubernetes_istio",
            "docker_compose",
            "serverless_aws",
            "serverless_azure"
        ],
        description="Microservices templates"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True
    )
        


# Global settings instance
settings = StackRecommenderSettings()
template_config = StackTemplatesConfig()