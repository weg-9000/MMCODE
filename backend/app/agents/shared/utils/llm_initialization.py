"""
Unified LLM Initialization Utilities for All Agents

This module provides a centralized, consistent approach to LLM initialization
across all agents in the MMCODE system. It implements a 3-level fallback chain:

1. Modern Unified Provider (DevStrategistLLMManager)
2. Legacy OpenAI Direct Initialization
3. Ultimate Fallback with Defaults

Usage:
    from app.agents.shared.utils.llm_initialization import initialize_llm_sync

    class MyEngine:
        def __init__(self, config: Dict[str, Any]):
            self.llm = initialize_llm_sync(config, default_temperature=0.1)
"""

from typing import Dict, Any, Optional, Union
import asyncio
import logging

from langchain_openai import ChatOpenAI
from langchain_core.language_models.base import BaseLanguageModel

logger = logging.getLogger(__name__)


def initialize_llm_sync(
    config: Union[Dict[str, Any], Any],
    default_model: str = "gpt-3.5-turbo",
    default_temperature: float = 0.1
) -> ChatOpenAI:
    """
    Synchronous LLM initialization with 3-level fallback chain.

    This function handles both dict-based config and object-based config
    (like AgentConfig) with method checking for backward compatibility.

    Args:
        config: Configuration dict or AgentConfig object
        default_model: Default model name if not specified in config
        default_temperature: Default temperature if not specified

    Returns:
        Initialized ChatOpenAI instance

    Fallback Chain:
        1. Modern: DevStrategistLLMManager (if config has get_llm_config method)
        2. Legacy: Direct OpenAI initialization from config dict
        3. Ultimate: Basic OpenAI with defaults
    """
    try:
        # Level 1: Modern unified provider system
        if hasattr(config, 'get_llm_config') and callable(config.get_llm_config):
            return _initialize_with_unified_provider(config, default_temperature)

        # Level 2: Legacy dict-based configuration
        if isinstance(config, dict):
            return _initialize_with_legacy_config(config, default_model, default_temperature)

        # If config is an object but doesn't have get_llm_config, try to extract dict
        if hasattr(config, '__dict__'):
            config_dict = {k: v for k, v in config.__dict__.items() if not k.startswith('_')}
            return _initialize_with_legacy_config(config_dict, default_model, default_temperature)

    except Exception as e:
        logger.warning(f"LLM initialization failed, using ultimate fallback: {e}")

    # Level 3: Ultimate fallback
    return _get_fallback_llm(default_model, default_temperature)


def _initialize_with_unified_provider(
    config: Any,
    default_temperature: float
) -> ChatOpenAI:
    """Initialize LLM using the unified DevStrategistLLMManager."""
    from app.core.llm_providers import DevStrategistLLMManager

    llm_config = config.get_llm_config()
    llm_manager = DevStrategistLLMManager(**llm_config)

    # Get LLM instance - handle async in sync context
    try:
        loop = asyncio.get_running_loop()
        # If we're in an async context, we need to run in a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: asyncio.run(llm_manager.get_llm_instance())
            )
            llm = future.result(timeout=30)
    except RuntimeError:
        # No running event loop - safe to create one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        llm = loop.run_until_complete(llm_manager.get_llm_instance())

    logger.info("LLM initialized with unified provider system")
    return llm


def _initialize_with_legacy_config(
    config: Dict[str, Any],
    default_model: str,
    default_temperature: float
) -> ChatOpenAI:
    """Initialize LLM using legacy dict-based configuration."""
    # Try multiple key variations for backward compatibility
    model = (
        config.get("llm_model") or
        config.get("model") or
        config.get("openai_model") or
        default_model
    )

    temperature = (
        config.get("temperature") or
        config.get("llm_temperature") or
        default_temperature
    )

    api_key = (
        config.get("llm_api_key") or
        config.get("openai_api_key") or
        config.get("api_key")
    )

    if not api_key:
        raise ValueError("No API key found in configuration")

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        openai_api_key=api_key
    )

    logger.info(f"LLM initialized with legacy configuration: model={model}")
    return llm


