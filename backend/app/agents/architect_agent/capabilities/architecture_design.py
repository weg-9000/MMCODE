"""Architecture Design Engine"""

import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..models.architecture_models import (
    ArchitectureDesign, ArchitecturePattern, ScalabilityTier,
    LayerSpec, DeploymentSpec
)


class ArchitectureDesignEngine:
    """
    Core engine for creating system architecture designs from analysis results
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config.get("openai_model", "gpt-3.5-turbo"),
            temperature=0.2,
            openai_api_key=config.get("openai_api_key")
        )
        
        # Architecture design prompt
        self.design_prompt = ChatPromptTemplate.from_template(
            """You are a senior software architect. Design a system architecture based on the provided analysis.

Analysis:
{analysis}

Design a comprehensive system architecture considering:
1. Entities and their relationships
2. Use cases and user flows
3. Quality attributes (performance, security, scalability)
4. Technical constraints and requirements
5. Domain context and complexity

Output JSON format:
{{
    "architecture_name": "Descriptive name",
    "description": "Brief architecture description",
    "primary_pattern": "layered|microservices|monolithic|event_driven|serverless|hexagonal",
    "secondary_patterns": ["pattern1", "pattern2"],
    "presentation_tier": "Technology/framework for UI layer",
    "business_tier": "Technology/framework for business logic",
    "data_tier": "Database technology and approach",
    "scalability_tier": "small|medium|large|enterprise",
    "complexity_level": 0.1-1.0,
    "key_decisions": [
        {{"decision": "Decision made", "rationale": "Why this decision"}}
    ],
    "assumptions": ["assumption1", "assumption2"],
    "constraints": ["constraint1", "constraint2"],
    "risks": [
        {{"risk": "Potential risk", "mitigation": "How to mitigate"}}
    ]
}}

