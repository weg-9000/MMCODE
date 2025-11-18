from abc import ABC, abstractmethod
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any
import asyncio
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

class AgentInput(BaseModel):
    """Input model for agents"""
    requirements: str
    context: Dict[str, Any] = {}
    session_id: str

class AgentOutput(BaseModel):
    """Output model for agents"""
    output: Dict[str, Any]
    sources: List[Dict[str, Any]] = []
    token_usage: int = 0
    execution_time: float = 0.0

class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY
        )
        logger.info(f"Initialized agent: {name}")
    
    @abstractmethod
    async def run(self, input_data: AgentInput) -> AgentOutput:
        """Execute the agent logic"""
        pass
    
    async def log_decision(
        self, 
        session_id: str, 
        decision: Dict[str, Any], 
        sources: List[Dict[str, Any]]
    ):
        """Log agent decision for audit"""
        try:
            from ..services.decision_service import log_agent_decision
            await log_agent_decision(
                session_id=session_id,
                agent_name=self.name,
                decision=decision,
                sources=sources
            )
        except Exception as e:
            logger.error(f"Failed to log decision for {self.name}: {str(e)}")
    
    def _extract_token_usage(self, response) -> int:
        """Extract token usage from LangChain response"""
        try:
            return response.response_metadata.get("token_usage", {}).get("total_tokens", 0)
        except (AttributeError, KeyError):
            return 0