"""Requirement Analysis Engine"""

import re
import logging
from typing import Any, Dict, List, Set
from dataclasses import dataclass
from datetime import datetime, timezone


from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage

from ..models.analysis_models import AnalysisResult, Entity, UseCase, QualityAttribute, AmbiguousItem


class RequirementAnalysisEngine:
    """
    Advanced requirement analysis engine for extracting structured information
    from natural language requirements.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize LLM with unified provider support
        self._initialize_llm(config)

    def _initialize_llm(self, config: Dict[str, Any]):
        """Initialize LLM with unified provider system and fallback compatibility"""
        try:
            # Modern: Check if we have a unified LLM manager or provider
            if hasattr(config, 'get_llm_config') and callable(config.get_llm_config):
                # AgentConfig with unified LLM support
                from app.core.llm_providers import DevStrategistLLMManager 
                llm_config = config.get_llm_config()
                llm_manager = DevStrategistLLMManager(**llm_config)
                
                # Note: We'll get the LLM instance synchronously for now
                # In a production system, you'd want to handle this asynchronously
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    self.llm = loop.run_until_complete(llm_manager.get_llm_instance())
                except RuntimeError:
                    # If no event loop, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    self.llm = loop.run_until_complete(llm_manager.get_llm_instance())
                    
                self.logger.info("LLM initialized with unified provider system")
                
            else:
                # Legacy: Fallback to OpenAI direct initialization
                self.llm = ChatOpenAI(
                    model=config.get("llm_model"),
                    temperature=config.get("temperature", config.get("llm_temperature", 0.1)),
                    openai_api_key=config.get("llm_api_key")
                )
                self.logger.info("LLM initialized with legacy OpenAI configuration")
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize with unified provider, falling back to OpenAI: {e}")
            # Ultimate fallback: Basic OpenAI initialization
            self.llm = ChatOpenAI(
                model=config.get("openai_model", "gpt-3.5-turbo"),
                temperature=0.1,
                openai_api_key=config.get("openai_api_key")
            )
        
        # Analysis prompt template
        self.analysis_prompt = ChatPromptTemplate.from_template(
            """You are a senior software requirements analyst. Analyze the following requirements and extract structured information.

Requirements:
{requirements}

Extract the following information in JSON format:

1. **Entities**: Business objects, data models, core concepts (use PascalCase)
2. **Use Cases**: User actions, system behaviors, functional requirements (use action-oriented names)
3. **Quality Attributes**: Non-functional requirements like performance, security, scalability
4. **Technical Context**: Any mentioned technologies, frameworks, platforms
5. **Constraints**: Limitations, restrictions, compliance requirements  
6. **Ambiguous Items**: Unclear or incomplete requirements that need clarification

Output JSON format:
{{
    "entities": [
        {{"name": "EntityName", "description": "Brief description", "attributes": ["attr1", "attr2"]}}
    ],
    "use_cases": [
        {{"name": "ActionName", "description": "What the system should do", "actors": ["User", "Admin"], "priority": "high|medium|low"}}
    ],
    "quality_attributes": [
        {{"name": "performance|security|usability|etc", "requirement": "Specific requirement", "measurable": "Quantifiable criteria if any"}}
    ],
    "technical_context": [
        {{"technology": "TechName", "context": "How it's mentioned", "requirement_type": "required|preferred|mentioned"}}
    ],
    "constraints": [
        {{"type": "budget|time|platform|compliance|etc", "description": "Constraint description"}}
    ],
    "ambiguous_items": [
        {{"text": "Ambiguous text from requirements", "question": "Clarifying question", "impact": "Why this needs clarification"}}
    ],
    "complexity_score": 0.1-1.0,
    "domain": "web|mobile|desktop|embedded|ai|etc"
}}

