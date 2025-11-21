"""
Unified LLM Provider System for MMCODE DevStrategist AI
Multi-provider LLM abstraction with auto-detection and fallback support
"""

import os
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, List
from dataclasses import dataclass
from enum import Enum
import logging

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.language_models.llms import BaseLLM
from langchain_core.language_models.chat_models import BaseChatModel


class ProviderType(Enum):
    """Supported LLM provider types"""
    OPENAI = "openai"
    PERPLEXITY = "perplexity"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    FALLBACK = "fallback"


@dataclass
class ProviderConfig:
    """Unified provider configuration"""
    provider_type: ProviderType
    api_key: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 2000
    timeout: int = 30
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    extra_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class BaseLLMProvider(ABC):
    """Base LLM provider interface"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._llm_instance: Optional[BaseChatModel] = None
    
    @abstractmethod
    def get_provider_type(self) -> ProviderType:
        """Return provider type"""
        pass
    
    @abstractmethod
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key format"""
        pass
    
    @abstractmethod
    def get_default_models(self) -> List[str]:
        """Return list of supported default models"""
        pass
    
    @abstractmethod
    async def create_llm_instance(self) -> BaseChatModel:
        """Create LLM instance"""
        pass
    
    async def initialize(self) -> bool:
        """Initialize provider"""
        try:
            if not self.validate_api_key(self.config.api_key):
                self.logger.error(f"Invalid API key format for {self.get_provider_type().value}")
                return False
            
            self._llm_instance = await self.create_llm_instance()
            self.logger.info(f"{self.get_provider_type().value} provider initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.get_provider_type().value} provider: {e}")
            return False
    
    def get_llm(self) -> Optional[BaseChatModel]:
        """Return initialized LLM instance"""
        return self._llm_instance
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Return provider information"""
        return {
            "provider": self.get_provider_type().value,
            "model": self.config.model,
            "api_key_valid": self.validate_api_key(self.config.api_key),
            "initialized": self._llm_instance is not None,
            "supported_models": self.get_default_models(),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation"""
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    def validate_api_key(self, api_key: str) -> bool:
        """OpenAI API key format: sk-..."""
        return bool(api_key and api_key.startswith("sk-") and len(api_key) > 20)
    
    def get_default_models(self) -> List[str]:
        return [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k", 
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-4o",
            "gpt-4o-mini",
            "o1-pro"
        ]
    
    async def create_llm_instance(self) -> BaseChatModel:
        """Create OpenAI ChatOpenAI instance"""
        return ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            request_timeout=self.config.timeout,
            api_key=self.config.api_key,
            **self.config.extra_params
        )


