"""
Configuration settings for Architect Agent.
Manages environment variables, default values, and validation.
"""
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
from pydantic import Field, validator
import os

class ArchitectAgentSettings(BaseSettings):
    """ArchitectAgent configuration"""
    
    # Agent Identity
    agent_name: str = Field(default="architect-agent", description="Agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")
    agent_description: str = Field(
        default="AI agent for system architecture design and pattern identification",
        description="Agent description"
    )
    
    # A2A Configuration
    a2a_server_host: str = Field(default="localhost", description="A2A server host")
    a2a_server_port: int = Field(default=8081, description="A2A server port") 
    a2a_auth_type: str = Field(default="OAuth2", description="Authentication type")
    a2a_auth_token: Optional[str] = Field(None, description="Authentication token", env="A2A_AUTH_TOKEN")
    
    # Unified LLM Configuration (Primary)
    llm_api_key: Optional[str] = Field(default=None, description="Unified LLM API key", env="LLM_API_KEY")
    llm_provider: Optional[str] = Field(default=None, description="LLM provider", env="LLM_PROVIDER")
    llm_model: Optional[str] = Field(default=None, description="LLM model", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="LLM temperature", env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=3000, description="Maximum tokens", env="LLM_MAX_TOKENS")
    llm_timeout: int = Field(default=45, description="LLM timeout", env="LLM_TIMEOUT")
    
    # Legacy LLM Configuration (Backward Compatibility)
    openai_api_key: Optional[str] = Field(default=None, description="Legacy OpenAI API key", env="OPENAI_API_KEY")
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
        return self.llm_model or self.openai_model or "gpt-4-turbo"
    
    @property
    def effective_temperature(self) -> float:
        """Get effective temperature (unified or legacy)"""
        return self.llm_temperature if self.llm_temperature is not None else (self.openai_temperature or 0.2)
    
    @property
    def effective_max_tokens(self) -> int:
        """Get effective max tokens (unified or legacy)"""
        return self.llm_max_tokens if self.llm_max_tokens is not None else (self.openai_max_tokens or 3000)
    
    # Database Configuration  
    supabase_url: str = Field(..., description="Supabase URL", env="SUPABASE_URL")
    supabase_key: str = Field(..., description="Supabase API key", env="SUPABASE_KEY")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL", env="REDIS_URL")
    redis_task_ttl: int = Field(default=3600, description="Task TTL in seconds")
    
    # pgvector Search Configuration
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")
    vector_search_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="Vector similarity threshold")
    
    # Quality Assessment Configuration
    quality_thresholds: Dict[str, float] = Field(
        default={
            "min_overall_score": 0.75,
            "min_structural_integrity": 0.7,
            "min_scalability_score": 0.6,
            "min_security_score": 0.7,
            "min_reliability_score": 0.6
        },
        description="Quality score thresholds"
    )
    
    # Architecture Patterns Configuration
    supported_patterns: List[str] = Field(
        default=[
            "microservices",
            "monolithic",
            "serverless",
            "event_driven",
            "layered",
            "soa"
        ],
        description="Supported architecture patterns"
    )
    
    # Performance Configuration
    task_timeout: int = Field(default=300, description="Default task timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    concurrent_requests: int = Field(default=5, description="Maximum concurrent requests")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    log_level: str = Field(default="INFO", description="Logging level")
    
    @validator('quality_thresholds')
    def validate_quality_thresholds(cls, v):
        """Validate all quality thresholds are between 0 and 1"""
        for key, value in v.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Quality threshold {key} must be between 0.0 and 1.0")
        return v
    
    @validator('openai_temperature')
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
                    "id": "architecture-design",
                    "description": "Designs system architecture and identifies patterns",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "analysis_result": {"type": "object"},
                            "constraints": {"type": "object"}
                        },
                        "required": ["analysis_result"]
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "architecture_design": {"type": "object"},
                            "diagrams": {"type": "array"},
                            "decisions": {"type": "array"}
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
        extra = "ignore"


# Global settings instance
settings = ArchitectAgentSettings()
