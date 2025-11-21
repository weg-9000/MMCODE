"""
A2A Server core implementation for StackRecommender agent.
Handles task reception, processing, and response generation.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import uuid

from ...shared.a2a_server.server import A2AServer, TaskHandler
from ...shared.models.a2a_models import AgentCard, A2ATask, Artifact, AgentFramework
from ..models.stack_models import StackArtifact, ArchitectureContext, StackRecommendation
from ..capabilities.stack_analysis import StackAnalysisEngine
from ..utils.quality_scorer import QualityScorer

# Setup logging
logger = logging.getLogger(__name__)


class StackRecommenderAgent(A2AServer):
    """Stack Recommendation Agent using A2A Server pattern"""
    
    def __init__(self, config: Dict[str, Any]):
        # Create agent card
        agent_card = AgentCard(
            agent_id="stack-recommender-agent",
            agent_name="Stack Recommendation Agent",
            framework=AgentFramework.LANGCHAIN,
            capabilities=[
                "stack_recommendation",
                "technology_analysis",
                "compatibility_assessment", 
                "performance_optimization",
                "security_analysis",
                "cost_estimation"
            ],
            endpoint_url=config.get("own_endpoint", "http://localhost:8002"),
            version="1.0.0",
            metadata={
                "role": "technology_advisor",
                "specializations": ["backend", "frontend", "database", "infrastructure", "devops"],
                "output_formats": ["json", "yaml", "markdown"]
            }
        )
        
        super().__init__(agent_card)
        
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize capabilities
        self.analysis_engine = StackAnalysisEngine()
        self.quality_scorer = QualityScorer()
    
    @TaskHandler("stack_recommendation")
    async def handle_stack_recommendation(self, task: A2ATask) -> Artifact:
        """
        Main stack recommendation task handler.
        Analyzes architecture context and generates technology stack recommendations.
        """
        self.logger.info(f"Starting stack recommendation for task {task.task_id}")
        
        try:
            # Extract context data
            architecture_data = task.context.get("architecture")
            requirements_data = task.context.get("requirements", {})
            constraints_data = task.context.get("constraints", {})
            
            if not architecture_data:
                raise ValueError("No architecture data provided in task context")
            
            # Parse architecture context
            arch_context = ArchitectureContext(**architecture_data)
            
            # Perform stack analysis
            recommendation = await self.analysis_engine.analyze_and_recommend(
                architecture=arch_context,
                requirements=requirements_data,
                constraints=constraints_data
            )
            
            # Calculate quality scores
            quality_score = await self.quality_scorer.evaluate_recommendation(
                recommendation, arch_context
            )
            
            # Create comprehensive stack artifact
            stack_result = {
                "recommendation": recommendation.to_dict() if hasattr(recommendation, 'to_dict') else recommendation,
                "quality_assessment": {
                    "overall_score": quality_score.overall_score,
                    "suitability": quality_score.suitability,
                    "completeness": quality_score.completeness,
                    "feasibility": quality_score.feasibility
                },
                "architecture_context": arch_context.to_dict() if hasattr(arch_context, 'to_dict') else arch_context.__dict__,
                "implementation_guidance": {
                    "rationale": f"Recommended stack for {arch_context.domain if hasattr(arch_context, 'domain') else 'application'} with optimized technology choices",
                    "implementation_notes": [
                        "Consider team expertise when implementing",
                        "Start with MVP features and scale gradually",
                        "Implement monitoring and logging early",
                        "Plan for security and compliance requirements"
                    ],
                    "next_steps": [
                        "Review recommendation with team",
                        "Validate technology choices against constraints",
                        "Create implementation timeline",
                        "Setup development environment"
                    ]
                },
                "metadata": {
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "agent_version": self.agent_card.version,
                    "complexity_assessment": "medium",
                    "confidence_level": quality_score.overall_score
                }
            }
            
            self.logger.info(f"Stack recommendation completed with quality score: {quality_score.overall_score}")
            
            return Artifact(
                artifact_type="stack_recommendation",
                content=stack_result,
                quality_score=quality_score.overall_score,
                metadata={
                    "task_id": task.task_id,
                    "agent_id": self.agent_card.agent_id,
                    "processing_time": (datetime.utcnow() - task.created_at).total_seconds(),
                    "recommendation_confidence": quality_score.overall_score,
                    "technology_count": len(stack_result["recommendation"]) if isinstance(stack_result["recommendation"], dict) else 0
                },
                created_by=self.agent_card.agent_id
            )
            
        except Exception as e:
            self.logger.error(f"Stack recommendation failed for task {task.task_id}: {e}")
            raise
    
    @TaskHandler("technology_analysis")
    async def handle_technology_analysis(self, task: A2ATask) -> Artifact:
        """
        Focused technology analysis task handler.
        Analyzes specific technology choices and provides detailed assessments.
        """
        self.logger.info(f"Starting technology analysis for task {task.task_id}")
        
        try:
            technologies = task.context.get("technologies", [])
            criteria = task.context.get("analysis_criteria", {})
            
            if not technologies:
                raise ValueError("No technologies specified for analysis")
            
            # Analyze each technology
            analysis_results = []
            for tech in technologies:
                tech_analysis = await self.analysis_engine.analyze_technology(
                    technology=tech,
                    criteria=criteria
                )
                analysis_results.append(tech_analysis)
            
            # Create analysis report
            analysis_report = {
                "technology_analyses": analysis_results,
                "comparative_assessment": await self._compare_technologies(analysis_results),
                "recommendations": await self._generate_tech_recommendations(analysis_results, criteria)
            }
            
            return Artifact(
                artifact_type="technology_analysis",
                content=analysis_report,
                quality_score=0.8,  # Default quality score for analysis
                metadata={
                    "task_id": task.task_id,
                    "technology_count": len(technologies),
                    "analysis_criteria": criteria
                },
                created_by=self.agent_card.agent_id
            )
            
        except Exception as e:
            self.logger.error(f"Technology analysis failed for task {task.task_id}: {e}")
            raise
    
    async def _compare_technologies(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare multiple technology analyses and provide comparative insights.
        """
        if len(analyses) < 2:
            return {"comparison": "Single technology analyzed - no comparison available"}
        
        # Simple comparison logic - can be enhanced based on specific criteria
        comparison = {
            "technology_count": len(analyses),
            "comparative_strengths": [],
            "trade_offs": [],
            "recommendations": []
        }
        
        return comparison
    
    async def _generate_tech_recommendations(self, analyses: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[str]:
        """
        Generate specific technology recommendations based on analysis results.
        """
        recommendations = [
            "Evaluate technology choices against team expertise",
            "Consider long-term maintenance and support",
            "Assess community and ecosystem maturity",
            "Plan for scalability and performance requirements"
        ]
        
        return recommendations


# Note: This file now defines the StackRecommenderAgent class.
# The actual server instantiation should be handled by the main application
# that imports this agent and provides the necessary configuration.