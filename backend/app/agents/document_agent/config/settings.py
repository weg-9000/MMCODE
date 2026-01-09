"""
Configuration settings for Document Agent.
Manages environment variables, default values, and validation.
"""
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict
import os

class DocumentAgentSettings(BaseSettings):
    """DocumentAgent configuration"""
    
    # Agent Identity
    agent_name: str = Field(default="document-agent", description="Agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")
    agent_description: str = Field(
        default="AI agent for generating comprehensive technical documentation",
        description="Agent description"
    )
    
    # A2A Configuration
    a2a_server_host: str = Field(default="localhost", description="A2A server host")
    a2a_server_port: int = Field(default=8083, description="A2A server port") 
    a2a_auth_type: str = Field(default="OAuth2", description="Authentication type")
    a2a_auth_token: Optional[str] = Field(None, description="Authentication token", alias="A2A_AUTH_TOKEN")
    
    # Unified LLM Configuration (Primary)
    llm_api_key: Optional[str] = Field(default=None, description="Unified LLM API key", alias="LLM_API_KEY")
    llm_provider: Optional[str] = Field(default=None, description="LLM provider", alias="LLM_PROVIDER")
    llm_model: Optional[str] = Field(default=None, description="LLM model", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM temperature", alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=4000, description="Maximum tokens", alias="LLM_MAX_TOKENS")
    llm_timeout: int = Field(default=60, description="LLM timeout", alias="LLM_TIMEOUT")
    
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
        return self.llm_model or self.openai_model or "gpt-3.5-turbo"
    
    @property
    def effective_temperature(self) -> float:
        """Get effective temperature (unified or legacy)"""
        return self.llm_temperature if self.llm_temperature is not None else (self.openai_temperature or 0.3)
    
    @property
    def effective_max_tokens(self) -> int:
        """Get effective max tokens (unified or legacy)"""
        return self.llm_max_tokens if self.llm_max_tokens is not None else (self.openai_max_tokens or 4000)
    
    # Database Configuration  
    supabase_url: str = Field(..., description="Supabase URL", alias="SUPABASE_URL")
    supabase_key: str = Field(..., description="Supabase API key", alias="SUPABASE_KEY")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL", alias="REDIS_URL")
    redis_task_ttl: int = Field(default=3600, description="Task TTL in seconds")
    
    # Documentation Configuration
    output_directory: str = Field(default="./artifacts/docs", description="Documentation output path")
    default_language: str = Field(default="ko", description="Default language code")
    include_diagrams: bool = Field(default=True, description="Include diagrams in docs")
    
    # Supported Formats
    supported_formats: List[str] = Field(
        default=["markdown", "pdf", "html", "openapi_json", "erd_mermaid"],
        description="Supported output formats"
    )
    
    # Performance Configuration
    task_timeout: int = Field(default=300, description="Default task timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    concurrent_requests: int = Field(default=5, description="Maximum concurrent requests")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    log_level: str = Field(default="INFO", description="Logging level")
    
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
                    "id": "documentation-generation",
                    "description": "Generates technical documentation",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "context": {"type": "object"},
                            "document_types": {"type": "array"}
                        },
                        "required": ["context"]
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "documents": {"type": "array"},
                            "files": {"type": "array"}
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


# Global settings instance
settings = DocumentAgentSettings()


def get_settings() -> DocumentAgentSettings:
    """Get the settings instance"""
    return settings