class PerplexityProvider(BaseLLMProvider):
    """Perplexity provider implementation"""
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.PERPLEXITY
    
    def validate_api_key(self, api_key: str) -> bool:
        """Perplexity API key format: pplx-..."""
        return bool(api_key and api_key.startswith("pplx-") and len(api_key) > 20)
    
    def get_default_models(self) -> List[str]:
        return [
            "sonar",
            "sonar-reasoning",
            "sonar-pro", 
            "sonar-reasoning-pro",
            "r1-1776"
        ]
    
    async def create_llm_instance(self) -> BaseChatModel:
        """Create Perplexity-compatible OpenAI instance"""
        # Perplexity API doesn't support stop parameter
        filtered_params = {k: v for k, v in self.config.extra_params.items() if k != 'stop'}
        
        # Custom ChatOpenAI wrapper for Perplexity compatibility
        class PerplexityChatOpenAI(ChatOpenAI):
            def _generate(self, messages, stop=None, **kwargs):
                return super()._generate(messages, stop=None, **kwargs)
            
            async def _agenerate(self, messages, stop=None, **kwargs):
                return await super()._agenerate(messages, stop=None, **kwargs)
            
            async def _astream(self, messages, stop=None, **kwargs):
                async for chunk in super()._astream(messages, stop=None, **kwargs):
                    yield chunk
        
        return PerplexityChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            request_timeout=self.config.timeout,
            api_key=self.config.api_key,
            base_url="https://api.perplexity.ai",
            **filtered_params
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation"""
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    def validate_api_key(self, api_key: str) -> bool:
        """Anthropic API key format: sk-ant-..."""
        return bool(api_key and api_key.startswith("sk-ant-") and len(api_key) > 20)
    
    def get_default_models(self) -> List[str]:
        return [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-3-7-sonnet",
            "claude-3-5-haiku",
            "claude-3-5-sonnet-20241022"
        ]
    
    async def create_llm_instance(self) -> BaseChatModel:
        """Create Anthropic instance"""
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                api_key=self.config.api_key,
                **self.config.extra_params
            )
        except ImportError:
            self.logger.warning("langchain_anthropic not installed, using fallback")
            raise ImportError("Please install: pip install langchain-anthropic")


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider implementation"""
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.GOOGLE
    
    def validate_api_key(self, api_key: str) -> bool:
        """Google API key format: AIza..."""
        return bool(api_key and api_key.startswith("AIza") and len(api_key) > 20)
    
    def get_default_models(self) -> List[str]:
        return [
            "gemini-2.0-flash-001",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-pro",
            "gemini-pro-vision"
        ]
    
    async def create_llm_instance(self) -> BaseChatModel:
        """Create Google Gemini instance"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=self.config.model,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                google_api_key=self.config.api_key,
                **self.config.extra_params
            )
        except ImportError:
            self.logger.warning("langchain_google_genai not installed, using fallback")
            raise ImportError("Please install: pip install langchain-google-genai")


class FallbackProvider(BaseLLMProvider):
    """Fallback provider for testing (Mock LLM)"""
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.FALLBACK
    
    def validate_api_key(self, api_key: str) -> bool:
        """Fallback mode is always valid"""
        return True
    
    def get_default_models(self) -> List[str]:
        return ["mock-model"]
    
    async def create_llm_instance(self) -> BaseChatModel:
        """Create Mock LLM instance for testing"""
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.messages import AIMessage
        
        # Mock responses for testing
        responses = [
            AIMessage(content="This is a mock response from the DevStrategist AI fallback provider."),
            AIMessage(content="Fallback mode is active. Please configure a valid API key for production use."),
            AIMessage(content="Mock LLM response for MMCODE testing purposes.")
        ]
        
        return FakeMessagesListChatModel(responses=responses)


class LLMProviderFactory:
    """LLM provider factory for auto-detection and creation"""
    
    _providers: Dict[ProviderType, Type[BaseLLMProvider]] = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.PERPLEXITY: PerplexityProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.GOOGLE: GoogleProvider,
        ProviderType.FALLBACK: FallbackProvider
    }
    
    @classmethod
    def detect_provider_from_key(cls, api_key: str) -> ProviderType:
        """Auto-detect provider from API key format"""
        if not api_key:
            return ProviderType.FALLBACK
        
        # API key pattern matching
        patterns = {
            ProviderType.OPENAI: r"^sk-[A-Za-z0-9\-_]{40,}$",
            ProviderType.PERPLEXITY: r"^pplx-[A-Za-z0-9\-_]{40,}$", 
            ProviderType.ANTHROPIC: r"^sk-ant-[A-Za-z0-9\-_]{40,}$",
            ProviderType.GOOGLE: r"^AIza[A-Za-z0-9\-_]{35,}$"
        }
        
        for provider_type, pattern in patterns.items():
            if re.match(pattern, api_key):
                return provider_type
        
        return ProviderType.FALLBACK
    
    @classmethod
    def get_provider_from_config(cls, provider_name: str) -> ProviderType:
        """Get provider type from config name"""
        provider_map = {
            "openai": ProviderType.OPENAI,
            "perplexity": ProviderType.PERPLEXITY,
            "anthropic": ProviderType.ANTHROPIC,
            "claude": ProviderType.ANTHROPIC,
            "google": ProviderType.GOOGLE,
            "gemini": ProviderType.GOOGLE,
            "fallback": ProviderType.FALLBACK,
            "mock": ProviderType.FALLBACK
        }
        
        return provider_map.get(provider_name.lower(), ProviderType.FALLBACK)
    
    @classmethod
    def create_provider(cls, config: ProviderConfig) -> BaseLLMProvider:
        """Create provider instance"""
        provider_class = cls._providers.get(config.provider_type, FallbackProvider)
        return provider_class(config)
    
    @classmethod
    def create_from_env(cls, 
                       api_key: str,
                       provider_name: Optional[str] = None,
                       model: Optional[str] = None,
                       **kwargs) -> BaseLLMProvider:
        """Create provider from environment configuration"""
        
        # Determine provider type (explicit setting first, then auto-detection)
        if provider_name:
            provider_type = cls.get_provider_from_config(provider_name)
        else:
            provider_type = cls.detect_provider_from_key(api_key)
        
        # Set default model
        if not model:
            temp_provider = cls._providers[provider_type](
                ProviderConfig(provider_type, api_key, "temp")
            )
            default_models = temp_provider.get_default_models()
            model = default_models[0] if default_models else "default-model"
        
        # Create configuration
        config = ProviderConfig(
            provider_type=provider_type,
            api_key=api_key,
            model=model,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 2000),
            timeout=kwargs.get("timeout", 30),
            base_url=kwargs.get("base_url"),
            api_version=kwargs.get("api_version"),
            extra_params=kwargs.get("extra_params", {})
        )
        
        return cls.create_provider(config)
    
    @classmethod
    def list_available_providers(cls) -> List[str]:
        """List available provider names"""
        return [provider.value for provider in cls._providers.keys()]


class DevStrategistLLMManager:
    """Central LLM management for DevStrategist AI agents"""
    
    def __init__(self, api_key: str, provider_name: Optional[str] = None, 
                 model: Optional[str] = None, **config_kwargs):
        self.api_key = api_key
        self.provider_name = provider_name
        self.model = model
        self.config_kwargs = config_kwargs
        self._provider: Optional[BaseLLMProvider] = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_llm_provider(self) -> BaseLLMProvider:
        """Get initialized LLM provider"""
        if not self._provider:
            self._provider = LLMProviderFactory.create_from_env(
                api_key=self.api_key,
                provider_name=self.provider_name,
                model=self.model,
                **self.config_kwargs
            )
            await self._provider.initialize()
            
            # Log provider info
            info = self._provider.get_provider_info()
            self.logger.info(f"LLM Provider initialized: {info['provider']} with model {info['model']}")
        
        return self._provider
    
    async def get_llm_instance(self) -> BaseChatModel:
        """Get LLM instance for direct use"""
        provider = await self.get_llm_provider()
        return provider.get_llm()
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        if self._provider:
            return self._provider.get_provider_info()
        else:
            # Detect provider without initializing
            detected_type = LLMProviderFactory.detect_provider_from_key(self.api_key)
            return {
                "provider": detected_type.value,
                "model": self.model,
                "initialized": False,
                "detected_from_key": True
            }


# Convenience functions for MMCODE integration
def create_devstrategist_llm_manager(settings_obj) -> DevStrategistLLMManager:
    """Create LLM manager from MMCODE settings"""
    return DevStrategistLLMManager(
        api_key=getattr(settings_obj, 'LLM_API_KEY', getattr(settings_obj, 'OPENAI_API_KEY', '')),
        provider_name=getattr(settings_obj, 'LLM_PROVIDER', None),
        model=getattr(settings_obj, 'LLM_MODEL', None),
        temperature=getattr(settings_obj, 'LLM_TEMPERATURE', 0.2),
        max_tokens=getattr(settings_obj, 'LLM_MAX_TOKENS', 2000),
        timeout=getattr(settings_obj, 'LLM_TIMEOUT', 30)
    )


def detect_current_provider() -> str:
    """Detect current provider from environment"""
    api_key = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    provider_type = LLMProviderFactory.detect_provider_from_key(api_key)
    return provider_type.value