"""
Template matching utility for stack recommendations.
Provides predefined stack templates for common use cases.
"""

from typing import List, Dict, Any, Optional, Set
import logging
from ..models.stack_models import (
    StackTemplate, StackRecommendation, TechnologyChoice, StackCategory
)
from ..config.settings import settings, template_config

logger = logging.getLogger(__name__)


class TemplateMatcher:
    """Matches requirements to predefined stack templates"""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    async def find_matching_templates(
        self,
        domain: str,
        scale: str,
        components: List[str],
        patterns: Optional[List[str]] = None
    ) -> List[StackTemplate]:
        """Find templates matching the given requirements"""
        
        logger.info(f"Finding templates for domain: {domain}, scale: {scale}")
        
        scored_templates = []
        
        for template in self.templates:
            score = self._calculate_template_score(
                template, domain, scale, components, patterns or []
            )
            
            if score > 0.3:  # Minimum relevance threshold
                scored_templates.append((template, score))
        
        # Sort by score descending
        scored_templates.sort(key=lambda x: x[1], reverse=True)
        
        # Return top templates
        return [template for template, _ in scored_templates[:5]]
    
    def _calculate_template_score(
        self,
        template: StackTemplate,
        domain: str,
        scale: str,
        components: List[str],
        patterns: List[str]
    ) -> float:
        """Calculate how well a template matches the requirements"""
        
        score = 0.0
        
        # Domain matching (40% weight)
        domain_score = self._calculate_domain_match(template.domain, domain)
        score += domain_score * 0.4
        
        # Scale appropriateness (20% weight)
        scale_score = self._calculate_scale_appropriateness(template, scale)
        score += scale_score * 0.2
        
        # Component coverage (25% weight)
        component_score = self._calculate_component_coverage(template, components)
        score += component_score * 0.25
        
        # Pattern support (15% weight)
        pattern_score = self._calculate_pattern_support(template, patterns)
        score += pattern_score * 0.15
        
        return min(score, 1.0)
    
    def _calculate_domain_match(self, template_domain: str, target_domain: str) -> float:
        """Calculate domain matching score"""
        
        template_domain_lower = template_domain.lower()
        target_domain_lower = target_domain.lower()
        
        # Exact match
        if template_domain_lower == target_domain_lower:
            return 1.0
        
        # Partial matches
        domain_keywords = {
            "web": ["web", "frontend", "ui", "interface"],
            "api": ["api", "service", "backend", "server"],
            "data": ["data", "analytics", "pipeline", "etl"],
            "mobile": ["mobile", "app", "ios", "android"],
            "enterprise": ["enterprise", "business", "corporate"]
        }
        
        template_keywords = set()
        target_keywords = set()
        
        for category, keywords in domain_keywords.items():
            if any(keyword in template_domain_lower for keyword in keywords):
                template_keywords.add(category)
            if any(keyword in target_domain_lower for keyword in keywords):
                target_keywords.add(category)
        
        if template_keywords and target_keywords:
            overlap = len(template_keywords.intersection(target_keywords))
            union = len(template_keywords.union(target_keywords))
            return overlap / union if union > 0 else 0.0
        
        return 0.3  # Default similarity for unknown domains
    
    def _calculate_scale_appropriateness(self, template: StackTemplate, scale: str) -> float:
        """Calculate how appropriate the template is for the given scale"""
        
        # Extract scale indicators from template technologies
        template_scale_score = 0.0
        tech_count = 0
        
        scale_scores = {
            "small": {"sqlite": 1.0, "flask": 0.9, "single_server": 1.0},
            "medium": {"postgresql": 1.0, "fastapi": 0.9, "redis": 0.8},
            "large": {"postgresql": 1.0, "microservices": 0.9, "kubernetes": 0.8},
            "enterprise": {"kubernetes": 1.0, "microservices": 1.0, "monitoring": 1.0}
        }
        
        target_preferences = scale_scores.get(scale, {})
        
        for category_techs in [
            template.technologies.backend,
            template.technologies.database,
            template.technologies.infrastructure
        ]:
            for tech in category_techs:
                tech_count += 1
                tech_name = tech.name.lower()
                template_scale_score += target_preferences.get(tech_name, 0.5)
        
        return template_scale_score / tech_count if tech_count > 0 else 0.5
    
    def _calculate_component_coverage(
        self, 
        template: StackTemplate, 
        components: List[str]
    ) -> float:
        """Calculate how well template covers required components"""
        
        if not components:
            return 0.8  # Default if no components specified
        
        component_tech_mapping = {
            "user_interface": ["react", "vue", "angular", "frontend"],
            "api": ["fastapi", "express", "django", "api"],
            "database": ["postgresql", "mongodb", "mysql", "database"],
            "authentication": ["oauth", "auth", "jwt", "security"],
            "search": ["elasticsearch", "solr", "search"],
            "cache": ["redis", "memcached", "cache"],
            "messaging": ["kafka", "rabbitmq", "redis", "messaging"],
            "file_storage": ["s3", "minio", "storage"],
            "monitoring": ["prometheus", "grafana", "monitoring"]
        }
        
        covered_components = 0
        
        for component in components:
            component_lower = component.lower().replace(" ", "_")
            required_techs = component_tech_mapping.get(component_lower, [])
            
            if self._template_has_technologies(template, required_techs):
                covered_components += 1
            elif self._component_name_in_template(template, component):
                covered_components += 0.5  # Partial credit for name match
        
        return covered_components / len(components) if components else 0.8
    
    def _calculate_pattern_support(
        self,
        template: StackTemplate,
        patterns: List[str]
    ) -> float:
        """Calculate pattern support score"""
        
        if not patterns:
            return 0.8  # Default if no patterns specified
        
        pattern_tech_requirements = {
            "microservices": ["kubernetes", "docker", "api_gateway"],
            "event_driven": ["kafka", "rabbitmq", "event", "messaging"],
            "cqrs": ["event_store", "read_model", "command"],
            "restful": ["api", "rest", "http"],
            "mvc": ["framework", "model", "view", "controller"],
            "layered": ["service", "repository", "controller"]
        }
        
        supported_patterns = 0
        
        for pattern in patterns:
            pattern_lower = pattern.lower().replace("-", "_").replace(" ", "_")
            required_techs = pattern_tech_requirements.get(pattern_lower, [])
            
            if required_techs and self._template_has_technologies(template, required_techs):
                supported_patterns += 1
            elif pattern_lower in template.name.lower() or pattern_lower in template.description.lower():
                supported_patterns += 0.7  # Partial credit for mention
        
        return supported_patterns / len(patterns) if patterns else 0.8
    
    def _template_has_technologies(self, template: StackTemplate, tech_names: List[str]) -> bool:
        """Check if template includes any of the specified technologies"""
        
        template_tech_names = set()
        
        for category_techs in [
            template.technologies.backend,
            template.technologies.frontend,
            template.technologies.database,
            template.technologies.infrastructure,
            template.technologies.devops,
            template.technologies.monitoring
        ]:
            for tech in category_techs:
                template_tech_names.add(tech.name.lower())
        
        return any(
            tech_name.lower() in template_tech_names or
            any(tech_name.lower() in template_tech for template_tech in template_tech_names)
            for tech_name in tech_names
        )
    
    def _component_name_in_template(self, template: StackTemplate, component: str) -> bool:
        """Check if component name appears in template description or use cases"""
        
        component_lower = component.lower()
        
        if component_lower in template.description.lower():
            return True
        
        for use_case in template.use_cases:
            if component_lower in use_case.lower():
                return True
        
        return False
    
    def _load_templates(self) -> List[StackTemplate]:
        """Load predefined stack templates"""
        
        templates = []
        
        # Web Application Templates
        templates.extend(self._create_web_templates())
        
        # API Service Templates
        templates.extend(self._create_api_templates())
        
        # Microservices Templates
        templates.extend(self._create_microservices_templates())
        
        # Data Pipeline Templates
        templates.extend(self._create_data_templates())
        
        # Mobile Backend Templates
        templates.extend(self._create_mobile_templates())
        
        logger.info(f"Loaded {len(templates)} stack templates")
        
        return templates
    
    def _create_web_templates(self) -> List[StackTemplate]:
        """Create web application templates"""
        
        return [
            StackTemplate(
                name="react_fastapi_postgres",
                domain="web_application",
                description="Modern web application with React frontend and FastAPI backend",
                technologies=StackRecommendation(
                    frontend=[
                        TechnologyChoice(
                            name="React", version="18.0", category=StackCategory.FRONTEND,
                            reason="Modern, component-based UI framework", alternatives=["Vue", "Angular"],
                            confidence=0.9
                        )
                    ],
                    backend=[
                        TechnologyChoice(
                            name="FastAPI", version="0.109.0", category=StackCategory.BACKEND,
                            reason="High-performance Python web framework", alternatives=["Django", "Flask"],
                            confidence=0.9
                        )
                    ],
                    database=[
                        TechnologyChoice(
                            name="PostgreSQL", version="15.0", category=StackCategory.DATABASE,
                            reason="Robust relational database", alternatives=["MySQL", "MongoDB"],
                            confidence=0.9
                        )
                    ],
                    infrastructure=[
                        TechnologyChoice(
                            name="Docker", version="latest", category=StackCategory.INFRASTRUCTURE,
                            reason="Containerization for consistent deployment", alternatives=["Podman"],
                            confidence=0.8
                        )
                    ]
                ),
                min_quality_score=0.8,
                use_cases=["SPA", "web dashboard", "CRUD application"]
            ),
            StackTemplate(
                name="vue_django_mysql",
                domain="web_application", 
                description="Traditional web application with Vue.js and Django",
                technologies=StackRecommendation(
                    frontend=[
                        TechnologyChoice(
                            name="Vue", version="3.0", category=StackCategory.FRONTEND,
                            reason="Progressive web framework", alternatives=["React", "Angular"],
                            confidence=0.8
                        )
                    ],
                    backend=[
                        TechnologyChoice(
                            name="Django", version="4.2", category=StackCategory.BACKEND,
                            reason="Full-featured Python web framework", alternatives=["FastAPI", "Flask"],
                            confidence=0.9
                        )
                    ],
                    database=[
                        TechnologyChoice(
                            name="MySQL", version="8.0", category=StackCategory.DATABASE,
                            reason="Widely-used relational database", alternatives=["PostgreSQL"],
                            confidence=0.8
                        )
                    ]
                ),
                min_quality_score=0.7,
                use_cases=["content management", "e-commerce", "traditional web app"]
            )
        ]
    
    def _create_api_templates(self) -> List[StackTemplate]:
        """Create API service templates"""
        
        return [
            StackTemplate(
                name="fastapi_postgres_redis",
                domain="api_service",
                description="High-performance API service with caching",
                technologies=StackRecommendation(
                    backend=[
                        TechnologyChoice(
                            name="FastAPI", version="0.109.0", category=StackCategory.BACKEND,
                            reason="Async-first API framework", alternatives=["Django REST", "Flask"],
                            confidence=0.95
                        )
                    ],
                    database=[
                        TechnologyChoice(
                            name="PostgreSQL", version="15.0", category=StackCategory.DATABASE,
                            reason="ACID-compliant database", alternatives=["MySQL"],
                            confidence=0.9
                        ),
                        TechnologyChoice(
                            name="Redis", version="7.0", category=StackCategory.DATABASE,
                            reason="High-performance caching", alternatives=["Memcached"],
                            confidence=0.9
                        )
                    ],
                    infrastructure=[
                        TechnologyChoice(
                            name="Docker", version="latest", category=StackCategory.INFRASTRUCTURE,
                            reason="Container deployment", alternatives=["Kubernetes"],
                            confidence=0.8
                        )
                    ]
                ),
                min_quality_score=0.8,
                use_cases=["REST API", "microservice", "backend service"]
            ),
            StackTemplate(
                name="express_postgres_redis",
                domain="api_service",
                description="Node.js API service with PostgreSQL and Redis",
                technologies=StackRecommendation(
                    backend=[
                        TechnologyChoice(
                            name="Express", version="4.18", category=StackCategory.BACKEND,
                            reason="Minimal web framework for Node.js", alternatives=["Koa", "Fastify"],
                            confidence=0.85
                        )
                    ],
                    database=[
                        TechnologyChoice(
                            name="PostgreSQL", version="15.0", category=StackCategory.DATABASE,
                            reason="Reliable relational database", alternatives=["MongoDB"],
                            confidence=0.9
                        ),
                        TechnologyChoice(
                            name="Redis", version="7.0", category=StackCategory.DATABASE,
                            reason="Session and cache storage", alternatives=["Memcached"],
                            confidence=0.8
                        )
                    ]
                ),
                min_quality_score=0.75,
                use_cases=["API gateway", "backend for frontend", "real-time service"]
            )
        ]
    
    def _create_microservices_templates(self) -> List[StackTemplate]:
        """Create microservices templates"""
        
        return [
            StackTemplate(
                name="kubernetes_microservices",
                domain="microservices",
                description="Container-orchestrated microservices architecture",
                technologies=StackRecommendation(
                    backend=[
                        TechnologyChoice(
                            name="FastAPI", version="0.109.0", category=StackCategory.BACKEND,
                            reason="Lightweight services", alternatives=["Express", "Spring Boot"],
                            confidence=0.8
                        )
                    ],
                    database=[
                        TechnologyChoice(
                            name="PostgreSQL", version="15.0", category=StackCategory.DATABASE,
                            reason="Per-service databases", alternatives=["MongoDB"],
                            confidence=0.8
                        )
                    ],
                    infrastructure=[
                        TechnologyChoice(
                            name="Kubernetes", version="1.28", category=StackCategory.INFRASTRUCTURE,
                            reason="Container orchestration", alternatives=["Docker Swarm"],
                            confidence=0.9
                        ),
                        TechnologyChoice(
                            name="Istio", version="1.19", category=StackCategory.INFRASTRUCTURE,
                            reason="Service mesh", alternatives=["Linkerd"],
                            confidence=0.7
                        )
                    ],
                    monitoring=[
                        TechnologyChoice(
                            name="Prometheus", version="2.45", category=StackCategory.MONITORING,
                            reason="Metrics collection", alternatives=["DataDog"],
                            confidence=0.9
                        )
                    ]
                ),
                min_quality_score=0.7,
                use_cases=["enterprise application", "scalable system", "distributed architecture"]
            )
        ]
    
    def _create_data_templates(self) -> List[StackTemplate]:
        """Create data pipeline templates"""
        
        return [
            StackTemplate(
                name="python_data_pipeline",
                domain="data_pipeline",
                description="Python-based data processing pipeline",
                technologies=StackRecommendation(
                    backend=[
                        TechnologyChoice(
                            name="Apache Airflow", version="2.7", category=StackCategory.BACKEND,
                            reason="Workflow orchestration", alternatives=["Prefect", "Dagster"],
                            confidence=0.85
                        )
                    ],
                    database=[
                        TechnologyChoice(
                            name="PostgreSQL", version="15.0", category=StackCategory.DATABASE,
                            reason="Metadata storage", alternatives=["MySQL"],
                            confidence=0.8
                        ),
                        TechnologyChoice(
                            name="Apache Spark", version="3.5", category=StackCategory.DATABASE,
                            reason="Big data processing", alternatives=["Dask"],
                            confidence=0.8
                        )
                    ]
                ),
                min_quality_score=0.7,
                use_cases=["ETL pipeline", "data analytics", "batch processing"]
            )
        ]
    
    def _create_mobile_templates(self) -> List[StackTemplate]:
        """Create mobile backend templates"""
        
        return [
            StackTemplate(
                name="mobile_backend_api",
                domain="mobile_backend",
                description="API backend optimized for mobile applications",
                technologies=StackRecommendation(
                    backend=[
                        TechnologyChoice(
                            name="FastAPI", version="0.109.0", category=StackCategory.BACKEND,
                            reason="Fast API responses", alternatives=["Express"],
                            confidence=0.9
                        )
                    ],
                    database=[
                        TechnologyChoice(
                            name="PostgreSQL", version="15.0", category=StackCategory.DATABASE,
                            reason="Structured data storage", alternatives=["MongoDB"],
                            confidence=0.8
                        ),
                        TechnologyChoice(
                            name="Redis", version="7.0", category=StackCategory.DATABASE,
                            reason="Session management", alternatives=["Memcached"],
                            confidence=0.9
                        )
                    ],
                    infrastructure=[
                        TechnologyChoice(
                            name="CDN", version="latest", category=StackCategory.INFRASTRUCTURE,
                            reason="Content delivery", alternatives=["CloudFlare"],
                            confidence=0.8
                        )
                    ]
                ),
                min_quality_score=0.75,
                use_cases=["mobile API", "user authentication", "push notifications"]
            )
        ]