"""Architect Agent - A2A Server for architecture design"""

import logging
from typing import Any, Dict,List
from datetime import datetime

from ...shared.a2a_server.server import A2AServer, TaskHandler
from ...shared.models.a2a_models import AgentCard, A2ATask, Artifact, AgentFramework
from ..capabilities.architecture_design import ArchitectureDesignEngine
from ..capabilities.pattern_matching import PatternMatchingEngine
from ..capabilities.component_modeling import ComponentModelingEngine
from ..models.architecture_models import ArchitectureDesign


class ArchitectAgent(A2AServer):
    """
    Architecture design agent that receives analysis results and creates
    system architecture designs, patterns, and component models.
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Create agent card
        agent_card = AgentCard(
            agent_id="architect-agent",
            agent_name="Architecture Design Agent",
            framework=AgentFramework.LANGCHAIN,
            capabilities=[
                "architecture_design",
                "pattern_matching", 
                "component_modeling",
                "diagram_generation",
                "adr_generation"
            ],
            endpoint_url=config.get("own_endpoint", "http://localhost:8001"),
            version="1.0.0",
            metadata={
                "role": "architect",
                "specializations": ["system_design", "patterns", "scalability"],
                "output_formats": ["mermaid", "plantuml", "json", "adr"]
            }
        )
        
        super().__init__(agent_card)
        
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize capabilities
        self.design_engine = ArchitectureDesignEngine(config)
        self.pattern_matcher = PatternMatchingEngine(config)
        self.component_modeler = ComponentModelingEngine(config)
    
    @TaskHandler("architecture_design")
    async def handle_architecture_design(self, task: A2ATask) -> Artifact:
        """
        Main architecture design task handler.
        Receives analysis result and creates comprehensive architecture design.
        """
        self.logger.info(f"Starting architecture design for task {task.task_id}")
        
        try:
            # Extract analysis data from context
            analysis_data = task.context.get("analysis")
            if not analysis_data:
                raise ValueError("No analysis data provided in task context")
            
            # Generate architecture design
            architecture = await self.design_engine.create_architecture(analysis_data)
            
            # Match and recommend patterns
            patterns = await self.pattern_matcher.recommend_patterns(architecture, analysis_data)
            
            # Create component model
            components = await self.component_modeler.model_components(architecture, patterns)
            
            # Combine into comprehensive design
            design_result = {
                "architecture": architecture.to_dict(),
                "patterns": [p.to_dict() for p in patterns],
                "components": [c.to_dict() for c in components],
                "diagrams": await self._generate_diagrams(architecture, components),
                "decisions": await self._generate_adrs(architecture, patterns),
                "metadata": {
                    "design_timestamp": datetime.utcnow().isoformat(),
                    "complexity_level": architecture.complexity_level,
                    "scalability_tier": architecture.scalability_tier,
                    "pattern_count": len(patterns),
                    "component_count": len(components)
                }
            }
            
            # Calculate quality score
            quality_score = await self._calculate_quality_score(design_result, analysis_data)
            
            self.logger.info(f"Architecture design completed with quality score: {quality_score}")
            
            return Artifact(
                artifact_type="architecture_design",
                content=design_result,
                quality_score=quality_score,
                metadata={
                    "task_id": task.task_id,
                    "agent_id": self.agent_card.agent_id,
                    "processing_time": (datetime.utcnow() - task.created_at).total_seconds(),
                    "design_approach": "pattern-driven",
                    "validation_passed": quality_score > 0.7
                },
                created_by=self.agent_card.agent_id
            )
            
        except Exception as e:
            self.logger.error(f"Architecture design failed for task {task.task_id}: {e}")
            raise
    
    @TaskHandler("pattern_recommendation")
    async def handle_pattern_recommendation(self, task: A2ATask) -> Artifact:
        """
        Focused pattern recommendation task.
        """
        self.logger.info(f"Starting pattern recommendation for task {task.task_id}")
        
        try:
            analysis_data = task.context.get("analysis")
            existing_architecture = task.context.get("architecture")
            
            # Quick architecture assessment if not provided
            if not existing_architecture:
                quick_arch = await self.design_engine.assess_architecture_needs(analysis_data)
                existing_architecture = quick_arch.to_dict()
            
            patterns = await self.pattern_matcher.recommend_patterns(
                existing_architecture, 
                analysis_data
            )
            
            pattern_result = {
                "recommended_patterns": [p.to_dict() for p in patterns],
                "pattern_rationale": await self.pattern_matcher.explain_recommendations(patterns),
                "implementation_priority": await self.pattern_matcher.prioritize_patterns(patterns),
                "compatibility_matrix": await self.pattern_matcher.check_pattern_compatibility(patterns)
            }
            
            quality_score = len(patterns) * 0.1 + 0.5  # Simple scoring
            quality_score = min(quality_score, 1.0)
            
            return Artifact(
                artifact_type="pattern_recommendation",
                content=pattern_result,
                quality_score=quality_score,
                metadata={
                    "task_id": task.task_id,
                    "pattern_count": len(patterns),
                    "recommendation_confidence": quality_score
                },
                created_by=self.agent_card.agent_id
            )
            
        except Exception as e:
            self.logger.error(f"Pattern recommendation failed for task {task.task_id}: {e}")
            raise
    
    async def _generate_diagrams(self, 
                                architecture: ArchitectureDesign, 
                                components: list) -> Dict[str, str]:
        """
        Generate Mermaid diagrams for architecture visualization
        """
        diagrams = {}
        
        # System architecture diagram
        diagrams["system_architecture"] = await self._create_system_diagram(architecture, components)
        
        # Component relationship diagram  
        diagrams["component_relations"] = await self._create_component_diagram(components)
        
        # Data flow diagram
        diagrams["data_flow"] = await self._create_dataflow_diagram(architecture, components)
        
        return diagrams
    
    async def _create_system_diagram(self, 
                                   architecture: ArchitectureDesign, 
                                   components: list) -> str:
        """
        Create Mermaid system architecture diagram
        """
        mermaid = ["graph TD"]
        
        # Add components as nodes
        for i, component in enumerate(components):
            node_id = f"C{i}"
            mermaid.append(f"    {node_id}[{component.name}]")
        
        # Add relationships
        for i, component in enumerate(components):
            for dep in component.dependencies:
                for j, other in enumerate(components):
                    if other.name == dep:
                        mermaid.append(f"    C{i} --> C{j}")
                        break
        
        return "\n".join(mermaid)
    
    async def _create_component_diagram(self, components: list) -> str:
        """
        Create component relationship diagram
        """
        # Simplified implementation
        mermaid = ["classDiagram"]
        
        for component in components:
            mermaid.append(f"    class {component.name.replace(' ', '_')} {{")
            for interface in component.interfaces:
                mermaid.append(f"        +{interface}")
            mermaid.append("    }")
        
        return "\n".join(mermaid)
    
    async def _create_dataflow_diagram(self, 
                                     architecture: ArchitectureDesign, 
                                     components: list) -> str:
        """
        Create data flow diagram
        """
        # Simplified data flow representation
        mermaid = ["flowchart LR"]
        mermaid.append("    User --> Frontend")
        mermaid.append("    Frontend --> Backend")
        mermaid.append("    Backend --> Database")
        
        return "\n".join(mermaid)
    
    async def _generate_adrs(self, 
                           architecture: ArchitectureDesign, 
                           patterns: list) -> List[Dict[str, Any]]:
        """
        Generate Architecture Decision Records (ADRs)
        """
        adrs = []
        
        # Main architecture pattern ADR
        if patterns:
            main_pattern = patterns[0]
            adr = {
                "id": "ADR-001",
                "title": f"Use {main_pattern.name} Pattern",
                "status": "Proposed",
                "context": f"System requires {main_pattern.context}",
                "decision": f"Implement {main_pattern.name} pattern",
                "rationale": main_pattern.benefits,
                "consequences": main_pattern.trade_offs
            }
            adrs.append(adr)
        
        # Database architecture ADR
        if architecture.data_tier:
            adr = {
                "id": "ADR-002", 
                "title": f"Database Architecture: {architecture.data_tier}",
                "status": "Proposed",
                "context": "System requires data persistence",
                "decision": f"Use {architecture.data_tier} for data layer",
                "rationale": "Matches system requirements and scalability needs",
                "consequences": "Will need appropriate ORM and connection management"
            }
            adrs.append(adr)
        
        return adrs
    
    async def _calculate_quality_score(self, 
                                     design_result: Dict[str, Any], 
                                     analysis_data: Dict[str, Any]) -> float:
        """
        Calculate quality score for architecture design
        """
        score = 0.0
        
        # Check completeness (40% of score)
        completeness_score = 0.0
        if design_result.get("architecture"):
            completeness_score += 0.25
        if design_result.get("patterns"):
            completeness_score += 0.25
        if design_result.get("components"):
            completeness_score += 0.25
        if design_result.get("diagrams"):
            completeness_score += 0.25
        
        score += completeness_score * 0.4
        
        # Check pattern alignment (30% of score)
        patterns = design_result.get("patterns", [])
        if patterns:
            pattern_score = min(len(patterns) * 0.2, 1.0)
            score += pattern_score * 0.3
        
        # Check component coverage (20% of score)
        components = design_result.get("components", [])
        entities = analysis_data.get("entities", [])
        if entities and components:
            coverage = min(len(components) / max(len(entities), 1), 1.0)
            score += coverage * 0.2
        
        # Check diagram quality (10% of score)
        diagrams = design_result.get("diagrams", {})
        if diagrams:
            diagram_score = min(len(diagrams) * 0.33, 1.0)
            score += diagram_score * 0.1
        
        return min(score, 1.0)