"""
Dependency injection system for DevStrategist AI
Manages agent lifecycle, database connections, and shared resources
"""

from typing import Dict, Any, Optional
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from app.db.session import get_db, AsyncSessionLocal
from app.models.models import Agent
from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient
from app.agents.requirement_analyzer.core.agent import RequirementAnalyzer
from app.core.config import Settings

logger = logging.getLogger(__name__)

# Global agent registry
_agent_registry: Dict[str, Any] = {}
_a2a_client: Optional[InMemoryA2AClient] = None
_settings = Settings()

# Lazy loading cache
_lazy_agent_cache: Dict[str, Any] = {}
_lazy_initialization_lock = asyncio.Lock()

class AgentRegistry:
    """Centralized agent registry for dependency injection"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.a2a_client: Optional[InMemoryA2AClient] = None
        self.requirement_analyzer: Optional[RequirementAnalyzer] = None
    
    async def initialize(self):
        """Initialize all agents and dependencies"""
        logger.info("Initializing agent registry...")
        
        # Initialize A2A client
        self.a2a_client = InMemoryA2AClient()
        
        # Import and instantiate agents
        try:
            await self._initialize_agents()
            await self._register_agents_in_database()
            logger.info(f"Initialized {len(self.agents)} agents successfully")
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            raise
    
    async def _initialize_agents(self):
        """Create agent instances with improved error handling and timeouts"""
        try:
            # Import agent classes with timeout protection
            import asyncio
            from app.agents.requirement_analyzer.core.agent import RequirementAnalyzer
            from app.agents.architect_agent.core.agent import ArchitectAgent
            from app.agents.stack_recommender.core.agent import StackRecommenderAgent
            from app.agents.document_agent.core.agent import DocumentAgent
            
            # Create instances with proper config - use in-memory client for all agents
            agent_config = {
                "llm_provider": getattr(_settings, 'LLM_PROVIDER', 'perplexity'),
                "llm_model": getattr(_settings, 'LLM_MODEL', 'sonar-reasoning'),
                "llm_api_key": getattr(_settings, 'LLM_API_KEY', None),
                "timeout": getattr(_settings, 'AGENT_TIMEOUT', 30),  # Reduced timeout
                "use_in_memory_client": True  # Force in-memory client usage
            }
            
            # Create agents with timeout protection
            async with asyncio.timeout(10):  # 10 second timeout for agent creation
                self.requirement_analyzer = RequirementAnalyzer(agent_config, a2a_client=self.a2a_client)
                architect = ArchitectAgent(agent_config)
                stack_recommender = StackRecommenderAgent(agent_config)
                documenter = DocumentAgent(agent_config)
            
            # Register with A2A client
            self.a2a_client.register("requirement-analyzer", self.requirement_analyzer)
            self.a2a_client.register("architect", architect)
            self.a2a_client.register("stack_recommender", stack_recommender)
            self.a2a_client.register("documenter", documenter)
            
            # Store in registry
            self.agents = {
                "requirement-analyzer": self.requirement_analyzer,
                "architect": architect,
                "stack_recommender": stack_recommender,
                "documenter": documenter
            }
            
            logger.info("All agent instances created successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import agent classes: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise
    
    async def _register_agents_in_database(self):
        """Register agents in database for API access with timeout protection"""
        try:
            import asyncio
            # Add timeout protection for database operations
            async with asyncio.timeout(5):  # 5 second timeout for DB operations
                async with AsyncSessionLocal() as db:
                    for agent_id, agent_instance in self.agents.items():
                        try:
                            # Check if agent already exists
                            from sqlalchemy import select
                            result = await db.execute(select(Agent).where(Agent.id == agent_id))
                            existing_agent = result.scalar_one_or_none()
                            
                            if not existing_agent:
                                # Create new agent record
                                agent_record = Agent(
                                    id=agent_id,
                                    name=agent_id.replace("-", " ").title(),
                                    role=agent_id.replace("-", "_"),
                                    description=f"AI agent for {agent_id.replace('-', ' ')} tasks",
                                    endpoint_url=f"local://{agent_id}",
                                    capabilities=self._get_agent_capabilities(agent_id),
                                    status="active",
                                    version="1.0.0"
                                )
                                db.add(agent_record)
                            else:
                                # Update existing agent
                                existing_agent.status = "active"
                                existing_agent.endpoint_url = f"local://{agent_id}"
                        
                        except Exception as agent_error:
                            logger.warning(f"Failed to register agent {agent_id}: {agent_error}")
                            continue
                    
                    await db.commit()
                    logger.info("Agent database registration completed")
                
        except asyncio.TimeoutError:
            logger.warning("Database registration timed out - agents will work without DB registration")
        except Exception as e:
            logger.error(f"Database registration failed: {e}")
            # Continue anyway - agents can work without DB registration
    
    def _get_agent_capabilities(self, agent_id: str) -> list:
        """Get capabilities for each agent"""
        capabilities_map = {
            "requirement-analyzer": ["requirement_analysis", "task_orchestration", "coordination"],
            "architect": ["architecture_design", "component_modeling", "pattern_matching"],
            "stack_recommender": ["stack_recommendation", "technology_analysis", "quality_assessment"],
            "documenter": ["documentation_generation", "template_management", "quality_assessment"]
        }
        return capabilities_map.get(agent_id, [])
    
    async def cleanup(self):
        """Cleanup agents and resources"""
        logger.info("Cleaning up agent registry...")
        
        # Close A2A client connections
        if self.a2a_client:
            await self.a2a_client.close()
        
        # Clear registry
        self.agents.clear()
        self.requirement_analyzer = None
        self.a2a_client = None
        
        logger.info("Agent registry cleanup completed")

# Global registry instance
_registry: Optional[AgentRegistry] = None

async def initialize_agents():
    """Initialize global agent registry"""
    global _registry
    _registry = AgentRegistry()
    await _registry.initialize()

async def cleanup_agents():
    """Cleanup global agent registry"""
    global _registry
    if _registry:
        await _registry.cleanup()
        _registry = None

def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry"""
    if not _registry:
        raise RuntimeError("Agent registry not initialized. Call initialize_agents() first.")
    return _registry

