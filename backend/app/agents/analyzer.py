from langchain.prompts import ChatPromptTemplate
from typing import Dict, List, Any
import json
import time
import logging

from .base import BaseAgent, AgentInput, AgentOutput
from ..services.search_service import search_by_keywords

logger = logging.getLogger(__name__)

class RequirementAnalyzer(BaseAgent):
    """Agent for analyzing user requirements"""
    
    def __init__(self):
        super().__init__("requirement_analyzer")
        
        self.prompt = ChatPromptTemplate.from_template("""
        You are a senior requirement analyst. Extract structured data from user requirements.
        
        Requirements: {requirements}
        
        Analyze and extract the following information in valid JSON format:
        {{
            "entities": ["PascalCase names of main entities/models"],
            "use_cases": ["action-oriented use cases"],
            "quality_attributes": ["performance", "security", "scalability", etc.],
            "technical_constraints": ["specific technology requirements"],
            "ambiguous_items": [{{
                "text": "unclear requirement text",
                "question": "clarification question"
            }}],
            "complexity_score": 0.0-1.0,
            "estimated_timeline": "rough estimate in weeks"
        }}
        
        Provide only the JSON response, no additional text.
        """)
        self.chain = self.prompt | self.llm
    
    async def run(self, input_data: AgentInput) -> AgentOutput:
        """Analyze requirements and extract structured information"""
        start_time = time.time()
        
        try:
            logger.info(f"Starting requirement analysis for session {input_data.session_id}")
            
            # Execute LLM analysis
            response = await self.chain.ainvoke({
                "requirements": input_data.requirements
            })
            
            # Parse JSON response
            try:
                analysis_result = json.loads(response.content)
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM response as JSON")
                analysis_result = {
                    "entities": [],
                    "use_cases": [],
                    "quality_attributes": [],
                    "technical_constraints": [],
                    "ambiguous_items": [],
                    "complexity_score": 0.5,
                    "estimated_timeline": "unknown"
                }
            
            # Search for relevant knowledge
            sources = await self._search_sources(analysis_result.get("entities", []))
            
            # Log decision
            await self.log_decision(
                input_data.session_id,
                analysis_result,
                sources
            )
            
            execution_time = time.time() - start_time
            
            return AgentOutput(
                output=analysis_result,
                sources=sources,
                token_usage=self._extract_token_usage(response),
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Requirement analysis failed: {str(e)}")
            execution_time = time.time() - start_time
            
            return AgentOutput(
                output={
                    "error": "Analysis failed",
                    "message": str(e)
                },
                sources=[],
                token_usage=0,
                execution_time=execution_time
            )
    
    async def _search_sources(self, entities: List[str]) -> List[Dict[str, Any]]:
        """Search for relevant sources based on extracted entities"""
        all_sources = []
        try:
            for entity in entities[:3]:  # Limit to top 3 entities
                sources = await search_by_keywords(entity, limit=2)
                all_sources.extend(sources)
        except Exception as e:
            logger.warning(f"Source search failed: {str(e)}")
        
        return all_sources