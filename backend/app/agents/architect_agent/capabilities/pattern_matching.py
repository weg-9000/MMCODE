"""Pattern Matching Engine for Architecture Agent"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncio

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from fastapi import HTTPException, status

from ..models.architecture_models import (
    ArchitecturalPattern, ArchitecturePattern, ArchitectureDesign
)
from ....core.exceptions import (
    DevStrategistException, ValidationException, LLMServiceException
)


class PatternMatchingEngine:
    """
    Engine for matching architectural patterns to requirements and context
    """
    
    def __init__(self, config: Dict[str, Any]):
        self._validate_config(config)
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize LLM with proper configuration
        try:
            self.llm = ChatOpenAI(
                model=config.get("openai_model", "gpt-4"),
                temperature=0.3,
                openai_api_key=config.get("openai_api_key"),
                timeout=config.get("llm_timeout", 60),
                max_retries=config.get("llm_max_retries", 3)
            )
        except Exception as e:
            raise LLMServiceException(
                message="Failed to initialize LLM client",
                details={"error": str(e), "config": {k: v for k, v in config.items() if k != "openai_api_key"}}
            )
        
        # Pattern recommendation prompt
        self.pattern_prompt = ChatPromptTemplate.from_template(
            """You are a senior software architect specializing in architectural patterns.

Analyze the following architecture and analysis data to recommend appropriate architectural patterns.

Architecture Context:
{architecture}

Analysis Data:
{analysis}

Based on the analysis, recommend architectural patterns considering:
1. System complexity and scale
2. Performance requirements
3. Team structure and expertise
4. Maintenance and evolution needs
5. Business constraints

Output JSON format:
{{
    "recommended_patterns": [
        {{
            "pattern_name": "Name of the pattern",
            "pattern_type": "layered|microservices|monolithic|event_driven|serverless|hexagonal|cqrs|saga|mvc",
            "confidence_score": 0.0-1.0,
            "rationale": "Why this pattern is recommended",
            "benefits": ["benefit1", "benefit2"],
            "trade_offs": ["tradeoff1", "tradeoff2"],
            "use_cases": ["usecase1", "usecase2"],
            "implementation_complexity": 0.0-1.0
        }}
    ],
    "pattern_compatibility": {{
        "primary_pattern": "main_pattern_name",
        "compatible_patterns": ["pattern1", "pattern2"],
        "conflicting_patterns": ["pattern3", "pattern4"]
    }},
    "implementation_guidance": {{
        "priority_order": ["pattern1", "pattern2"],
        "phased_approach": ["Phase 1: pattern1", "Phase 2: pattern2"],
        "risk_factors": ["risk1", "risk2"]
    }}
}}

