import os
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, BaseModel, ConfigDict
import logging

class Settings(BaseSettings):
    """
    DevStrategist AI application configuration
    Manages all environment variables with validation and type safety
    """

    # Basic application settings
    APP_NAME: str = "DevStrategist AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

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
        repr=False,
        description="Supabase API key"
    )
    
    @property
    def DATABASE_URL(self) -> str:
        return self.SUPABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    # Multi-Provider LLM Configuration (Primary)
    LLM_API_KEY: str = Field(
        ..., 
        repr=False,
        description="LLM API key (auto-detects provider from key format)"
    )
    LLM_PROVIDER: Optional[str] = Field(
        default=None,
        description="Explicit LLM provider (openai|anthropic|perplexity|google|fallback)"
    )
    LLM_MODEL: Optional[str] = Field(
        default=None,
        description="LLM model (auto-selects default if not specified)"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.2,
        ge=0.0, le=2.0,
        description="LLM temperature for all agents"
    )
    LLM_MAX_TOKENS: int = Field(
        default=2000,
        description="Maximum tokens for LLM responses"
    )
    LLM_TIMEOUT: int = Field(
        default=30,
        description="LLM request timeout in seconds"
    )
    
    # Legacy LLM Configuration (Backward Compatibility)
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        repr=False,
        description="Legacy OpenAI API key (mapped from LLM_API_KEY)"
    )
    OPENAI_MODEL: Optional[str] = Field(
        default=None,
        description="Legacy OpenAI model (mapped from LLM_MODEL)"
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model for vector search"
    )
    
    # Backward compatibility properties
    @property
    def OPENAI_API_KEY_COMPAT(self) -> str:
        """Backward compatibility: return LLM_API_KEY as OPENAI_API_KEY"""
        return self.OPENAI_API_KEY or self.LLM_API_KEY
    
    @property  
    def OPENAI_MODEL_COMPAT(self) -> str:
        """Backward compatibility: return LLM_MODEL as OPENAI_MODEL"""
        return self.OPENAI_MODEL or self.LLM_MODEL or "gpt-3.5-turbo"

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
        repr=False,
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
    
    # Agent endpoints for A2A communication
    REQUIREMENT_ANALYZER_URL: str = Field(
        default="http://localhost:8000",
        description="Requirement Analyzer agent endpoint"
    )
    ARCHITECT_AGENT_URL: str = Field(
        default="http://localhost:8001",
        description="Architect Agent endpoint"
    )
    STACK_RECOMMENDER_URL: str = Field(
        default="http://localhost:8002",
        description="Stack Recommender agent endpoint"
    )
    DOCUMENT_AGENT_URL: str = Field(
        default="http://localhost:8003",
        description="Document Agent endpoint"
    )
    
    # Agent-specific settings
    AGENT_LLM_TEMPERATURE: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="LLM temperature for agent responses"
    )
    AGENT_MAX_RETRIES: int = Field(
        default=3,
        description="Maximum retries for agent operations"
    )
    AGENT_QUALITY_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum quality score threshold for agent outputs"
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
        repr=False,
        description="GitHub OAuth client secret"
    )

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

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
    
    @field_validator("AGENT_LLM_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("AGENT_LLM_TEMPERATURE must be between 0.0 and 1.0")
        return v
    
    @field_validator("AGENT_QUALITY_THRESHOLD")
    @classmethod
    def validate_quality_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("AGENT_QUALITY_THRESHOLD must be between 0.0 and 1.0")
        return v
    
    @field_validator('LLM_API_KEY')
    @classmethod
    def validate_llm_api_key(cls, v):
        if not v:
            raise ValueError("LLM_API_KEY is required")
        
        # Import here to avoid circular imports
        try:
            from .llm_providers import LLMProviderFactory
            # Validate format based on provider detection
            provider_type = LLMProviderFactory.detect_provider_from_key(v)
            if provider_type.value == "fallback" and not v.startswith("mock"):
                logging.warning(f"API key format not recognized, using fallback provider")
        except ImportError:
            # If llm_providers not available, skip validation
            pass
        
        return v
    
    @field_validator('LLM_PROVIDER')
    @classmethod 
    def validate_llm_provider(cls, v):
        if v:
            valid_providers = ["openai", "anthropic", "perplexity", "google", "fallback"]
            if v.lower() not in valid_providers:
                raise ValueError(f"Invalid LLM provider: {v}. Must be one of: {valid_providers}")
        return v
    
    @field_validator('LLM_TEMPERATURE')
    @classmethod
    def validate_llm_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("LLM_TEMPERATURE must be between 0.0 and 2.0")
        return round(v, 2)

class AgentConfig(BaseModel):
    """
    Standardized configuration for individual agents with unified LLM support
    """
    agent_id: str
    agent_name: str
    endpoint_url: str
    
    # Unified LLM Configuration (Primary)
    llm_api_key: str
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2000
    llm_timeout: int = 30
    
    # Legacy Configuration (Backward Compatibility)
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    
    # Agent-specific settings
    temperature: float = 0.2  # Legacy alias for llm_temperature
    timeout_minutes: int = 5
    max_retries: int = 3
    quality_threshold: float = 0.7
    
    # Backward compatibility properties
    @property
    def effective_api_key(self) -> str:
        """Get the effective API key (unified or legacy)"""
        return self.llm_api_key
    
    @property
    def effective_model(self) -> str:
        """Get the effective model (unified or legacy)"""
        return self.llm_model or self.openai_model or "gpt-3.5-turbo"
    
    @property
    def effective_temperature(self) -> float:
        """Get the effective temperature (unified)"""
        return self.llm_temperature
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration for provider creation"""
        return {
            "api_key": self.effective_api_key,
            "provider_name": self.llm_provider,
            "model": self.effective_model,
            "temperature": self.effective_temperature,
            "max_tokens": self.llm_max_tokens,
            "timeout": self.llm_timeout
        }
    
    def get_legacy_config(self) -> Dict[str, Any]:
        """Get legacy configuration format for backward compatibility"""
        return {
            "openai_api_key": self.effective_api_key,
            "openai_model": self.effective_model,
            "temperature": self.effective_temperature,
            "timeout_minutes": self.timeout_minutes,
            "max_retries": self.max_retries,
            "quality_threshold": self.quality_threshold
        }
    
    model_config = ConfigDict(frozen=True)


class AgentConfigManager:
    """
    Enhanced configuration manager with unified LLM provider support
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._agent_configs = {}
        self._llm_manager = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_llm_manager(self):
        """Get or create unified LLM manager"""
        if not self._llm_manager:
            from .llm_providers import DevStrategistLLMManager
            self._llm_manager = DevStrategistLLMManager(
                api_key=self.settings.LLM_API_KEY,
                provider_name=self.settings.LLM_PROVIDER,
                model=self.settings.LLM_MODEL,
                temperature=self.settings.LLM_TEMPERATURE,
                max_tokens=self.settings.LLM_MAX_TOKENS,
                timeout=self.settings.LLM_TIMEOUT
            )
            self.logger.info("Unified LLM manager initialized")
        return self._llm_manager
    
    async def get_agent_config(self, agent_id: str) -> AgentConfig:
        """
        Get configuration for a specific agent with LLM provider support
        """
        if agent_id not in self._agent_configs:
            self._agent_configs[agent_id] = await self._create_agent_config(agent_id)
        return self._agent_configs[agent_id]
    
    async def _create_agent_config(self, agent_id: str) -> AgentConfig:
        """
        Create agent configuration with unified LLM provider system
        """
        agent_configs = {
            "requirement-analyzer": {
                "agent_name": "Requirement Analyzer",
                "endpoint_url": self.settings.REQUIREMENT_ANALYZER_URL
            },
            "architect-agent": {
                "agent_name": "Architecture Design Agent",
                "endpoint_url": self.settings.ARCHITECT_AGENT_URL
            },
            "stack-recommender-agent": {
                "agent_name": "Stack Recommendation Agent",
                "endpoint_url": self.settings.STACK_RECOMMENDER_URL
            },
            "document-agent": {
                "agent_name": "Documentation Generation Agent",
                "endpoint_url": self.settings.DOCUMENT_AGENT_URL
            }
        }
        
        if agent_id not in agent_configs:
            raise ValueError(f"Unknown agent_id: {agent_id}")
        
        config_data = agent_configs[agent_id]
        
        return AgentConfig(
            agent_id=agent_id,
            agent_name=config_data["agent_name"],
            endpoint_url=config_data["endpoint_url"],
            # Unified LLM configuration
            llm_api_key=self.settings.LLM_API_KEY,
            llm_provider=self.settings.LLM_PROVIDER,
            llm_model=self.settings.LLM_MODEL,
            llm_temperature=self.settings.LLM_TEMPERATURE,
            llm_max_tokens=self.settings.LLM_MAX_TOKENS,
            llm_timeout=self.settings.LLM_TIMEOUT,
            # Backward compatibility
            openai_api_key=self.settings.OPENAI_API_KEY_COMPAT,
            openai_model=self.settings.OPENAI_MODEL_COMPAT,
            # Agent settings  
            temperature=self.settings.LLM_TEMPERATURE,  # Use unified temperature
            timeout_minutes=self.settings.AGENT_TIMEOUT_MINUTES,
            max_retries=self.settings.AGENT_MAX_RETRIES,
            quality_threshold=self.settings.AGENT_QUALITY_THRESHOLD
        )
    
    def get_agent_endpoints(self) -> Dict[str, str]:
        """
        Get all agent endpoints for A2A communication
        """
        return {
            "architect": self.settings.ARCHITECT_AGENT_URL,
            "stack_recommender": self.settings.STACK_RECOMMENDER_URL,
            "documenter": self.settings.DOCUMENT_AGENT_URL
        }
    
    def get_common_config(self) -> Dict[str, Any]:
        """
        Get common configuration with unified LLM provider support
        """
        return {
            # Unified LLM configuration
            "llm_api_key": self.settings.LLM_API_KEY,
            "llm_provider": self.settings.LLM_PROVIDER,
            "llm_model": self.settings.LLM_MODEL,
            "llm_temperature": self.settings.LLM_TEMPERATURE,
            "llm_max_tokens": self.settings.LLM_MAX_TOKENS,
            "llm_timeout": self.settings.LLM_TIMEOUT,
            # Backward compatibility
            "openai_api_key": self.settings.OPENAI_API_KEY_COMPAT,
            "openai_model": self.settings.OPENAI_MODEL_COMPAT,
            # Agent settings
            "temperature": self.settings.LLM_TEMPERATURE,
            "timeout_minutes": self.settings.AGENT_TIMEOUT_MINUTES,
            "max_retries": self.settings.AGENT_MAX_RETRIES,
            "quality_threshold": self.settings.AGENT_QUALITY_THRESHOLD,
            # Infrastructure
            "database_url": self.settings.DATABASE_URL,
            "redis_url": self.settings.REDIS_URL
        }
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """Get current LLM provider information"""
        llm_manager = await self.get_llm_manager()
        return llm_manager.get_provider_info()
    
    def get_legacy_config(self, agent_id: str) -> Dict[str, Any]:
        """
        Get legacy configuration format for backward compatibility
        """
        return {
            "openai_api_key": self.settings.OPENAI_API_KEY_COMPAT,
            "openai_model": self.settings.OPENAI_MODEL_COMPAT,
            "temperature": self.settings.LLM_TEMPERATURE,
            "timeout_minutes": self.settings.AGENT_TIMEOUT_MINUTES,
            "max_retries": self.settings.AGENT_MAX_RETRIES,
            "quality_threshold": self.settings.AGENT_QUALITY_THRESHOLD
        }


# Global settings instance
settings = Settings()

# Global agent config manager
agent_config_manager = AgentConfigManager(settings)