def _get_fallback_llm(
    default_model: str,
    default_temperature: float
) -> ChatOpenAI:
    """Get ultimate fallback LLM with environment-based API key."""
    import os

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("No OPENAI_API_KEY environment variable found for fallback")
        raise ValueError("Cannot initialize LLM: No API key available")

    llm = ChatOpenAI(
        model=default_model,
        temperature=default_temperature,
        openai_api_key=api_key
    )

    logger.warning(f"LLM initialized with ultimate fallback: model={default_model}")
    return llm


async def initialize_llm_async(
    config: Union[Dict[str, Any], Any],
    default_model: str = "gpt-3.5-turbo",
    default_temperature: float = 0.1
) -> ChatOpenAI:
    """
    Async version of LLM initialization.

    Use this when you're already in an async context and need to
    initialize the LLM without blocking.

    Args:
        config: Configuration dict or AgentConfig object
        default_model: Default model name if not specified
        default_temperature: Default temperature if not specified

    Returns:
        Initialized ChatOpenAI instance
    """
    try:
        # Level 1: Modern unified provider system
        if hasattr(config, 'get_llm_config') and callable(config.get_llm_config):
            from app.core.llm_providers import DevStrategistLLMManager

            llm_config = config.get_llm_config()
            llm_manager = DevStrategistLLMManager(**llm_config)
            llm = await llm_manager.get_llm_instance()

            logger.info("LLM initialized with unified provider system (async)")
            return llm

        # Level 2 & 3: Fall back to sync initialization
        # (These don't benefit from async anyway)
        return initialize_llm_sync(config, default_model, default_temperature)

    except Exception as e:
        logger.warning(f"Async LLM initialization failed, using fallback: {e}")
        return _get_fallback_llm(default_model, default_temperature)


async def ensure_llm_instance(
    llm: Optional[ChatOpenAI],
    llm_manager: Optional[Any],
    fallback_settings: Optional[Dict[str, Any]] = None
) -> ChatOpenAI:
    """
    Lazy initialization helper for engines that use deferred LLM creation.

    This is useful for engines like StackAnalysisEngine that want to
    delay LLM initialization until first use.

    Args:
        llm: Existing LLM instance (may be None)
        llm_manager: LLM manager instance (may be None)
        fallback_settings: Dict with 'model', 'temperature', 'api_key' for fallback

    Returns:
        Initialized ChatOpenAI instance

    Example:
        class MyEngine:
            def __init__(self):
                self.llm = None
                self._llm_manager = create_manager()

            async def do_work(self):
                self.llm = await ensure_llm_instance(
                    self.llm,
                    self._llm_manager,
                    {'model': 'gpt-4', 'temperature': 0.2}
                )
                result = await self.llm.ainvoke(...)
    """
    if llm is not None:
        return llm

    if llm_manager is not None:
        try:
            llm = await llm_manager.get_llm_instance()
            logger.info("LLM initialized via lazy loading with manager")
            return llm
        except Exception as e:
            logger.warning(f"Failed to get LLM from manager: {e}")

    # Fallback to settings-based initialization
    if fallback_settings:
        model = fallback_settings.get('model', 'gpt-3.5-turbo')
        temperature = fallback_settings.get('temperature', 0.1)
        api_key = fallback_settings.get('api_key')

        if api_key:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=api_key
            )
            logger.info(f"LLM initialized via lazy loading with fallback settings: model={model}")
            return llm

    # Ultimate fallback
    return _get_fallback_llm('gpt-3.5-turbo', 0.1)


def get_llm_info(llm: ChatOpenAI) -> Dict[str, Any]:
    """
    Get information about an initialized LLM instance.

    Useful for logging and debugging.

    Args:
        llm: ChatOpenAI instance

    Returns:
        Dict with model info, temperature, etc.
    """
    return {
        "model_name": getattr(llm, 'model_name', 'unknown'),
        "temperature": getattr(llm, 'temperature', 'unknown'),
        "max_tokens": getattr(llm, 'max_tokens', 'not set'),
        "provider": "OpenAI"
    }
