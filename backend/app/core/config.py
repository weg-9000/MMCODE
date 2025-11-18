from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import re

class Settings(BaseSettings):
    """
    DevStrategist AI application configuration
    Manages all environment variables with validation and type safety
    """

    # Basic application settings
    APP_NAME: str = "DevStrategist AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # API settings
    API_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://devstrategist.ai"],
        description="Allowed CORS origins"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "*.render.com"],
        description="Allowed host list"
    )

    # Database - Supabase PostgreSQL
    SUPABASE_URL: str = Field(
        ...,
        description="Supabase PostgreSQL connection URL"
    )
    SUPABASE_KEY: str = Field(
        ...,
        description="Supabase API key"
    )
    
    @property
    def DATABASE_URL(self) -> str:
        return self.SUPABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    # LLM Configuration
    OPENAI_API_KEY: str = Field(
        ...,
        description="OpenAI API key for LangChain"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model for agents"
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model for vector search"
    )

    # Redis for agent state management
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )

    # LangChain settings
    LANGCHAIN_TRACING: bool = Field(
        default=True,
        description="Enable LangChain tracing"
    )
    LANGCHAIN_PROJECT: str = Field(
        default="devstrategist-ai",
        description="LangChain project name"
    )

    # Security
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Secret key for session encryption"
    )

    # Agent configuration
    AGENT_TIMEOUT_MINUTES: int = Field(
        default=5,
        description="Agent execution timeout in minutes"
    )
    MAX_CONCURRENT_AGENTS: int = Field(
        default=4,
        description="Maximum concurrent agents"
    )

    # File upload limits
    MAX_UPLOAD_SIZE: int = Field(
        default=5 * 1024 * 1024,  # 5MB
        description="Maximum file upload size in bytes"
    )

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        description="API rate limit per minute"
    )

    # GitHub integration
    GITHUB_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="GitHub OAuth client ID"
    )
    GITHUB_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="GitHub OAuth client secret"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

settings = Settings()