def get_requirement_analyzer() -> RequirementAnalyzer:
    """Get the requirement analyzer instance"""
    registry = get_agent_registry()
    if not registry.requirement_analyzer:
        raise RuntimeError("Requirement analyzer not available")
    return registry.requirement_analyzer

def get_a2a_client() -> InMemoryA2AClient:
    """Get the A2A client instance"""
    registry = get_agent_registry()
    if not registry.a2a_client:
        raise RuntimeError("A2A client not available")
    return registry.a2a_client

def get_agent(agent_id: str) -> Any:
    """Get specific agent by ID"""
    registry = get_agent_registry()
    agent = registry.agents.get(agent_id)
    if not agent:
        raise RuntimeError(f"Agent '{agent_id}' not found in registry")
    return agent

@asynccontextmanager
async def get_agent_with_db(agent_id: str):
    """Get agent with database session context"""
    agent = get_agent(agent_id)
    async with AsyncSessionLocal() as db:
        yield agent, db

# FastAPI dependency functions
async def get_db_session() -> AsyncSession:
    """FastAPI dependency for database session"""
    async for session in get_db():
        yield session

def get_analyzer_dependency() -> RequirementAnalyzer:
    """FastAPI dependency for requirement analyzer"""
    return get_requirement_analyzer()

def get_a2a_dependency() -> InMemoryA2AClient:
    """FastAPI dependency for A2A client"""
    return get_a2a_client()

# Agent registration helpers for API endpoints
def register_agent_instance(agent_id: str, agent_instance: Any):
    """Register agent instance (used by API endpoints)"""
    try:
        registry = get_agent_registry()
        registry.agents[agent_id] = agent_instance
        if registry.a2a_client:
            registry.a2a_client.register(agent_id, agent_instance)
        logger.info(f"Agent '{agent_id}' registered successfully")
    except Exception as e:
        logger.error(f"Failed to register agent '{agent_id}': {e}")

def get_all_agents() -> Dict[str, Any]:
    """Get all registered agents"""
    registry = get_agent_registry()
    return registry.agents.copy()

