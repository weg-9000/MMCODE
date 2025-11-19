"""
Agent System Integration Module

This module provides integration between the new modular A2A agent architecture
and the existing FastAPI system for backward compatibility.
"""

from typing import Dict, Any, Optional
import logging

# Import new modular agents
from .requirement_analyzer.core.agent import RequirementAnalyzer
from .requirement_analyzer.config.settings import get_agent_config

# Import shared A2A infrastructure
from .shared.models.a2a_models import AgentCard, A2ATask, Artifact
from .shared.a2a_client.client import A2AClient
from .shared.registry.agent_registry import AgentRegistry


class AgentSystemManager:
    """
    Manager for the entire agent system, providing both legacy and A2A interfaces
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize requirement analyzer (main orchestrator)
        self.requirement_analyzer = RequirementAnalyzer(get_agent_config())
        
        # A2A infrastructure
        self.a2a_client = A2AClient()
        self.agent_registry: Optional[AgentRegistry] = None
        
    async def initialize(self, redis_client=None):
        """Initialize the agent system"""
        if redis_client:
            self.agent_registry = AgentRegistry(redis_client)
            
        self.logger.info("Agent system initialized")
    
    # Legacy interface methods for backward compatibility
    async def analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        Legacy interface: Analyze requirements only
        """
        try:
            analysis_result = await self.requirement_analyzer.analyze_requirements_only(requirements)
            return analysis_result.to_dict()
        except Exception as e:
            self.logger.error(f"Requirement analysis failed: {e}")
            raise
    
    async def run_full_orchestration(self, requirements: str, session_id: str) -> Dict[str, Any]:
        """
        New A2A interface: Full analysis and orchestration
        """
        try:
            return await self.requirement_analyzer.analyze_and_orchestrate(requirements, session_id)
        except Exception as e:
            self.logger.error(f"Full orchestration failed: {e}")
            raise
    
    async def execute_single_agent_task(self, 
                                      agent_name: str, 
                                      task_type: str, 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task on specific agent (A2A interface)
        """
        try:
            task_result = await self.requirement_analyzer.execute_agent_task(
                agent_name, task_type, context
            )
            return {
                "task_id": task_result.task_id,
                "status": task_result.status.value,
                "result": task_result.result,
                "error": task_result.error
            }
        except Exception as e:
            self.logger.error(f"Agent task execution failed: {e}")
            raise
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get health status of entire agent system
        """
        try:
            return await self.requirement_analyzer.health_check()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Clean up resources"""
        await self.requirement_analyzer.close()
        await self.a2a_client.close()


# Global agent system manager instance
_agent_manager: Optional[AgentSystemManager] = None


def get_agent_manager(config: Optional[Dict[str, Any]] = None) -> AgentSystemManager:
    """Get global agent manager instance"""
    global _agent_manager
    
    if _agent_manager is None:
        if config is None:
            config = get_agent_config()
        _agent_manager = AgentSystemManager(config)
    
    return _agent_manager


async def initialize_agent_system(config: Dict[str, Any], redis_client=None):
    """Initialize the global agent system"""
    global _agent_manager
    _agent_manager = AgentSystemManager(config)
    await _agent_manager.initialize(redis_client)


# Legacy interface functions for backward compatibility
async def analyze_requirements_legacy(requirements: str) -> Dict[str, Any]:
    """Legacy function for requirement analysis"""
    manager = get_agent_manager()
    return await manager.analyze_requirements(requirements)


# Export key classes and functions
__all__ = [
    'AgentSystemManager',
    'get_agent_manager', 
    'initialize_agent_system',
    'analyze_requirements_legacy',
    'RequirementAnalyzer',
    'AgentCard',
    'A2ATask', 
    'Artifact',
    'A2AClient',
    'AgentRegistry'
]