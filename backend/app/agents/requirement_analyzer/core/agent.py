"""Requirement Analyzer Agent - Main orchestrator with A2A client capabilities"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...shared.a2a_client.client import A2AClient
from ...shared.models.a2a_models import AgentCard, A2ATask, Artifact, AgentFramework
from ..capabilities.requirement_analysis import RequirementAnalysisEngine
from ..capabilities.task_decomposition import TaskDecompositionEngine
from ..capabilities.coordination import AgentCoordinator
from ..models.analysis_models import AnalysisResult, CoordinationPlan


class RequirementAnalyzer:
    """
    Main requirement analyzer agent that acts as both analyzer and A2A orchestrator.
    Analyzes user requirements and coordinates other agents via A2A protocol.
    """
    
    def __init__(self, agent_config: Dict[str, Any], a2a_client=None):
        self.agent_id = "requirement-analyzer"
        self.agent_name = "Requirement Analyzer & Orchestrator"
        self.config = agent_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize capabilities
        self.analysis_engine = RequirementAnalysisEngine(agent_config)
        self.decomposition_engine = TaskDecompositionEngine(agent_config)
        self.coordinator = AgentCoordinator(agent_config)
        
        if a2a_client:
            self.a2a_client = a2a_client
        else:
            # 기존 코드: 내부 생성
            self.a2a_client = A2AClient(timeout=300)
        
        # Known agent endpoints (from configuration or registry)
        self.agent_endpoints = {
            "architect": agent_config.get("architect_url", "http://localhost:8001"),
            "stack_recommender": agent_config.get("stack_recommender_url", "http://localhost:8002"),
            "documenter": agent_config.get("documenter_url", "http://localhost:8003")
        }
    
    async def analyze_and_orchestrate(self, requirements: str, session_id: str) -> Dict[str, Any]:
        """
        Main entry point: analyze requirements and orchestrate other agents
        """
        self.logger.info(f"Starting analysis and orchestration for session {session_id}")
        
        try:
            # Phase 1: Analyze requirements
            analysis_result = await self.analysis_engine.analyze(requirements)
            
            # Phase 2: Decompose into tasks
            coordination_plan = await self.decomposition_engine.decompose(analysis_result)
            
            # Phase 3: Execute coordination plan
            orchestration_result = await self.coordinator.execute_plan(
                coordination_plan, 
                self.agent_endpoints,
                self.a2a_client
            )
            
            return {
                "session_id": session_id,
                "analysis": analysis_result.to_dict(),
                "coordination_plan": coordination_plan.to_dict(),
                "orchestration_result": orchestration_result,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Analysis and orchestration failed for session {session_id}: {e}")
            return {
                "session_id": session_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_requirements_only(self, requirements: str) -> AnalysisResult:
        """
        Analyze requirements without orchestration (for backward compatibility)
        """
        return await self.analysis_engine.analyze(requirements)
    
    async def create_coordination_plan(self, analysis: AnalysisResult) -> CoordinationPlan:
        """
        Create coordination plan from analysis result
        """
        return await self.decomposition_engine.decompose(analysis)
    
    async def execute_agent_task(self, agent_name: str, task_type: str, context: Dict[str, Any]) -> A2ATask:
        """
        Execute a specific task on a target agent
        """
        if agent_name not in self.agent_endpoints:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        agent_url = self.agent_endpoints[agent_name]
        
        try:
            task = await self.a2a_client.create_task_with_wait(
                agent_url=agent_url,
                task_type=task_type,
                context=context,
                max_wait_time=300.0
            )
            
            self.logger.info(f"Task {task.task_id} completed on {agent_name}: {task.status}")
            return task
            
        except Exception as e:
            self.logger.error(f"Task execution failed on {agent_name}: {e}")
            raise
    
    async def get_agent_capabilities(self, agent_name: str) -> Dict[str, Any]:
        """
        Get capabilities of a specific agent
        """
        if agent_name not in self.agent_endpoints:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        return await self.a2a_client.get_agent_capabilities(self.agent_endpoints[agent_name])
    
    def create_agent_card(self) -> AgentCard:
        """
        Create agent card for this analyzer (for registration if needed)
        """
        return AgentCard(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            framework=AgentFramework.LANGCHAIN,
            capabilities=[
                "requirement_analysis",
                "task_decomposition", 
                "agent_orchestration",
                "a2a_coordination"
            ],
            endpoint_url=self.config.get("own_endpoint", "http://localhost:8000"),
            version="1.0.0",
            metadata={
                "role": "orchestrator",
                "can_coordinate": True,
                "sub_agents": list(self.agent_endpoints.keys())
            }
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for this agent and connected agents
        """
        health_status = {
            "self": "healthy",
            "sub_agents": {}
        }
        
        for agent_name, endpoint in self.agent_endpoints.items():
            try:
                capabilities = await self.a2a_client.get_agent_capabilities(endpoint)
                health_status["sub_agents"][agent_name] = "healthy"
            except Exception as e:
                health_status["sub_agents"][agent_name] = f"unhealthy: {str(e)}"
        
        return health_status
    
    async def close(self):
        """
        Clean up resources
        """
        await self.a2a_client.close()
        self.logger.info("RequirementAnalyzer closed")