async def get_agent_lazy(agent_id: str) -> Any:
    """Get agent with lazy initialization - creates agent on first request"""
    global _lazy_agent_cache, _lazy_initialization_lock
    
    # Check if agent is already cached
    if agent_id in _lazy_agent_cache:
        return _lazy_agent_cache[agent_id]
    
    async with _lazy_initialization_lock:
        # Double-check after acquiring lock
        if agent_id in _lazy_agent_cache:
            return _lazy_agent_cache[agent_id]
        
        logger.info(f"Lazy initializing agent: {agent_id}")
        
        try:
            # Initialize agent based on type
            agent_config = {
                "llm_provider": getattr(_settings, 'LLM_PROVIDER', 'perplexity'),
                "llm_model": getattr(_settings, 'LLM_MODEL', 'sonar-reasoning'),
                "llm_api_key": getattr(_settings, 'LLM_API_KEY', None),
                "timeout": getattr(_settings, 'AGENT_TIMEOUT', 30),
                "use_in_memory_client": True
            }
            
            # Get or create A2A client
            if not _a2a_client:
                _a2a_client = InMemoryA2AClient()
            
            # Create agent with timeout protection
            async with asyncio.timeout(15):  # 15 second timeout for lazy loading
                if agent_id == "requirement-analyzer":
                    from app.agents.requirement_analyzer.core.agent import RequirementAnalyzer
                    agent = RequirementAnalyzer(agent_config, a2a_client=_a2a_client)
                elif agent_id == "architect":
                    from app.agents.architect_agent.core.agent import ArchitectAgent
                    agent = ArchitectAgent(agent_config)
                elif agent_id == "stack_recommender":
                    from app.agents.stack_recommender.core.agent import StackRecommenderAgent
                    agent = StackRecommenderAgent(agent_config)
                elif agent_id == "documenter":
                    from app.agents.document_agent.core.agent import DocumentAgent
                    agent = DocumentAgent(agent_config)
                else:
                    raise ValueError(f"Unknown agent type: {agent_id}")
                
                # Register with A2A client
                _a2a_client.register(agent_id, agent)
                
                # Cache the agent
                _lazy_agent_cache[agent_id] = agent
                
                logger.info(f"Agent '{agent_id}' lazy initialized successfully")
                return agent
                
        except Exception as e:
            logger.error(f"Failed to lazy initialize agent '{agent_id}': {e}")
            raise RuntimeError(f"Agent '{agent_id}' initialization failed: {e}")

def get_requirement_analyzer_lazy() -> RequirementAnalyzer:
    """FastAPI dependency for lazy-loaded requirement analyzer"""
    import asyncio
    
    # Create a new event loop for sync context if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(get_agent_lazy("requirement-analyzer"))

# Health check utilities
async def check_agent_health(agent_id: str) -> Dict[str, Any]:
    """Check health of specific agent"""
    try:
        agent = get_agent(agent_id)
        
        health_status = {
            "agent_id": agent_id,
            "status": "healthy",
            "registered": True,
            "capabilities": _registry._get_agent_capabilities(agent_id) if _registry else []
        }
        
        # Try to call health check method if available
        if hasattr(agent, 'health_check'):
            try:
                agent_health = await agent.health_check()
                health_status.update(agent_health)
            except Exception as e:
                health_status["status"] = "unhealthy"
                health_status["error"] = str(e)
        
        return health_status
        
    except Exception as e:
        return {
            "agent_id": agent_id,
            "status": "unhealthy",
            "registered": False,
            "error": str(e)
        }

async def system_health_check() -> Dict[str, Any]:
    """Check overall system health"""
    try:
        registry = get_agent_registry()
        
        agent_statuses = []
        for agent_id in registry.agents.keys():
            status = await check_agent_health(agent_id)
            agent_statuses.append(status)
        
        healthy_agents = sum(1 for status in agent_statuses if status["status"] == "healthy")
        
        return {
            "system_status": "healthy" if healthy_agents == len(agent_statuses) else "degraded",
            "total_agents": len(agent_statuses),
            "healthy_agents": healthy_agents,
            "agent_details": agent_statuses,
            "a2a_client_status": "healthy" if registry.a2a_client else "unavailable"
        }
        
    except Exception as e:
        return {
            "system_status": "unhealthy",
            "error": str(e),
            "total_agents": 0,
            "healthy_agents": 0
        }