"""
Stack analysis engine for technology recommendation.
Combines knowledge search, template matching, and LLM reasoning.
"""

from typing import Dict, Any, List, Optional, Tuple
import asyncio
import json
import logging
from langchain_core.prompts import ChatPromptTemplate

from ..models.stack_models import (
    StackRecommendation, TechnologyChoice, StackCategory,
    ArchitectureContext, StackTemplate
)
from ..config.settings import settings
from ..utils.knowledge_search import KnowledgeSearcher
from ..utils.template_matcher import TemplateMatcher
from ..utils.compatibility_matrix import get_compatibility_matrix, CompatibilityLevel
from app.agents.shared.utils.llm_initialization import ensure_llm_instance

logger = logging.getLogger(__name__)


class StackAnalysisEngine:
    """Core engine for analyzing requirements and recommending technology stacks"""

    def __init__(self):
        # Use lazy initialization pattern to avoid event loop conflicts
        self.llm = None
        self._llm_manager = None
        self._fallback_settings = {
            'model': settings.effective_model,
            'temperature': settings.effective_temperature,
            'max_tokens': settings.effective_max_tokens,
            'api_key': settings.effective_api_key
        }

        # Try to prepare LLM manager for lazy initialization
        try:
            from app.core.llm_providers import DevStrategistLLMManager
            from app.core.config import settings as global_settings

            if hasattr(global_settings, 'LLM_API_KEY') and global_settings.LLM_API_KEY:
                self._llm_manager = DevStrategistLLMManager(
                    api_key=global_settings.LLM_API_KEY,
                    provider_name=getattr(global_settings, 'LLM_PROVIDER', None),
                    model=getattr(global_settings, 'LLM_MODEL', None),
                    temperature=getattr(global_settings, 'LLM_TEMPERATURE', settings.openai_temperature),
                    max_tokens=getattr(global_settings, 'LLM_MAX_TOKENS', settings.openai_max_tokens),
                    timeout=getattr(global_settings, 'LLM_TIMEOUT', 30)
                )
                logger.info("LLM manager prepared for lazy initialization")
        except Exception as e:
            logger.warning(f"Failed to prepare LLM manager: {e}")

        self.knowledge_searcher = KnowledgeSearcher()
        self.template_matcher = TemplateMatcher()
        self.compatibility_matrix = get_compatibility_matrix()

        # Setup prompts
        self._setup_prompts()

    async def _ensure_llm(self):
        """Ensure LLM is initialized (lazy initialization) using shared utility"""
        self.llm = await ensure_llm_instance(
            self.llm,
            self._llm_manager,
            self._fallback_settings
        )

    def _setup_prompts(self):
        """Setup LangChain prompts for stack analysis"""
        
        self.analysis_prompt = ChatPromptTemplate.from_template("""
You are a senior technology architect with 15+ years of experience in system design and technology selection.

Analyze the following architecture context and recommend a technology stack:

ARCHITECTURE CONTEXT:
- Domain: {domain}
- Scale: {scale}
- Components: {components}
- Patterns: {patterns}
- Quality Attributes: {quality_attributes}
- Constraints: {constraints}

KNOWLEDGE BASE INSIGHTS:
{knowledge_insights}

TEMPLATE SUGGESTIONS:
{template_suggestions}

Based on this information, recommend specific technologies for each category.
Consider team expertise, scalability, maintainability, and cost-effectiveness.

Respond with a JSON object matching this structure:
{{
    "backend": [
        {{
            "name": "technology_name",
            "version": "recommended_version",
            "category": "backend",
            "reason": "detailed_rationale",
            "alternatives": ["alt1", "alt2"],
            "confidence": 0.85
        }}
    ],
    "frontend": [...],
    "database": [...],
    "infrastructure": [...],
    "devops": [...],
    "monitoring": [...]
}}

Focus on proven, well-supported technologies that align with the architecture requirements.
""")
        
        self.refinement_prompt = ChatPromptTemplate.from_template("""
Review and refine the following technology stack recommendation:

ORIGINAL RECOMMENDATION:
{original_recommendation}

ARCHITECTURE CONTEXT:
{architecture_context}

VALIDATION CONCERNS:
{validation_concerns}

Please refine the recommendation addressing any validation concerns.
Ensure the stack is coherent, compatible, and optimized for the use case.

Return the refined recommendation in the same JSON format.
""")
    
    async def analyze_and_recommend(
        self,
        architecture: ArchitectureContext,
        requirements: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> StackRecommendation:
        """Main analysis workflow"""
        
        logger.info(f"Starting stack analysis for {architecture.domain} domain")
        
        try:
            # Step 1: Search knowledge base
            knowledge_insights = await self._search_knowledge_base(architecture)
            
            # Step 2: Match templates
            template_suggestions = await self._match_templates(architecture)
            
            # Step 3: Generate initial recommendation
            initial_recommendation = await self._generate_recommendation(
                architecture, knowledge_insights, template_suggestions
            )
            
            # Step 4: Validate and refine
            final_recommendation = await self._validate_and_refine(
                initial_recommendation, architecture
            )
            
            logger.info(f"Completed stack analysis with {len(self._count_technologies(final_recommendation))} technologies")
            
            return final_recommendation
            
        except Exception as e:
            logger.error(f"Stack analysis failed: {str(e)}")
            # Return fallback recommendation
            return await self._get_fallback_recommendation(architecture)
    
    async def _search_knowledge_base(self, architecture: ArchitectureContext) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant technology insights"""
        
        search_queries = [
            f"{architecture.domain} technology stack",
            f"{architecture.scale} scale architecture",
            *architecture.components[:3],  # Top 3 components
            *architecture.patterns[:2],    # Top 2 patterns
            *architecture.quality_attributes[:3]  # Top 3 quality attributes
        ]
        
        all_insights = []
        for query in search_queries:
            insights = await self.knowledge_searcher.search(query, limit=2)
            all_insights.extend(insights)
        
        # Deduplicate and limit results
        unique_insights = {
            insight["content"][:100]: insight 
            for insight in all_insights
        }
        
        return list(unique_insights.values())[:10]
    
    async def _match_templates(self, architecture: ArchitectureContext) -> List[StackTemplate]:
        """Find matching stack templates"""
        
        templates = await self.template_matcher.find_matching_templates(
            domain=architecture.domain,
            scale=architecture.scale,
            components=architecture.components,
            patterns=architecture.patterns
        )
        
        return templates[:3]  # Top 3 matches
    
    async def _generate_recommendation(
        self,
        architecture: ArchitectureContext,
        knowledge_insights: List[Dict[str, Any]],
        templates: List[StackTemplate]
    ) -> StackRecommendation:
        """Generate initial technology stack recommendation using LLM"""
        
        # Ensure LLM is initialized
        await self._ensure_llm()
        
        # Format inputs
        knowledge_text = self._format_knowledge_insights(knowledge_insights)
        template_text = self._format_template_suggestions(templates)
        
        # Prepare prompt variables
        prompt_vars = {
            "domain": architecture.domain,
            "scale": architecture.scale,
            "components": ", ".join(architecture.components),
            "patterns": ", ".join(architecture.patterns),
            "quality_attributes": ", ".join(architecture.quality_attributes),
            "constraints": json.dumps(architecture.constraints, indent=2),
            "knowledge_insights": knowledge_text,
            "template_suggestions": template_text
        }
        
        # Generate response
        chain = self.analysis_prompt | self.llm
        response = await chain.ainvoke(prompt_vars)
        
        # Parse JSON response
        try:
            recommendation_data = json.loads(response.content)
            return self._parse_recommendation(recommendation_data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Try to extract JSON from response
            return await self._extract_json_from_text(response.content)
    
    async def _validate_and_refine(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> StackRecommendation:
        """Validate recommendation and refine if needed"""
        
        validation_concerns = self._validate_recommendation(recommendation, architecture)
        
        if not validation_concerns:
            return recommendation
        
        # Ensure LLM is initialized for refinement
        await self._ensure_llm()
        
        # Refine recommendation
        refinement_vars = {
            "original_recommendation": recommendation.json(),
            "architecture_context": architecture.json(),
            "validation_concerns": "\n".join(validation_concerns)
        }
        
        chain = self.refinement_prompt | self.llm
        response = await chain.ainvoke(refinement_vars)
        
        try:
            refined_data = json.loads(response.content)
            return self._parse_recommendation(refined_data)
        except json.JSONDecodeError:
            logger.warning("Failed to parse refinement response, returning original")
            return recommendation
    
    def _validate_recommendation(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> List[str]:
        """Validate recommendation for common issues using compatibility matrix"""

        concerns = []

        # Check if essential categories are covered
        if not recommendation.backend and "api" in architecture.domain.lower():
            concerns.append("Backend framework missing for API-centric application")

        if not recommendation.frontend and "web" in architecture.domain.lower():
            concerns.append("Frontend framework missing for web application")

        if not recommendation.database and any("data" in comp.lower() for comp in architecture.components):
            concerns.append("Database missing despite data-related components")

        # Collect all technologies for compatibility validation
        all_techs = []
        for tech in recommendation.backend:
            all_techs.append((tech.name, tech.version))
        for tech in recommendation.frontend:
            all_techs.append((tech.name, tech.version))
        for tech in recommendation.database:
            all_techs.append((tech.name, tech.version))
        for tech in recommendation.infrastructure:
            all_techs.append((tech.name, tech.version))

        # Use compatibility matrix for comprehensive validation
        if len(all_techs) > 1:
            validation_result = self.compatibility_matrix.validate_stack(all_techs)

            # Add compatibility issues
            for issue in validation_result.get("issues", []):
                concerns.append(issue.get("message", "Compatibility issue detected"))

            # Add high-priority warnings
            for warning in validation_result.get("warnings", []):
                if warning.get("level") == "partial":
                    concerns.append(f"Warning: {warning.get('message', 'Compatibility warning')}")

        # Check for scale appropriateness
        if architecture.scale == "enterprise":
            tech_names = [
                tech.name.lower()
                for category in [recommendation.backend, recommendation.frontend, recommendation.database]
                for tech in category
            ]

            if "sqlite" in tech_names:
                concerns.append("SQLite not recommended for enterprise scale")

        # Check version recommendations
        for tech_name, tech_version in all_techs:
            version_info = self.compatibility_matrix.get_recommended_versions(tech_name)
            if version_info.get("status") != "unknown":
                lts = version_info.get("lts")
                if lts and tech_version and tech_version != lts:
                    min_rec = version_info.get("min_recommended", "")
                    if min_rec and tech_version < min_rec:
                        concerns.append(
                            f"{tech_name} version {tech_version} is below minimum recommended ({min_rec})"
                        )

        return concerns
    
    def _parse_recommendation(self, data: Dict[str, Any]) -> StackRecommendation:
        """Parse LLM response data into StackRecommendation"""
        
        parsed = {}
        
        for category in StackCategory:
            category_data = data.get(category.value, [])
            if isinstance(category_data, list):
                parsed[category.value] = [
                    TechnologyChoice(**tech_data) 
                    for tech_data in category_data
                    if isinstance(tech_data, dict)
                ]
            else:
                parsed[category.value] = []
        
        return StackRecommendation(**parsed)
    
    async def _extract_json_from_text(self, text: str) -> StackRecommendation:
        """Extract JSON from text response when direct parsing fails"""
        
        # Find JSON-like content between braces
        import re
        
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                return self._parse_recommendation(data)
            except json.JSONDecodeError:
                continue
        
        # Fallback to empty recommendation
        return StackRecommendation()
    
    async def _get_fallback_recommendation(self, architecture: ArchitectureContext) -> StackRecommendation:
        """Provide fallback recommendation when analysis fails"""
        
        # Use template matcher for basic recommendation
        templates = await self.template_matcher.find_matching_templates(
            domain=architecture.domain,
            scale=architecture.scale,
            components=architecture.components[:3]
        )
        
        if templates:
            return templates[0].technologies
        
        # Ultimate fallback - basic web stack
        return StackRecommendation(
            backend=[TechnologyChoice(
                name="FastAPI",
                version="0.109.0",
                category=StackCategory.BACKEND,
                reason="Modern, high-performance Python web framework",
                alternatives=["Django", "Flask"],
                confidence=0.7
            )],
            frontend=[TechnologyChoice(
                name="React",
                version="18.0",
                category=StackCategory.FRONTEND,
                reason="Popular, component-based frontend framework",
                alternatives=["Vue", "Angular"],
                confidence=0.7
            )],
            database=[TechnologyChoice(
                name="PostgreSQL",
                version="15.0",
                category=StackCategory.DATABASE,
                reason="Reliable, feature-rich relational database",
                alternatives=["MySQL", "MongoDB"],
                confidence=0.8
            )]
        )
    
    def _format_knowledge_insights(self, insights: List[Dict[str, Any]]) -> str:
        """Format knowledge insights for prompt"""
        
        if not insights:
            return "No specific insights found in knowledge base."
        
        formatted = []
        for insight in insights[:5]:  # Top 5 insights
            content = insight.get("content", "")[:200]  # Truncate
            source = insight.get("metadata", {}).get("url", "Unknown")
            formatted.append(f"- {content}... (Source: {source})")
        
        return "\n".join(formatted)
    
    def _format_template_suggestions(self, templates: List[StackTemplate]) -> str:
        """Format template suggestions for prompt"""
        
        if not templates:
            return "No matching templates found."
        
        formatted = []
        for template in templates:
            formatted.append(f"- {template.name}: {template.description}")
        
        return "\n".join(formatted)
    
    def _count_technologies(self, recommendation: StackRecommendation) -> int:
        """Count total technologies in recommendation"""
        
        return sum(
            len(getattr(recommendation, category.value, []))
            for category in StackCategory
        )