Focus on practical, proven patterns that match the system's requirements and constraints."""
        )
    
    async def recommend_patterns(self, 
                               architecture: ArchitectureDesign, 
                               analysis_data: Dict[str, Any]) -> List[ArchitecturalPattern]:
        """
        Recommend architectural patterns based on architecture design and analysis data
        """
        self.logger.info("Starting pattern recommendation process")
        
        try:
            # Generate pattern recommendations using LLM
            llm_result = await self._generate_patterns_llm(architecture, analysis_data)
            
            # Convert to ArchitecturalPattern objects
            patterns = self._create_pattern_objects(llm_result)
            
            # Apply rule-based validation and enhancement
            validated_patterns = await self._validate_and_enhance_patterns(patterns, architecture, analysis_data)
            
            self.logger.info(f"Generated {len(validated_patterns)} pattern recommendations")
            return validated_patterns
            
        except LLMServiceException:
            raise  # Re-raise LLM-specific exceptions
        except ValidationException:
            raise  # Re-raise validation exceptions
        except Exception as e:
            self.logger.error(f"Pattern recommendation failed: {e}")
            raise DevStrategistException(
                message="Pattern recommendation process failed",
                details={"error": str(e), "architecture_id": getattr(architecture, 'id', 'unknown')},
                error_code="PATTERN_RECOMMENDATION_FAILED"
            ) from e
    
    async def explain_recommendations(self, patterns: List[ArchitecturalPattern]) -> Dict[str, str]:
        """
        Generate detailed explanations for pattern recommendations
        """
        explanations = {}
        
        for pattern in patterns:
            explanation = {
                "overview": f"{pattern.name} is recommended because {pattern.context}",
                "benefits": f"Key benefits include: {', '.join(pattern.benefits)}",
                "considerations": f"Important trade-offs: {', '.join(pattern.trade_offs)}",
                "implementation": f"Implementation complexity: {pattern.implementation_complexity:.1f}/1.0"
            }
            explanations[pattern.name] = explanation
        
        return explanations
    
    async def prioritize_patterns(self, patterns: List[ArchitecturalPattern]) -> List[Dict[str, Any]]:
        """
        Prioritize patterns based on implementation feasibility and impact
        """
        prioritized = []
        
        for pattern in patterns:
            priority_score = self._calculate_priority_score(pattern)
            prioritized.append({
                "pattern": pattern,
                "priority_score": priority_score,
                "implementation_order": len(prioritized) + 1,
                "rationale": f"Priority score {priority_score:.2f} based on complexity and benefits"
            })
        
        # Sort by priority score (higher is better)
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
        
        # Update implementation order
        for i, item in enumerate(prioritized):
            item["implementation_order"] = i + 1
        
        return prioritized
    
    async def check_pattern_compatibility(self, patterns: List[ArchitecturalPattern]) -> Dict[str, Any]:
        """
        Check compatibility between multiple patterns
        """
        if len(patterns) < 2:
            return {"status": "single_pattern", "compatibility": "N/A"}
        
        compatibility_matrix = {}
        conflicts = []
        synergies = []
        
        # Define known pattern relationships
        pattern_relationships = {
            "layered": {"compatible": ["mvc", "mvp", "hexagonal"], "conflicts": ["microservices"]},
            "microservices": {"compatible": ["event_driven", "cqrs", "saga"], "conflicts": ["monolithic", "layered"]},
            "event_driven": {"compatible": ["microservices", "cqrs"], "conflicts": ["monolithic"]},
            "hexagonal": {"compatible": ["layered", "cqrs"], "conflicts": []},
        }
        
        for i, pattern1 in enumerate(patterns):
            for j, pattern2 in enumerate(patterns[i+1:], i+1):
                pattern1_type = pattern1.pattern_type.value if pattern1.pattern_type else "unknown"
                pattern2_type = pattern2.pattern_type.value if pattern2.pattern_type else "unknown"
                
                is_compatible = self._check_pattern_pair_compatibility(
                    pattern1_type, pattern2_type, pattern_relationships
                )
                
                if is_compatible:
                    synergies.append(f"{pattern1.name} + {pattern2.name}")
                else:
                    conflicts.append(f"{pattern1.name} conflicts with {pattern2.name}")
        
        return {
            "total_patterns": len(patterns),
            "conflicts": conflicts,
            "synergies": synergies,
            "overall_compatibility": "Good" if len(conflicts) == 0 else "Moderate" if len(conflicts) < len(synergies) else "Poor"
        }
    
    async def _generate_patterns_llm(self, 
                                   architecture: ArchitectureDesign, 
                                   analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to generate pattern recommendations
        """
        try:
            response = await self.llm.ainvoke(
                self.pattern_prompt.format_messages(
                    architecture=architecture.to_dict(),
                    analysis=analysis_data
                )
            )
            
            try:
                return json.loads(response.content)
            except json.JSONDecodeError as e:
                raise ValidationException(
                    message="Invalid JSON response from LLM",
                    details={"response_content": response.content[:500], "error": str(e)}
                )
            
        except (LLMServiceException, ValidationException):
            raise  # Re-raise known exceptions
        except Exception as e:
            self.logger.warning(f"LLM pattern generation failed: {e}")
            raise LLMServiceException(
                message="LLM pattern generation failed",
                details={"error": str(e), "architecture_complexity": architecture.complexity_level}
            ) from e
    
    def _create_pattern_objects(self, llm_result: Dict[str, Any]) -> List[ArchitecturalPattern]:
        """
        Convert LLM result to ArchitecturalPattern objects
        """
        patterns = []
        
        for pattern_data in llm_result.get("recommended_patterns", []):
            try:
                pattern_type = ArchitecturePattern(pattern_data.get("pattern_type", "layered"))
                
                pattern = ArchitecturalPattern(
                    name=pattern_data.get("pattern_name", "Unknown Pattern"),
                    pattern_type=pattern_type,
                    description=pattern_data.get("rationale", "Pattern recommendation"),
                    benefits=pattern_data.get("benefits", []),
                    trade_offs=pattern_data.get("trade_offs", []),
                    use_cases=pattern_data.get("use_cases", []),
                    context=pattern_data.get("rationale", ""),
                    implementation_complexity=pattern_data.get("implementation_complexity", 0.5)
                )
                patterns.append(pattern)
                
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Failed to create pattern object: {e}")
                # Continue processing other patterns instead of raising exception
                continue
        
        if not patterns:
            raise ValidationException(
                message="No valid patterns could be generated",
                details={"llm_result": llm_result}
            )
        
        return patterns
    
    async def _validate_and_enhance_patterns(self, 
                                           patterns: List[ArchitecturalPattern],
                                           architecture: ArchitectureDesign,
                                           analysis_data: Dict[str, Any]) -> List[ArchitecturalPattern]:
        """
        Validate and enhance patterns with rule-based logic
        """
        enhanced_patterns = []
        
        for pattern in patterns:
            # Validate pattern against architecture constraints
            if self._is_pattern_suitable(pattern, architecture, analysis_data):
                # Enhance pattern with additional context
                enhanced_pattern = self._enhance_pattern_context(pattern, architecture, analysis_data)
                enhanced_patterns.append(enhanced_pattern)
            else:
                self.logger.info(f"Pattern {pattern.name} filtered out due to constraints")
        
        return enhanced_patterns
    
    def _is_pattern_suitable(self, 
                           pattern: ArchitecturalPattern,
                           architecture: ArchitectureDesign,
                           analysis_data: Dict[str, Any]) -> bool:
        """
        Check if pattern is suitable for the given architecture and analysis
        """
        # Check complexity alignment
        if pattern.implementation_complexity > 0.8 and architecture.complexity_level < 0.5:
            return False
        
        # Check scalability alignment
        if pattern.pattern_type == ArchitecturePattern.MICROSERVICES and architecture.scalability_tier.value == "small":
            return False
        
        # Check entity count for microservices
        entities = analysis_data.get("entities", [])
        if pattern.pattern_type == ArchitecturePattern.MICROSERVICES and len(entities) < 5:
            return False
        
        return True
    
    def _enhance_pattern_context(self, 
                               pattern: ArchitecturalPattern,
                               architecture: ArchitectureDesign,
                               analysis_data: Dict[str, Any]) -> ArchitecturalPattern:
        """
        Enhance pattern with additional context and recommendations
        """
        # Add architecture-specific benefits
        enhanced_benefits = pattern.benefits.copy()
        
        if architecture.scalability_tier.value in ["large", "enterprise"]:
            enhanced_benefits.append("Supports high scalability requirements")
        
        if architecture.complexity_level > 0.7:
            enhanced_benefits.append("Handles complex business logic effectively")
        
        # Add context-specific use cases
        enhanced_use_cases = pattern.use_cases.copy()
        domain = analysis_data.get("domain", "general")
        enhanced_use_cases.append(f"Suitable for {domain} applications")
        
        # Return enhanced pattern (creating new instance)
        return ArchitecturalPattern(
            name=pattern.name,
            pattern_type=pattern.pattern_type,
            description=pattern.description,
            benefits=enhanced_benefits,
            trade_offs=pattern.trade_offs,
            use_cases=enhanced_use_cases,
            context=pattern.context,
            implementation_complexity=pattern.implementation_complexity
        )
    
    async def _fallback_pattern_recommendation(self, 
                                             architecture: ArchitectureDesign,
                                             analysis_data: Dict[str, Any]) -> List[ArchitecturalPattern]:
        """
        Fallback rule-based pattern recommendation
        """
        patterns = []
        
        # Basic pattern selection based on complexity and scale
        if architecture.complexity_level > 0.7 or architecture.scalability_tier.value in ["large", "enterprise"]:
            # High complexity - recommend microservices
            patterns.append(ArchitecturalPattern(
                name="Microservices Architecture",
                pattern_type=ArchitecturePattern.MICROSERVICES,
                description="Distributed system with independent services",
                benefits=["High scalability", "Technology diversity", "Independent deployment"],
                trade_offs=["Increased complexity", "Network latency", "Data consistency challenges"],
                use_cases=["Large-scale applications", "High-traffic systems", "Enterprise solutions"],
                context="High complexity and scalability requirements",
                implementation_complexity=0.8
            ))
        elif architecture.complexity_level > 0.4:
            # Medium complexity - recommend layered architecture
            patterns.append(ArchitecturalPattern(
                name="Layered Architecture",
                pattern_type=ArchitecturePattern.LAYERED,
                description="Hierarchical organization of system components",
                benefits=["Clear separation of concerns", "Easy to understand", "Good for teams"],
                trade_offs=["Can become monolithic", "Performance overhead", "Tight coupling"],
                use_cases=["Business applications", "CRUD systems", "Traditional web apps"],
                context="Balanced complexity and maintainability",
                implementation_complexity=0.4
            ))
        else:
            # Low complexity - recommend monolithic
            patterns.append(ArchitecturalPattern(
                name="Modular Monolith",
                pattern_type=ArchitecturePattern.MONOLITHIC,
                description="Single deployable unit with modular internal structure",
                benefits=["Simple deployment", "Easy testing", "Lower operational complexity"],
                trade_offs=["Limited scalability", "Technology lock-in", "Can become unwieldy"],
                use_cases=["Startups", "Simple applications", "MVP development"],
                context="Simple requirements with future growth potential",
                implementation_complexity=0.2
            ))
        
        return patterns
    
    async def _fallback_pattern_generation(self, 
                                         architecture: ArchitectureDesign,
                                         analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule-based fallback pattern generation
        """
        return {
            "recommended_patterns": [
                {
                    "pattern_name": "Layered Architecture",
                    "pattern_type": "layered",
                    "confidence_score": 0.7,
                    "rationale": "Fallback recommendation for balanced approach",
                    "benefits": ["Clear separation", "Maintainable", "Well understood"],
                    "trade_offs": ["Can become monolithic", "Performance overhead"],
                    "use_cases": ["Business applications", "Web systems"],
                    "implementation_complexity": 0.4
                }
            ],
            "pattern_compatibility": {
                "primary_pattern": "layered",
                "compatible_patterns": ["mvc"],
                "conflicting_patterns": []
            }
        }
    
    def _calculate_priority_score(self, pattern: ArchitecturalPattern) -> float:
        """
        Calculate priority score for pattern implementation
        """
        # Simple scoring based on benefits vs complexity
        benefit_score = len(pattern.benefits) * 0.2
        complexity_penalty = pattern.implementation_complexity * 0.3
        
        return max(0.1, benefit_score - complexity_penalty + 0.5)
    
    def _check_pattern_pair_compatibility(self, 
                                        pattern1: str, 
                                        pattern2: str, 
                                        relationships: Dict[str, Any]) -> bool:
        """
        Check if two patterns are compatible
        """
        if pattern1 in relationships:
            return pattern2 not in relationships[pattern1].get("conflicts", [])
        return True  # Default to compatible if no specific relationship defined
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration parameters
        """
        required_keys = ["openai_api_key"]
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            raise ValidationException(
                message="Missing required configuration parameters",
                details={"missing_keys": missing_keys}
            )
        
        # Validate API key format (basic check)
        api_key = config.get("openai_api_key", "")
        if not api_key or not api_key.startswith(("sk-", "sk-proj-")):
            raise ValidationException(
                message="Invalid OpenAI API key format",
                details={"expected_format": "sk-* or sk-proj-*"}
            )