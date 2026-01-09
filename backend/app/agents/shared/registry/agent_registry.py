"""Agent Registry and Discovery System"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

import redis.asyncio as redis
from ..models.a2a_models import AgentCard
from ..a2a_client.client import A2AClient


class AgentRegistry:
    """Central agent registration and discovery system"""
    
    def __init__(self, redis_client: redis.Redis, registry_prefix: str = "agent_registry"):
        self.redis = redis_client
        self.prefix = registry_prefix
        self.logger = logging.getLogger(self.__class__.__name__)
        self.capability_index_prefix = f"{registry_prefix}:capabilities"
        self.health_check_interval = 30  # seconds
        
    async def register_agent(self, agent_card: AgentCard) -> bool:
        """Register an agent in the registry"""
        import json

        try:
            # Store agent card as proper JSON
            agent_key = f"{self.prefix}:agents:{agent_card.agent_id}"
            agent_data = json.dumps(agent_card.to_dict())
            await self.redis.set(agent_key, agent_data)
            
            # Update capability index
            for capability in agent_card.capabilities:
                capability_key = f"{self.capability_index_prefix}:{capability}"
                await self.redis.sadd(capability_key, agent_card.agent_id)
            
            # Store endpoint mapping
            endpoint_key = f"{self.prefix}:endpoints:{agent_card.agent_id}"
            await self.redis.set(endpoint_key, agent_card.endpoint_url)
            
            # Set TTL for health checking
            await self.redis.expire(agent_key, self.health_check_interval * 2)
            
            self.logger.info(f"Registered agent {agent_card.agent_id} ({agent_card.agent_name})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_card.agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the registry"""
        try:
            # Get agent card first to clean up capability index
            agent = await self.get_agent_by_id(agent_id)
            if agent:
                for capability in agent.capabilities:
                    capability_key = f"{self.capability_index_prefix}:{capability}"
                    await self.redis.srem(capability_key, agent_id)
            
            # Remove agent data
            agent_key = f"{self.prefix}:agents:{agent_id}"
            endpoint_key = f"{self.prefix}:endpoints:{agent_id}"
            
            await self.redis.delete(agent_key, endpoint_key)
            
            self.logger.info(f"Unregistered agent {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def get_agent_by_id(self, agent_id: str) -> Optional[AgentCard]:
        """Get agent by ID"""
        try:
            agent_key = f"{self.prefix}:agents:{agent_id}"
            agent_data = await self.redis.get(agent_key)
            
            if not agent_data:
                return None
            
            # Parse agent data (simplified - in real implementation use proper JSON parsing)
            return self._parse_agent_data(agent_data)
            
        except Exception as e:
            self.logger.error(f"Failed to get agent {agent_id}: {e}")
            return None
    
    async def find_agents_by_capability(self, capability: str) -> List[AgentCard]:
        """Find all agents with specific capability"""
        try:
            capability_key = f"{self.capability_index_prefix}:{capability}"
            agent_ids = await self.redis.smembers(capability_key)
            
            agents = []
            for agent_id in agent_ids:
                agent = await self.get_agent_by_id(agent_id.decode() if isinstance(agent_id, bytes) else agent_id)
                if agent:
                    agents.append(agent)
            
            return agents
            
        except Exception as e:
            self.logger.error(f"Failed to find agents with capability {capability}: {e}")
            return []
    
    async def get_all_agents(self) -> List[AgentCard]:
        """Get all registered agents"""
        try:
            pattern = f"{self.prefix}:agents:*"
            agent_keys = await self.redis.keys(pattern)
            
            agents = []
            for agent_key in agent_keys:
                agent_id = agent_key.decode().split(":")[-1] if isinstance(agent_key, bytes) else agent_key.split(":")[-1]
                agent = await self.get_agent_by_id(agent_id)
                if agent:
                    agents.append(agent)
            
            return agents
            
        except Exception as e:
            self.logger.error(f"Failed to get all agents: {e}")
            return []
    
    async def health_check_agents(self) -> Dict[str, bool]:
        """Perform health check on all registered agents"""
        agents = await self.get_all_agents()
        health_status = {}
        
        async with A2AClient() as client:
            for agent in agents:
                try:
                    # Try to get agent capabilities as health check
                    await client.get_agent_capabilities(agent.endpoint_url)
                    health_status[agent.agent_id] = True
                    
                    # Refresh TTL
                    agent_key = f"{self.prefix}:agents:{agent.agent_id}"
                    await self.redis.expire(agent_key, self.health_check_interval * 2)
                    
                except Exception as e:
                    self.logger.warning(f"Health check failed for agent {agent.agent_id}: {e}")
                    health_status[agent.agent_id] = False
                    
                    # Consider unregistering after multiple failures
                    await self._handle_unhealthy_agent(agent.agent_id)
        
        return health_status
    
    async def _handle_unhealthy_agent(self, agent_id: str):
        """Handle unhealthy agent (unregister after threshold)"""
        failure_key = f"{self.prefix}:failures:{agent_id}"
        failures = await self.redis.incr(failure_key)
        await self.redis.expire(failure_key, self.health_check_interval * 5)
        
        if failures >= 3:  # Unregister after 3 consecutive failures
            await self.unregister_agent(agent_id)
            await self.redis.delete(failure_key)
            self.logger.warning(f"Unregistered unhealthy agent {agent_id} after {failures} failures")
    
    def _parse_agent_data(self, agent_data: bytes | str) -> Optional[AgentCard]:
        """Parse agent data from Redis with proper JSON deserialization"""
        import json

        try:
            # Handle bytes from Redis
            if isinstance(agent_data, bytes):
                agent_data = agent_data.decode('utf-8')

            # Try parsing as JSON first
            try:
                data = json.loads(agent_data)
            except json.JSONDecodeError:
                # Fallback: Try to evaluate as Python dict representation
                # This handles legacy format: {'key': 'value'} stored as string
                import ast
                data = ast.literal_eval(agent_data)

            # Create AgentCard from parsed data
            return AgentCard(
                agent_id=data.get('agent_id'),
                agent_name=data.get('agent_name', ''),
                description=data.get('description', ''),
                endpoint_url=data.get('endpoint_url', ''),
                capabilities=data.get('capabilities', []),
                version=data.get('version', '1.0.0'),
                status=data.get('status', 'unknown'),
                metadata=data.get('metadata', {})
            )
        except Exception as e:
            self.logger.error(f"Failed to parse agent data: {e}")
            return None
    
    async def start_health_monitoring(self):
        """Start background health monitoring task"""
        async def monitor():
            while True:
                try:
                    await self.health_check_agents()
                    await asyncio.sleep(self.health_check_interval)
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(5)
        
        asyncio.create_task(monitor())