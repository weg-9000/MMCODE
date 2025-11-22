"""Component Modeling Engine for Architecture Agent"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json
import asyncio

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from fastapi import HTTPException, status

from ..models.architecture_models import (
    Component, ComponentType, ArchitecturalPattern, ArchitectureDesign
)
from ....core.exceptions import (
    DevStrategistException, ValidationException, LLMServiceException
)


class ComponentModelingEngine:
    """
    Engine for modeling system components based on architecture and requirements
    """
    
    def __init__(self, config: Dict[str, Any]):
        self._validate_config(config)
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize LLM with proper configuration
        try:
            self.llm = ChatOpenAI(
                model=config.get("llm_model"),
                temperature=0.2,
                openai_api_key=config.get("llm_api_key"),
                timeout=config.get("llm_timeout", 60),
                max_retries=config.get("llm_max_retries", 3)
            )
        except Exception as e:
            raise LLMServiceException(
                message="Failed to initialize LLM client",
                details={"error": str(e), "config": {k: v for k, v in config.items() if k != "openai_api_key"}}
            )
        
        # Component modeling prompt
        self.modeling_prompt = ChatPromptTemplate.from_template(
            """You are a senior software architect specializing in system component design.

Design system components based on the architecture and patterns provided.

Architecture Design:
{architecture}

Architectural Patterns:
{patterns}

Analysis Context:
{analysis}

Create detailed component specifications considering:
1. Business entities and their relationships
2. Use cases and functional requirements
3. Architectural patterns and constraints
4. Quality attributes (performance, security, scalability)
5. Technology stack compatibility

Output JSON format:
{{
    "components": [
        {{
            "name": "Component Name",
            "component_type": "presentation|business_logic|data_access|integration|infrastructure|security|monitoring",
            "description": "Detailed component description",
            "responsibilities": ["responsibility1", "responsibility2"],
            "interfaces": ["interface1", "interface2"],
            "dependencies": ["dependency1", "dependency2"],
            "technologies": ["tech1", "tech2"],
            "data_entities": ["entity1", "entity2"],
            "quality_attributes": {{
                "performance": "performance requirement",
                "security": "security requirement",
                "scalability": "scalability requirement"
            }}
        }}
    ],
    "component_relationships": [
        {{
            "source": "ComponentA",
            "target": "ComponentB", 
            "relationship_type": "depends_on|uses|publishes_to|subscribes_from",
            "interface": "Interface specification",
            "data_flow": "Data flow description"
        }}
    ],
    "deployment_considerations": {{
        "deployment_units": ["unit1", "unit2"],
        "scaling_strategy": "horizontal|vertical|auto",
        "monitoring_points": ["metric1", "metric2"]
    }}
}}