Focus on:
- Complete entity extraction with relationships
- Actionable use cases with clear actors
- Measurable quality attributes
- Technical stack inference
- Identifying missing information"""
        )
        
        # Entity extraction patterns
        self.entity_patterns = [
            r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b',  # PascalCase entities
            r'\b(user|customer|admin|product|order|payment|account|profile|setting)\b',  # Common entities
        ]
        
        # Use case action verbs
        self.action_verbs = {
            'create', 'add', 'register', 'sign up', 'build', 'generate',
            'update', 'edit', 'modify', 'change', 'configure',
            'delete', 'remove', 'cancel', 'deactivate',
            'view', 'display', 'show', 'list', 'search', 'filter',
            'login', 'authenticate', 'authorize', 'access',
            'upload', 'download', 'import', 'export', 'sync',
            'send', 'receive', 'notify', 'alert', 'email'
        }
    
    async def analyze(self, requirements: str) -> AnalysisResult:
        """
        Main analysis method that processes requirements text
        """
        self.logger.info("Starting requirement analysis")
        
        try:
            # Preprocess requirements
            cleaned_requirements = self._preprocess_requirements(requirements)
            
            # LLM-based analysis
            llm_result = await self._llm_analysis(cleaned_requirements)
            
            # Rule-based validation and enhancement
            enhanced_result = await self._enhance_analysis(llm_result, cleaned_requirements)
            
            # Calculate metadata
            metadata = self._calculate_analysis_metadata(cleaned_requirements, enhanced_result)
            
            # Create final analysis result
            analysis_result = AnalysisResult(
                entities=enhanced_result.get("entities", []),
                use_cases=enhanced_result.get("use_cases", []),
                quality_attributes=enhanced_result.get("quality_attributes", []),
                technical_context=enhanced_result.get("technical_context", []),
                constraints=enhanced_result.get("constraints", []),
                ambiguous_items=enhanced_result.get("ambiguous_items", []),
                complexity_score=enhanced_result.get("complexity_score", 0.5),
                domain=enhanced_result.get("domain", "web"),
                metadata=metadata
            )
            
            self.logger.info(f"Analysis completed: {len(analysis_result.entities)} entities, {len(analysis_result.use_cases)} use cases")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise
    
    def _preprocess_requirements(self, requirements: str) -> str:
        """
        Clean and normalize requirements text
        """
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', requirements.strip())
        
        # Normalize bullet points
        cleaned = re.sub(r'[•\-\*]\s*', '- ', cleaned)
        
        # Ensure proper sentence endings
        cleaned = re.sub(r'([a-z])\s*\n\s*([A-Z])', r'\1. \2', cleaned)
        
        return cleaned
    
    async def _llm_analysis(self, requirements: str) -> Dict[str, Any]:
        """
        Use LLM for initial structured analysis
        """
        import json
        
        try:
            response = await self.llm.ainvoke(
                self.analysis_prompt.format_messages(requirements=requirements)
            )
            
            # Parse JSON response
            result = json.loads(response.content)
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse LLM JSON response: {e}")
            # Fallback to rule-based analysis
            return await self._fallback_analysis(requirements)
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            return await self._fallback_analysis(requirements)
    
    async def _fallback_analysis(self, requirements: str) -> Dict[str, Any]:
        """
        Rule-based fallback analysis when LLM fails
        """
        self.logger.info("Using fallback rule-based analysis")
        
        # Simple entity extraction
        entities = []
        for pattern in self.entity_patterns:
            matches = re.findall(pattern, requirements, re.IGNORECASE)
            for match in set(matches):
                if len(match) > 2 and match.lower() not in {'the', 'and', 'for', 'with'}:
                    entities.append({
                        "name": match.title(),
                        "description": f"Entity extracted from requirements",
                        "attributes": []
                    })
        
        # Simple use case extraction based on action verbs
        use_cases = []
        sentences = requirements.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for verb in self.action_verbs:
                if verb in sentence_lower:
                    use_cases.append({
                        "name": f"{verb.title()} {self._extract_object(sentence)}",
                        "description": sentence.strip(),
                        "actors": ["User"],
                        "priority": "medium"
                    })
                    break
        
        return {
            "entities": entities[:10],  # Limit results
            "use_cases": use_cases[:10],
            "quality_attributes": [],
            "technical_context": [],
            "constraints": [],
            "ambiguous_items": [],
            "complexity_score": 0.5,
            "domain": "web"
        }
    
    def _extract_object(self, sentence: str) -> str:
        """
        Extract object from sentence for use case naming
        """
        words = sentence.split()
        if len(words) > 2:
            return ' '.join(words[-3:]).title()
        return "Object"
    
    async def _enhance_analysis(self, llm_result: Dict[str, Any], requirements: str) -> Dict[str, Any]:
        """
        Enhance LLM analysis with rule-based validation
        """
        # Validate entity names (PascalCase)
        if "entities" in llm_result:
            for entity in llm_result["entities"]:
                if isinstance(entity, dict) and "name" in entity:
                    # Ensure PascalCase
                    entity["name"] = ''.join(word.capitalize() for word in entity["name"].split())
        
        # Validate use case priorities
        if "use_cases" in llm_result:
            for use_case in llm_result["use_cases"]:
                if isinstance(use_case, dict):
                    priority = use_case.get("priority", "medium").lower()
                    if priority not in ["high", "medium", "low"]:
                        use_case["priority"] = "medium"
        
        # Ensure complexity score is in valid range
        complexity = llm_result.get("complexity_score", 0.5)
        if not isinstance(complexity, (int, float)) or complexity < 0 or complexity > 1:
            llm_result["complexity_score"] = 0.5
        
        return llm_result
    
    def _calculate_analysis_metadata(self, requirements: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate analysis metadata and statistics
        """
        return {
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "requirements_length": len(requirements),
            "word_count": len(requirements.split()),
            "sentence_count": len([s for s in requirements.split('.') if s.strip()]),
            "entity_count": len(analysis.get("entities", [])),
            "use_case_count": len(analysis.get("use_cases", [])),
            "quality_attribute_count": len(analysis.get("quality_attributes", [])),
            "ambiguous_item_count": len(analysis.get("ambiguous_items", [])),
            "analysis_version": "1.0.0"
        }