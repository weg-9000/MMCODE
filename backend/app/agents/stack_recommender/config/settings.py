"""
Configuration settings for StackRecommender agent.
Manages environment variables, default values, and validation.
"""

from typing import Dict, List, Optional
from pydantic import BaseSettings, Field, validator
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
    a2a_auth_token: Optional[str] = Field(None, description="Authentication token", env="A2A_AUTH_TOKEN")
    
    # LLM Configuration
    openai_api_key: str = Field(..., description="OpenAI API key", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", description="OpenAI model name")
    openai_temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM temperature")
    openai_max_tokens: int = Field(default=2000, description="Maximum tokens for LLM response")
    
    # Database Configuration  
    supabase_url: str = Field(..., description="Supabase URL", env="SUPABASE_URL")
    supabase_key: str = Field(..., description="Supabase API key", env="SUPABASE_KEY")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL", env="REDIS_URL")
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
    
    @validator('quality_thresholds')
    def validate_quality_thresholds(cls, v):
        """Validate all quality thresholds are between 0 and 1"""
        for key, value in v.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Quality threshold {key} must be between 0.0 and 1.0")
        return v
    
    @validator('openai_temperature')
    def validate_temperature(cls, v):
        return round(v, 2)
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


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
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = StackRecommenderSettings()
template_config = StackTemplatesConfig()