Focus on creating cohesive components with clear responsibilities and minimal coupling."""
        )
    
    async def model_components(self, 
                             architecture: ArchitectureDesign,
                             patterns: List[ArchitecturalPattern]) -> List[Component]:
        """
        Model system components based on architecture design and patterns
        """
        self.logger.info("Starting component modeling process")
        
        try:
            # Generate components using LLM
            llm_result = await self._generate_components_llm(architecture, patterns)
            
            # Convert to Component objects
            components = self._create_component_objects(llm_result)
            
            # Apply rule-based validation and enhancement
            validated_components = await self._validate_and_enhance_components(
                components, architecture, patterns
            )
            
            self.logger.info(f"Generated {len(validated_components)} system components")
            return validated_components
            
        except LLMServiceException:
            raise  # Re-raise LLM-specific exceptions
        except ValidationException:
            raise  # Re-raise validation exceptions
        except Exception as e:
            self.logger.error(f"Component modeling failed: {e}")
            raise DevStrategistException(
                message="Component modeling process failed",
                details={"error": str(e), "architecture_id": getattr(architecture, 'id', 'unknown')},
                error_code="COMPONENT_MODELING_FAILED"
            ) from e
    
    async def derive_components_from_entities(self, 
                                            entities: List[str],
                                            use_cases: List[str],
                                            architecture: ArchitectureDesign) -> List[Component]:
        """
        Derive components directly from business entities and use cases
        """
        components = []
        
        # Generate data access components for each major entity
        for entity in entities:
            if entity.strip():
                data_component = Component(
                    name=f"{entity.title().replace(' ', '')}Repository",
                    component_type=ComponentType.DATA_ACCESS,
                    description=f"Data access layer for {entity} entity",
                    responsibilities=[
                        f"CRUD operations for {entity}",
                        f"{entity} data validation",
                        f"{entity} persistence management"
                    ],
                    interfaces=[
                        f"I{entity.title().replace(' ', '')}Repository",
                        f"{entity.title().replace(' ', '')}DataModel"
                    ],
                    dependencies=["Database", "ORM Framework"],
                    technologies=["SQLAlchemy", "PostgreSQL"],
                    data_entities=[entity],
                    quality_attributes={
                        "performance": "Sub-second query response",
                        "consistency": "ACID compliance",
                        "scalability": "Handle concurrent access"
                    }
                )
                components.append(data_component)
        
        # Generate business logic components based on use cases
        for use_case in use_cases[:5]:  # Limit to avoid too many components
            if use_case.strip():
                service_name = self._derive_service_name(use_case)
                business_component = Component(
                    name=f"{service_name}Service",
                    component_type=ComponentType.BUSINESS_LOGIC,
                    description=f"Business logic for {use_case}",
                    responsibilities=[
                        f"Implement {use_case} logic",
                        "Business rule validation",
                        "Transaction coordination"
                    ],
                    interfaces=[f"I{service_name}Service"],
                    dependencies=self._derive_dependencies(use_case, entities),
                    technologies=["FastAPI", "Pydantic"],
                    data_entities=self._extract_related_entities(use_case, entities),
                    quality_attributes={
                        "performance": "Low latency processing",
                        "reliability": "High availability",
                        "maintainability": "Clean code practices"
                    }
                )
                components.append(business_component)
        
        # Add standard infrastructure components
        infrastructure_components = self._generate_infrastructure_components(architecture)
        components.extend(infrastructure_components)
        
        return components
    
    async def optimize_component_structure(self, 
                                         components: List[Component],
                                         architecture: ArchitectureDesign) -> List[Component]:
        """
        Optimize component structure for better cohesion and coupling
        """
        optimized_components = []
        
        # Group related components
        component_groups = self._group_related_components(components)
        
        # Optimize each group
        for group in component_groups:
            if len(group) > 1:
                # Consider merging highly coupled components
                merged_component = self._consider_component_merge(group, architecture)
                if merged_component:
                    optimized_components.append(merged_component)
                else:
                    optimized_components.extend(group)
            else:
                optimized_components.extend(group)
        
        # Validate final structure
        return self._validate_component_structure(optimized_components, architecture)
    
    async def _generate_components_llm(self, 
                                     architecture: ArchitectureDesign,
                                     patterns: List[ArchitecturalPattern]) -> Dict[str, Any]:
        """
        Use LLM to generate component specifications
        """
        try:
            patterns_data = [pattern.to_dict() for pattern in patterns]
            
            response = await self.llm.ainvoke(
                self.modeling_prompt.format_messages(
                    architecture=architecture.to_dict(),
                    patterns=patterns_data,
                    analysis={"domain": "system", "complexity": architecture.complexity_level}
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
            self.logger.warning(f"LLM component generation failed: {e}")
            raise LLMServiceException(
                message="LLM component generation failed",
                details={"error": str(e), "architecture_complexity": architecture.complexity_level}
            ) from e
    
    def _create_component_objects(self, llm_result: Dict[str, Any]) -> List[Component]:
        """
        Convert LLM result to Component objects
        """
        components = []
        
        for comp_data in llm_result.get("components", []):
            try:
                component_type = ComponentType(comp_data.get("component_type", "business_logic"))
                
                component = Component(
                    name=comp_data.get("name", "Unknown Component"),
                    component_type=component_type,
                    description=comp_data.get("description", "Component description"),
                    responsibilities=comp_data.get("responsibilities", []),
                    interfaces=comp_data.get("interfaces", []),
                    dependencies=comp_data.get("dependencies", []),
                    technologies=comp_data.get("technologies", []),
                    data_entities=comp_data.get("data_entities", []),
                    quality_attributes=comp_data.get("quality_attributes", {})
                )
                components.append(component)
                
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Failed to create component object: {e}")
                continue
        
        if not components:
            raise ValidationException(
                message="No valid components could be generated",
                details={"llm_result": llm_result}
            )
        
        return components
    
    async def _validate_and_enhance_components(self, 
                                             components: List[Component],
                                             architecture: ArchitectureDesign,
                                             patterns: List[ArchitecturalPattern]) -> List[Component]:
        """
        Validate and enhance components with additional context
        """
        enhanced_components = []
        
        for component in components:
            # Validate component design
            if self._is_component_well_designed(component, architecture):
                # Enhance component with pattern-specific details
                enhanced_component = self._enhance_component(component, architecture, patterns)
                enhanced_components.append(enhanced_component)
            else:
                self.logger.info(f"Component {component.name} needs redesign")
                # Try to fix common issues
                fixed_component = self._fix_component_issues(component, architecture)
                enhanced_components.append(fixed_component)
        
        return enhanced_components
    
    def _is_component_well_designed(self, 
                                  component: Component,
                                  architecture: ArchitectureDesign) -> bool:
        """
        Check if component follows good design principles
        """
        # Check if component has clear responsibilities
        if not component.responsibilities or len(component.responsibilities) == 0:
            return False
        
        # Check for reasonable number of responsibilities (SRP)
        if len(component.responsibilities) > 5:
            return False
        
        # Check if component has appropriate interfaces
        if component.component_type in [ComponentType.BUSINESS_LOGIC, ComponentType.DATA_ACCESS]:
            if not component.interfaces:
                return False
        
        return True
    
    def _enhance_component(self, 
                         component: Component,
                         architecture: ArchitectureDesign,
                         patterns: List[ArchitecturalPattern]) -> Component:
        """
        Enhance component with architecture and pattern-specific details
        """
        enhanced_responsibilities = component.responsibilities.copy()
        enhanced_technologies = component.technologies.copy()
        enhanced_quality_attributes = component.quality_attributes.copy()
        
        # Add pattern-specific enhancements
        for pattern in patterns:
            if pattern.pattern_type.value == "microservices":
                if component.component_type == ComponentType.BUSINESS_LOGIC:
                    enhanced_responsibilities.append("Service health monitoring")
                    enhanced_technologies.extend(["Service Discovery", "API Gateway"])
                    enhanced_quality_attributes["resilience"] = "Circuit breaker patterns"
            
            elif pattern.pattern_type.value == "event_driven":
                enhanced_responsibilities.append("Event publishing/subscription")
                enhanced_technologies.append("Message Broker")
                enhanced_quality_attributes["async_processing"] = "Event-driven communication"
        
        # Add architecture-specific enhancements
        if architecture.scalability_tier.value in ["large", "enterprise"]:
            enhanced_quality_attributes["scalability"] = "Horizontal scaling support"
            enhanced_technologies.append("Load Balancer")
        
        return Component(
            name=component.name,
            component_type=component.component_type,
            description=component.description,
            responsibilities=enhanced_responsibilities,
            interfaces=component.interfaces,
            dependencies=component.dependencies,
            technologies=enhanced_technologies,
            data_entities=component.data_entities,
            quality_attributes=enhanced_quality_attributes
        )
    
    def _fix_component_issues(self, 
                            component: Component,
                            architecture: ArchitectureDesign) -> Component:
        """
        Fix common component design issues
        """
        fixed_responsibilities = component.responsibilities.copy()
        fixed_interfaces = component.interfaces.copy()
        
        # Add default responsibilities if missing
        if not fixed_responsibilities:
            if component.component_type == ComponentType.BUSINESS_LOGIC:
                fixed_responsibilities = [f"Manage {component.name} business logic"]
            elif component.component_type == ComponentType.DATA_ACCESS:
                fixed_responsibilities = [f"Handle {component.name} data operations"]
        
        # Add default interfaces if missing for service components
        if not fixed_interfaces and component.component_type in [ComponentType.BUSINESS_LOGIC, ComponentType.DATA_ACCESS]:
            interface_name = f"I{component.name}"
            fixed_interfaces = [interface_name]
        
        return Component(
            name=component.name,
            component_type=component.component_type,
            description=component.description or f"Component for {component.name}",
            responsibilities=fixed_responsibilities,
            interfaces=fixed_interfaces,
            dependencies=component.dependencies,
            technologies=component.technologies,
            data_entities=component.data_entities,
            quality_attributes=component.quality_attributes
        )
    
    async def _fallback_component_modeling(self, 
                                         architecture: ArchitectureDesign,
                                         patterns: List[ArchitecturalPattern]) -> List[Component]:
        """
        Fallback rule-based component modeling
        """
        components = []
        
        # Standard web application components
        components.extend([
            Component(
                name="WebController",
                component_type=ComponentType.PRESENTATION,
                description="Handles HTTP requests and responses",
                responsibilities=["Request routing", "Input validation", "Response formatting"],
                interfaces=["IController", "IRequestHandler"],
                dependencies=["BusinessService"],
                technologies=["FastAPI", "Pydantic"],
                data_entities=[],
                quality_attributes={
                    "performance": "Sub-100ms response time",
                    "security": "Input sanitization",
                    "usability": "Clear error messages"
                }
            ),
            Component(
                name="BusinessService",
                component_type=ComponentType.BUSINESS_LOGIC,
                description="Core business logic implementation",
                responsibilities=["Business rule implementation", "Transaction coordination", "Data validation"],
                interfaces=["IBusinessService"],
                dependencies=["DataRepository"],
                technologies=["Python", "Business Logic Framework"],
                data_entities=["BusinessEntity"],
                quality_attributes={
                    "maintainability": "Clean code practices",
                    "testability": "Unit test coverage",
                    "reliability": "Error handling"
                }
            ),
            Component(
                name="DataRepository",
                component_type=ComponentType.DATA_ACCESS,
                description="Data persistence and retrieval",
                responsibilities=["Data CRUD operations", "Query optimization", "Data consistency"],
                interfaces=["IRepository"],
                dependencies=["Database"],
                technologies=["SQLAlchemy", "PostgreSQL"],
                data_entities=["DataModel"],
                quality_attributes={
                    "performance": "Optimized queries",
                    "consistency": "ACID compliance",
                    "scalability": "Connection pooling"
                }
            )
        ])
        
        return components
    
    def _generate_infrastructure_components(self, architecture: ArchitectureDesign) -> List[Component]:
        """
        Generate standard infrastructure components
        """
        infrastructure_components = [
            Component(
                name="AuthenticationService",
                component_type=ComponentType.SECURITY,
                description="User authentication and authorization",
                responsibilities=["User authentication", "Token management", "Access control"],
                interfaces=["IAuthService"],
                dependencies=["UserRepository"],
                technologies=["JWT", "OAuth2"],
                data_entities=["User", "Role"],
                quality_attributes={
                    "security": "Secure token handling",
                    "performance": "Fast authentication",
                    "compliance": "Security standards"
                }
            ),
            Component(
                name="LoggingService",
                component_type=ComponentType.MONITORING,
                description="System logging and monitoring",
                responsibilities=["Log collection", "Error tracking", "Performance monitoring"],
                interfaces=["ILogger"],
                dependencies=["LogStorage"],
                technologies=["Structured Logging", "Monitoring Tools"],
                data_entities=["LogEntry"],
                quality_attributes={
                    "observability": "Comprehensive logging",
                    "performance": "Minimal overhead",
                    "retention": "Log rotation policy"
                }
            )
        ]
        
        # Add caching component for medium+ scale systems
        if architecture.scalability_tier.value in ["medium", "large", "enterprise"]:
            cache_component = Component(
                name="CacheService",
                component_type=ComponentType.INFRASTRUCTURE,
                description="Data caching and performance optimization",
                responsibilities=["Cache management", "Cache invalidation", "Performance optimization"],
                interfaces=["ICacheService"],
                dependencies=["Redis"],
                technologies=["Redis", "Cache Strategies"],
                data_entities=["CacheEntry"],
                quality_attributes={
                    "performance": "Sub-millisecond access",
                    "scalability": "Distributed caching",
                    "reliability": "Cache consistency"
                }
            )
            infrastructure_components.append(cache_component)
        
        return infrastructure_components
    
    def _derive_service_name(self, use_case: str) -> str:
        """
        Derive service name from use case description
        """
        # Simple extraction - take first significant words
        words = use_case.strip().split()[:3]
        return ''.join(word.capitalize() for word in words if word.isalpha())
    
    def _derive_dependencies(self, use_case: str, entities: List[str]) -> List[str]:
        """
        Derive component dependencies from use case and entities
        """
        dependencies = []
        
        # Check which entities are mentioned in the use case
        use_case_lower = use_case.lower()
        for entity in entities:
            if entity.lower() in use_case_lower:
                repo_name = f"{entity.title().replace(' ', '')}Repository"
                dependencies.append(repo_name)
        
        return dependencies
    
    def _extract_related_entities(self, use_case: str, entities: List[str]) -> List[str]:
        """
        Extract entities related to a specific use case
        """
        related_entities = []
        use_case_lower = use_case.lower()
        
        for entity in entities:
            if entity.lower() in use_case_lower:
                related_entities.append(entity)
        
        return related_entities
    
    def _group_related_components(self, components: List[Component]) -> List[List[Component]]:
        """
        Group components by their relationships and dependencies
        """
        groups = []
        processed = set()
        
        for component in components:
            if component.name in processed:
                continue
            
            group = [component]
            processed.add(component.name)
            
            # Find related components
            for other_component in components:
                if (other_component.name not in processed and 
                    self._are_components_related(component, other_component)):
                    group.append(other_component)
                    processed.add(other_component.name)
            
            groups.append(group)
        
        return groups
    
    def _are_components_related(self, comp1: Component, comp2: Component) -> bool:
        """
        Check if two components are closely related
        """
        # Check dependencies
        if comp1.name in comp2.dependencies or comp2.name in comp1.dependencies:
            return True
        
        # Check shared data entities
        shared_entities = set(comp1.data_entities) & set(comp2.data_entities)
        if shared_entities:
            return True
        
        # Check component types - group similar types
        related_types = [
            {ComponentType.PRESENTATION, ComponentType.BUSINESS_LOGIC},
            {ComponentType.BUSINESS_LOGIC, ComponentType.DATA_ACCESS},
            {ComponentType.SECURITY, ComponentType.INFRASTRUCTURE}
        ]
        
        for type_group in related_types:
            if comp1.component_type in type_group and comp2.component_type in type_group:
                return True
        
        return False
    
    def _consider_component_merge(self, 
                                components: List[Component], 
                                architecture: ArchitectureDesign) -> Optional[Component]:
        """
        Consider merging highly related components if beneficial
        """
        if len(components) != 2:  # Only consider merging pairs for simplicity
            return None
        
        comp1, comp2 = components[0], components[1]
        
        # Only merge if they're of compatible types and have high coupling
        compatible_merges = [
            {ComponentType.PRESENTATION, ComponentType.BUSINESS_LOGIC},
            {ComponentType.BUSINESS_LOGIC, ComponentType.DATA_ACCESS}
        ]
        
        comp_types = {comp1.component_type, comp2.component_type}
        
        for compatible_set in compatible_merges:
            if comp_types == compatible_set:
                # Merge components
                return self._merge_components(comp1, comp2)
        
        return None
    
    def _merge_components(self, comp1: Component, comp2: Component) -> Component:
        """
        Merge two compatible components
        """
        merged_name = f"{comp1.name}And{comp2.name}"
        merged_responsibilities = comp1.responsibilities + comp2.responsibilities
        merged_interfaces = list(set(comp1.interfaces + comp2.interfaces))
        merged_dependencies = list(set(comp1.dependencies + comp2.dependencies))
        merged_technologies = list(set(comp1.technologies + comp2.technologies))
        merged_entities = list(set(comp1.data_entities + comp2.data_entities))
        
        # Merge quality attributes
        merged_quality = {}
        merged_quality.update(comp1.quality_attributes)
        merged_quality.update(comp2.quality_attributes)
        
        return Component(
            name=merged_name,
            component_type=comp1.component_type,  # Use first component's type
            description=f"Merged component: {comp1.description} and {comp2.description}",
            responsibilities=merged_responsibilities,
            interfaces=merged_interfaces,
            dependencies=merged_dependencies,
            technologies=merged_technologies,
            data_entities=merged_entities,
            quality_attributes=merged_quality
        )
    
    def _validate_component_structure(self, 
                                    components: List[Component],
                                    architecture: ArchitectureDesign) -> List[Component]:
        """
        Final validation of component structure
        """
        validated = []
        
        for component in components:
            # Ensure component has reasonable complexity
            if len(component.responsibilities) <= 7:  # Follow 7±2 rule
                validated.append(component)
            else:
                # Split complex components
                split_components = self._split_complex_component(component)
                validated.extend(split_components)
        
        return validated
    
    def _split_complex_component(self, component: Component) -> List[Component]:
        """
        Split overly complex component into smaller ones
        """
        # Simple split strategy - divide responsibilities
        mid_point = len(component.responsibilities) // 2
        
        comp1_responsibilities = component.responsibilities[:mid_point]
        comp2_responsibilities = component.responsibilities[mid_point:]
        
        comp1 = Component(
            name=f"{component.name}Core",
            component_type=component.component_type,
            description=f"Core part of {component.name}",
            responsibilities=comp1_responsibilities,
            interfaces=component.interfaces[:len(component.interfaces)//2] if component.interfaces else [],
            dependencies=component.dependencies,
            technologies=component.technologies,
            data_entities=component.data_entities,
            quality_attributes=component.quality_attributes
        )
        
        comp2 = Component(
            name=f"{component.name}Extended",
            component_type=component.component_type,
            description=f"Extended functionality of {component.name}",
            responsibilities=comp2_responsibilities,
            interfaces=component.interfaces[len(component.interfaces)//2:] if component.interfaces else [],
            dependencies=component.dependencies + [comp1.name],
            technologies=component.technologies,
            data_entities=component.data_entities,
            quality_attributes=component.quality_attributes
        )
        
        return [comp1, comp2]
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration parameters
        """
        # 1. API Key Existence Check (Unified + Legacy)
        api_key = config.get("llm_api_key") or config.get("openai_api_key")
        
        if not api_key:
            # 기존 코드 호환성을 위해 openai_api_key가 없다고 에러 메시지 출력
            raise ValidationException(
                message="Missing required configuration parameters",
                details={"missing_keys": ["openai_api_key"]},
                field="api_key",
                value="None"
            )
        
        # 2. Validate API key format (Expanded for Perplexity support)
        valid_prefixes = ("sk-", "sk-proj-", "pplx-", "sk-ant-", "AIza")
        
        if not api_key.startswith(valid_prefixes):
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
            raise ValidationException(
                message="Invalid API key format",
                details={"expected_format": "sk-*, sk-proj-*, pplx-*, sk-ant-*, or AIza*"},
                field="api_key",
                value=masked_key
            )

    
    async def _fallback_component_generation(self, 
                                           architecture: ArchitectureDesign,
                                           patterns: List[ArchitecturalPattern]) -> Dict[str, Any]:
        """
        Rule-based fallback component generation
        """
        return {
            "components": [
                {
                    "name": "ApplicationController",
                    "component_type": "presentation",
                    "description": "Main application controller",
                    "responsibilities": ["Handle requests", "Route to services"],
                    "interfaces": ["IController"],
                    "dependencies": ["ApplicationService"],
                    "technologies": ["FastAPI"],
                    "data_entities": [],
                    "quality_attributes": {"performance": "Fast response"}
                },
                {
                    "name": "ApplicationService",
                    "component_type": "business_logic", 
                    "description": "Core business logic service",
                    "responsibilities": ["Business logic", "Validation"],
                    "interfaces": ["IApplicationService"],
                    "dependencies": ["Repository"],
                    "technologies": ["Python"],
                    "data_entities": ["BusinessEntity"],
                    "quality_attributes": {"maintainability": "Clean code"}
                }
            ],
            "component_relationships": [],
            "deployment_considerations": {
                "deployment_units": ["web-tier", "business-tier", "data-tier"],
                "scaling_strategy": "horizontal",
                "monitoring_points": ["response-time", "error-rate"]
            }
        }