Consider:
- Start simple, allow for growth
- Choose proven patterns over novel ones
- Optimize for team skills and maintenance
- Balance immediate needs with future scalability"""
        )
    
    async def create_architecture(self, analysis_data: Dict[str, Any]) -> ArchitectureDesign:
        """
        Create comprehensive architecture design from analysis
        """
        self.logger.info("Creating architecture design")
        
        try:
            # Generate architecture using LLM
            llm_result = await self._generate_architecture_llm(analysis_data)
            
            # Enhance with rule-based decisions
            enhanced_design = await self._enhance_architecture(llm_result, analysis_data)
            
            # Create architecture design object
            architecture = self._create_architecture_object(enhanced_design, analysis_data)
            
            self.logger.info(f"Architecture design created: {architecture.name}")
            return architecture
            
        except Exception as e:
            self.logger.error(f"Architecture design failed: {e}")
            raise
    
    async def assess_architecture_needs(self, analysis_data: Dict[str, Any]) -> ArchitectureDesign:
        """
        Quick architecture assessment for pattern recommendations
        """
        # Simplified architecture assessment
        entities = analysis_data.get("entities", [])
        use_cases = analysis_data.get("use_cases", [])
        complexity_score = analysis_data.get("complexity_score", 0.5)
        
        # Determine primary pattern based on complexity and scale
        if complexity_score > 0.7 or len(entities) > 10:
            primary_pattern = ArchitecturePattern.MICROSERVICES
            scalability = ScalabilityTier.LARGE
        elif complexity_score > 0.4 or len(use_cases) > 8:
            primary_pattern = ArchitecturePattern.LAYERED
            scalability = ScalabilityTier.MEDIUM
        else:
            primary_pattern = ArchitecturePattern.MONOLITHIC
            scalability = ScalabilityTier.SMALL
        
        return ArchitectureDesign(
            design_id=str(uuid.uuid4()),
            name="Quick Assessment Architecture",
            description="Preliminary architecture assessment",
            primary_pattern=primary_pattern,
            scalability_tier=scalability,
            complexity_level=complexity_score
        )
    
    async def _generate_architecture_llm(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to generate architecture design
        """
        try:
            response = await self.llm.ainvoke(
                self.design_prompt.format_messages(analysis=analysis_data)
            )
            
            import json
            return json.loads(response.content)
            
        except Exception as e:
            self.logger.warning(f"LLM architecture generation failed: {e}")
            return await self._fallback_architecture(analysis_data)
    
    async def _fallback_architecture(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule-based fallback architecture generation
        """
        entities = analysis_data.get("entities", [])
        use_cases = analysis_data.get("use_cases", [])
        complexity = analysis_data.get("complexity_score", 0.5)
        domain = analysis_data.get("domain", "web")
        
        # Simple rule-based architecture selection
        if complexity > 0.7 or len(entities) > 15:
            pattern = "microservices"
            tier = "large"
        elif complexity > 0.4:
            pattern = "layered"
            tier = "medium"
        else:
            pattern = "monolithic"
            tier = "small"
        
        return {
            "architecture_name": f"{domain.title()} Application Architecture",
            "description": f"Architecture for {domain} application with {len(entities)} entities",
            "primary_pattern": pattern,
            "secondary_patterns": ["mvc"] if pattern == "layered" else [],
            "presentation_tier": "React" if domain == "web" else "Native",
            "business_tier": "REST API",
            "data_tier": "Relational Database",
            "scalability_tier": tier,
            "complexity_level": complexity,
            "key_decisions": [
                {"decision": f"Use {pattern} pattern", "rationale": "Matches system complexity"}
            ],
            "assumptions": ["Standard web application", "Moderate user load"],
            "constraints": ["Budget constraints", "Time to market"],
            "risks": [
                {"risk": "Technology choice", "mitigation": "Use proven technologies"}
            ]
        }
    
    async def _enhance_architecture(self, 
                                   llm_result: Dict[str, Any], 
                                   analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance LLM result with rule-based improvements
        """
        # Validate and normalize pattern names
        pattern_mapping = {
            "layered": "layered",
            "microservices": "microservices", 
            "monolithic": "monolithic",
            "event_driven": "event_driven",
            "serverless": "serverless",
            "hexagonal": "hexagonal"
        }
        
        primary_pattern = llm_result.get("primary_pattern", "layered").lower()
        llm_result["primary_pattern"] = pattern_mapping.get(primary_pattern, "layered")
        
        # Validate scalability tier
        tier_mapping = {
            "small": "small",
            "medium": "medium", 
            "large": "large",
            "enterprise": "enterprise"
        }
        
        scalability_tier = llm_result.get("scalability_tier", "medium").lower()
        llm_result["scalability_tier"] = tier_mapping.get(scalability_tier, "medium")
        
        # Ensure complexity level is in valid range
        complexity = llm_result.get("complexity_level", 0.5)
        if not isinstance(complexity, (int, float)) or complexity < 0 or complexity > 1:
            llm_result["complexity_level"] = analysis_data.get("complexity_score", 0.5)
        
        # Add technology recommendations based on domain
        domain = analysis_data.get("domain", "web")
        self._enhance_technology_choices(llm_result, domain)
        
        return llm_result
    
    def _enhance_technology_choices(self, design: Dict[str, Any], domain: str):
        """
        Enhance technology choices based on domain and pattern
        """
        pattern = design.get("primary_pattern", "layered")
        
        # Presentation tier enhancements
        if not design.get("presentation_tier"):
            if domain == "web":
                design["presentation_tier"] = "React/Next.js"
            elif domain == "mobile":
                design["presentation_tier"] = "React Native / Flutter"
            else:
                design["presentation_tier"] = "Web Framework"
        
        # Business tier enhancements
        if not design.get("business_tier"):
            if pattern == "microservices":
                design["business_tier"] = "REST/GraphQL APIs with Service Mesh"
            else:
                design["business_tier"] = "FastAPI/Express.js"
        
        # Data tier enhancements
        if not design.get("data_tier"):
            if pattern == "microservices":
                design["data_tier"] = "Polyglot Persistence (SQL/NoSQL)"
            else:
                design["data_tier"] = "PostgreSQL with Redis Cache"
    
    def _create_architecture_object(self, 
                                   design_data: Dict[str, Any], 
                                   analysis_data: Dict[str, Any]) -> ArchitectureDesign:
        """
        Create ArchitectureDesign object from design data
        """
        # Parse pattern enums
        primary_pattern = ArchitecturePattern(design_data.get("primary_pattern", "layered"))
        
        secondary_patterns = []
        for pattern_name in design_data.get("secondary_patterns", []):
            try:
                secondary_patterns.append(ArchitecturePattern(pattern_name))
            except ValueError:
                pass  # Skip invalid pattern names
        
        # Parse scalability tier
        scalability_tier = ScalabilityTier(design_data.get("scalability_tier", "medium"))
        
        return ArchitectureDesign(
            design_id=str(uuid.uuid4()),
            name=design_data.get("architecture_name", "System Architecture"),
            description=design_data.get("description", ""),
            primary_pattern=primary_pattern,
            secondary_patterns=secondary_patterns,
            presentation_tier=design_data.get("presentation_tier"),
            business_tier=design_data.get("business_tier"),
            data_tier=design_data.get("data_tier"),
            scalability_tier=scalability_tier,
            complexity_level=design_data.get("complexity_level", 0.5),
            key_decisions=design_data.get("key_decisions", []),
            assumptions=design_data.get("assumptions", []),
            constraints=design_data.get("constraints", []),
            risks=design_data.get("risks", [])
        )