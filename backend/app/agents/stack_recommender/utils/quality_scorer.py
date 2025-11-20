"""
Quality scoring system for stack recommendations.
Evaluates recommendations across multiple quality dimensions.
"""

from typing import Dict, Any, List, Tuple
import asyncio
import logging
from ..models.stack_models import (
    QualityScore, StackRecommendation, ArchitectureContext,
    TechnologyChoice, QualityAttribute
)
from ..config.settings import settings

logger = logging.getLogger(__name__)


class QualityScorer:
    """Evaluates quality of stack recommendations across multiple dimensions"""
    
    def __init__(self):
        self.weights = {
            QualityAttribute.SUITABILITY: 0.3,
            QualityAttribute.COMPLETENESS: 0.25,
            QualityAttribute.FEASIBILITY: 0.2,
            QualityAttribute.SCALABILITY: 0.15,
            QualityAttribute.MAINTAINABILITY: 0.1
        }
        
        # Technology maturity and reliability scores
        self.tech_reliability = self._load_tech_reliability_data()
        
        # Compatibility matrix
        self.compatibility_matrix = self._load_compatibility_matrix()
    
    async def evaluate_recommendation(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> QualityScore:
        """Evaluate overall quality of stack recommendation"""
        
        logger.info("Evaluating recommendation quality")
        
        # Calculate individual quality scores
        suitability = await self._evaluate_suitability(recommendation, architecture)
        completeness = await self._evaluate_completeness(recommendation, architecture)
        feasibility = await self._evaluate_feasibility(recommendation, architecture)
        scalability = await self._evaluate_scalability(recommendation, architecture)
        maintainability = await self._evaluate_maintainability(recommendation, architecture)
        
        quality_score = QualityScore(
            suitability=suitability,
            completeness=completeness,
            feasibility=feasibility,
            scalability=scalability,
            maintainability=maintainability
        )
        
        logger.info(f"Quality evaluation complete: overall score {quality_score.overall_score}")
        
        return quality_score
    
    async def _evaluate_suitability(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> float:
        """Evaluate how well the stack suits the architecture requirements"""
        
        score = 0.0
        total_weight = 0.0
        
        # Domain alignment score (40%)
        domain_score = self._calculate_domain_alignment(recommendation, architecture.domain)
        score += domain_score * 0.4
        total_weight += 0.4
        
        # Pattern support score (30%)
        pattern_score = self._calculate_pattern_support(recommendation, architecture.patterns)
        score += pattern_score * 0.3
        total_weight += 0.3
        
        # Quality attributes score (30%)
        qa_score = self._calculate_quality_attributes_support(
            recommendation, architecture.quality_attributes
        )
        score += qa_score * 0.3
        total_weight += 0.3
        
        return min(score / total_weight, 1.0) if total_weight > 0 else 0.5
    
    async def _evaluate_completeness(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> float:
        """Evaluate completeness of the technology stack"""
        
        required_categories = self._determine_required_categories(architecture)
        covered_categories = self._get_covered_categories(recommendation)
        
        # Basic coverage score
        coverage_ratio = len(covered_categories.intersection(required_categories)) / len(required_categories)
        
        # Penalize missing critical categories
        critical_missing = required_categories - covered_categories
        critical_penalty = len(critical_missing) * 0.2
        
        # Bonus for comprehensive coverage
        extra_categories = covered_categories - required_categories
        extra_bonus = min(len(extra_categories) * 0.1, 0.2)
        
        return max(0.0, min(1.0, coverage_ratio - critical_penalty + extra_bonus))
    
    async def _evaluate_feasibility(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> float:
        """Evaluate implementation feasibility"""
        
        scores = []
        
        # Technology maturity (40%)
        maturity_score = self._calculate_technology_maturity(recommendation)
        scores.append((maturity_score, 0.4))
        
        # Learning curve (30%)
        learning_score = self._calculate_learning_curve(recommendation)
        scores.append((learning_score, 0.3))
        
        # Resource requirements (20%)
        resource_score = self._calculate_resource_requirements(recommendation, architecture)
        scores.append((resource_score, 0.2))
        
        # Constraint compliance (10%)
        constraint_score = self._calculate_constraint_compliance(recommendation, architecture)
        scores.append((constraint_score, 0.1))
        
        return sum(score * weight for score, weight in scores)
    
    async def _evaluate_scalability(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> float:
        """Evaluate scalability potential"""
        
        scale_requirements = {
            "small": 0.5,
            "medium": 0.7,
            "large": 0.8,
            "enterprise": 0.9
        }
        
        required_scalability = scale_requirements.get(architecture.scale, 0.7)
        
        # Technology scalability scores
        tech_scores = []
        
        for category_techs in [
            recommendation.backend, recommendation.database, 
            recommendation.infrastructure
        ]:
            for tech in category_techs:
                tech_scalability = self._get_technology_scalability(tech.name)
                tech_scores.append(tech_scalability)
        
        if not tech_scores:
            return 0.5
        
        average_scalability = sum(tech_scores) / len(tech_scores)
        
        # Compare with requirements
        if average_scalability >= required_scalability:
            return min(1.0, average_scalability * 1.1)  # Bonus for exceeding requirements
        else:
            penalty = (required_scalability - average_scalability) * 0.5
            return max(0.0, average_scalability - penalty)
    
    async def _evaluate_maintainability(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> float:
        """Evaluate long-term maintainability"""
        
        scores = []
        
        # Technology ecosystem (35%)
        ecosystem_score = self._calculate_ecosystem_strength(recommendation)
        scores.append((ecosystem_score, 0.35))
        
        # Documentation quality (25%)
        doc_score = self._calculate_documentation_quality(recommendation)
        scores.append((doc_score, 0.25))
        
        # Community support (20%)
        community_score = self._calculate_community_support(recommendation)
        scores.append((community_score, 0.2))
        
        # Technology compatibility (20%)
        compatibility_score = self._calculate_technology_compatibility(recommendation)
        scores.append((compatibility_score, 0.2))
        
        return sum(score * weight for score, weight in scores)
    
    def _calculate_domain_alignment(self, recommendation: StackRecommendation, domain: str) -> float:
        """Calculate how well technologies align with domain"""
        
        domain_preferences = {
            "web_application": {
                "react": 0.9, "vue": 0.8, "angular": 0.8,
                "fastapi": 0.9, "django": 0.8, "express": 0.7,
                "postgresql": 0.9, "mysql": 0.8
            },
            "api_service": {
                "fastapi": 1.0, "express": 0.9, "gin": 0.8,
                "postgresql": 0.9, "redis": 0.9, "mongodb": 0.7
            },
            "data_pipeline": {
                "python": 1.0, "apache_spark": 0.9, "airflow": 0.9,
                "postgresql": 0.8, "clickhouse": 0.9, "kafka": 0.9
            }
        }
        
        preferences = domain_preferences.get(domain.lower().replace(" ", "_"), {})
        
        if not preferences:
            return 0.7  # Default score for unknown domains
        
        scores = []
        
        for category_techs in [
            recommendation.backend, recommendation.frontend, recommendation.database
        ]:
            for tech in category_techs:
                tech_key = tech.name.lower().replace("-", "_").replace(" ", "_")
                tech_score = preferences.get(tech_key, 0.5)
                scores.append(tech_score)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _calculate_pattern_support(self, recommendation: StackRecommendation, patterns: List[str]) -> float:
        """Calculate how well technologies support architectural patterns"""
        
        pattern_tech_support = {
            "microservices": {
                "fastapi": 0.9, "express": 0.8, "spring_boot": 0.9,
                "docker": 1.0, "kubernetes": 1.0, "istio": 1.0
            },
            "event_driven": {
                "kafka": 1.0, "rabbitmq": 0.9, "redis": 0.7,
                "nodejs": 0.8, "python": 0.7
            },
            "cqrs": {
                "postgresql": 0.8, "mongodb": 0.9, "elasticsearch": 1.0,
                "redis": 0.9
            }
        }
        
        if not patterns:
            return 0.8  # Default if no patterns specified
        
        pattern_scores = []
        
        for pattern in patterns:
            pattern_key = pattern.lower().replace("-", "_").replace(" ", "_")
            tech_support = pattern_tech_support.get(pattern_key, {})
            
            if tech_support:
                tech_scores = []
                for category_techs in [
                    recommendation.backend, recommendation.frontend, 
                    recommendation.database, recommendation.infrastructure
                ]:
                    for tech in category_techs:
                        tech_key = tech.name.lower().replace("-", "_")
                        support_score = tech_support.get(tech_key, 0.5)
                        tech_scores.append(support_score)
                
                pattern_score = sum(tech_scores) / len(tech_scores) if tech_scores else 0.5
                pattern_scores.append(pattern_score)
        
        return sum(pattern_scores) / len(pattern_scores) if pattern_scores else 0.7
    
    def _calculate_quality_attributes_support(
        self, 
        recommendation: StackRecommendation, 
        quality_attributes: List[str]
    ) -> float:
        """Calculate support for quality attributes"""
        
        qa_tech_scores = {
            "performance": {
                "fastapi": 0.9, "gin": 0.9, "nginx": 1.0,
                "redis": 1.0, "postgresql": 0.8
            },
            "security": {
                "fastapi": 0.8, "django": 0.9, "spring_security": 1.0,
                "postgresql": 0.9, "oauth2": 1.0
            },
            "scalability": {
                "kubernetes": 1.0, "docker": 0.9, "microservices": 1.0,
                "postgresql": 0.8, "mongodb": 0.9
            }
        }
        
        if not quality_attributes:
            return 0.8
        
        qa_scores = []
        
        for qa in quality_attributes:
            qa_key = qa.lower().replace("-", "_").replace(" ", "_")
            tech_scores_for_qa = qa_tech_scores.get(qa_key, {})
            
            if tech_scores_for_qa:
                tech_scores = []
                for category_techs in [
                    recommendation.backend, recommendation.frontend,
                    recommendation.database, recommendation.infrastructure
                ]:
                    for tech in category_techs:
                        tech_key = tech.name.lower().replace("-", "_")
                        score = tech_scores_for_qa.get(tech_key, 0.5)
                        tech_scores.append(score)
                
                qa_score = sum(tech_scores) / len(tech_scores) if tech_scores else 0.5
                qa_scores.append(qa_score)
        
        return sum(qa_scores) / len(qa_scores) if qa_scores else 0.7
    
    def _determine_required_categories(self, architecture: ArchitectureContext) -> set:
        """Determine required technology categories based on architecture"""
        
        required = {"backend"}  # Backend almost always required
        
        if "web" in architecture.domain.lower() or "frontend" in architecture.components:
            required.add("frontend")
        
        if any("data" in comp.lower() for comp in architecture.components):
            required.add("database")
        
        if architecture.scale in ["large", "enterprise"]:
            required.update({"infrastructure", "monitoring"})
        
        if "deployment" in architecture.quality_attributes:
            required.add("devops")
        
        return required
    
    def _get_covered_categories(self, recommendation: StackRecommendation) -> set:
        """Get categories covered by recommendation"""
        
        covered = set()
        
        if recommendation.backend:
            covered.add("backend")
        if recommendation.frontend:
            covered.add("frontend")
        if recommendation.database:
            covered.add("database")
        if recommendation.infrastructure:
            covered.add("infrastructure")
        if recommendation.devops:
            covered.add("devops")
        if recommendation.monitoring:
            covered.add("monitoring")
        
        return covered
    
    def _calculate_technology_maturity(self, recommendation: StackRecommendation) -> float:
        """Calculate average technology maturity score"""
        
        scores = []
        
        for category_techs in [
            recommendation.backend, recommendation.frontend, recommendation.database,
            recommendation.infrastructure, recommendation.devops, recommendation.monitoring
        ]:
            for tech in category_techs:
                maturity = self.tech_reliability.get(tech.name.lower(), 0.7)
                scores.append(maturity)
        
        return sum(scores) / len(scores) if scores else 0.7
    
    def _calculate_learning_curve(self, recommendation: StackRecommendation) -> float:
        """Estimate learning curve difficulty (higher is easier)"""
        
        learning_scores = {
            "react": 0.7, "vue": 0.8, "angular": 0.6,
            "fastapi": 0.9, "django": 0.7, "express": 0.8,
            "postgresql": 0.8, "mongodb": 0.9, "mysql": 0.8,
            "docker": 0.7, "kubernetes": 0.4
        }
        
        scores = []
        
        for category_techs in [
            recommendation.backend, recommendation.frontend, recommendation.database
        ]:
            for tech in category_techs:
                score = learning_scores.get(tech.name.lower(), 0.6)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.6
    
    def _calculate_resource_requirements(
        self, 
        recommendation: StackRecommendation, 
        architecture: ArchitectureContext
    ) -> float:
        """Calculate resource requirement appropriateness"""
        
        # Simple heuristic based on scale
        scale_multiplier = {
            "small": 1.0,
            "medium": 0.8,
            "large": 0.6,
            "enterprise": 0.4
        }
        
        multiplier = scale_multiplier.get(architecture.scale, 0.7)
        
        # Heavy technologies get penalized for smaller scales
        heavy_techs = {"kubernetes", "microservices", "elasticsearch"}
        
        tech_count = 0
        heavy_count = 0
        
        for category_techs in [
            recommendation.backend, recommendation.frontend, recommendation.database,
            recommendation.infrastructure
        ]:
            for tech in category_techs:
                tech_count += 1
                if tech.name.lower() in heavy_techs:
                    heavy_count += 1
        
        if tech_count == 0:
            return 0.5
        
        heavy_ratio = heavy_count / tech_count
        resource_score = 1.0 - (heavy_ratio * (1.0 - multiplier))
        
        return max(0.2, resource_score)
    
    def _calculate_constraint_compliance(
        self,
        recommendation: StackRecommendation,
        architecture: ArchitectureContext
    ) -> float:
        """Check compliance with constraints"""
        
        constraints = architecture.constraints
        
        if not constraints:
            return 1.0
        
        violations = 0
        total_constraints = 0
        
        # Check budget constraints
        if "budget" in constraints:
            total_constraints += 1
            # Simple cost estimation
            tech_costs = self._estimate_tech_costs(recommendation)
            budget = constraints["budget"]
            if isinstance(budget, (int, float)) and tech_costs > budget:
                violations += 1
        
        # Check technology preferences
        if "preferred_languages" in constraints:
            total_constraints += 1
            preferred = constraints["preferred_languages"]
            if isinstance(preferred, list):
                backend_langs = self._get_languages_from_recommendation(recommendation)
                if not any(lang in preferred for lang in backend_langs):
                    violations += 1
        
        # Check deployment constraints
        if "deployment_type" in constraints:
            total_constraints += 1
            deployment_type = constraints["deployment_type"]
            infra_types = [tech.name.lower() for tech in recommendation.infrastructure]
            
            if deployment_type == "on_premise" and any("cloud" in tech for tech in infra_types):
                violations += 1
            elif deployment_type == "cloud" and any("on_premise" in tech for tech in infra_types):
                violations += 1
        
        if total_constraints == 0:
            return 1.0
        
        compliance_rate = 1.0 - (violations / total_constraints)
        return max(0.0, compliance_rate)
    
    def _get_technology_scalability(self, tech_name: str) -> float:
        """Get scalability score for a technology"""
        
        scalability_scores = {
            "fastapi": 0.9, "django": 0.7, "express": 0.8,
            "react": 0.8, "vue": 0.8, "angular": 0.8,
            "postgresql": 0.9, "mongodb": 0.8, "redis": 0.9,
            "kubernetes": 1.0, "docker": 0.8, "nginx": 0.9
        }
        
        return scalability_scores.get(tech_name.lower(), 0.6)
    
    def _calculate_ecosystem_strength(self, recommendation: StackRecommendation) -> float:
        """Calculate strength of technology ecosystem"""
        
        ecosystem_scores = {
            "react": 0.95, "vue": 0.85, "angular": 0.9,
            "fastapi": 0.85, "django": 0.9, "express": 0.9,
            "postgresql": 0.95, "mongodb": 0.85, "mysql": 0.9,
            "python": 0.95, "javascript": 0.95, "typescript": 0.9
        }
        
        scores = []
        
        for category_techs in [
            recommendation.backend, recommendation.frontend, recommendation.database
        ]:
            for tech in category_techs:
                score = ecosystem_scores.get(tech.name.lower(), 0.6)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.6
    
    def _calculate_documentation_quality(self, recommendation: StackRecommendation) -> float:
        """Calculate documentation quality score"""
        
        doc_scores = {
            "react": 0.9, "vue": 0.9, "angular": 0.9,
            "fastapi": 0.95, "django": 0.9, "express": 0.8,
            "postgresql": 0.9, "mongodb": 0.8
        }
        
        scores = []
        
        for category_techs in [
            recommendation.backend, recommendation.frontend, recommendation.database
        ]:
            for tech in category_techs:
                score = doc_scores.get(tech.name.lower(), 0.6)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.6
    
    def _calculate_community_support(self, recommendation: StackRecommendation) -> float:
        """Calculate community support strength"""
        
        community_scores = {
            "react": 0.95, "vue": 0.85, "angular": 0.8,
            "fastapi": 0.8, "django": 0.9, "express": 0.9,
            "postgresql": 0.9, "mongodb": 0.8
        }
        
        scores = []
        
        for category_techs in [
            recommendation.backend, recommendation.frontend, recommendation.database
        ]:
            for tech in category_techs:
                score = community_scores.get(tech.name.lower(), 0.6)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.6
    
    def _calculate_technology_compatibility(self, recommendation: StackRecommendation) -> float:
        """Calculate internal technology compatibility"""
        
        # Simple compatibility checking
        compatibility_issues = 0
        total_pairs = 0
        
        all_techs = []
        for category_techs in [
            recommendation.backend, recommendation.frontend, recommendation.database,
            recommendation.infrastructure
        ]:
            all_techs.extend([tech.name.lower() for tech in category_techs])
        
        # Check known incompatibilities
        incompatible_pairs = {
            ("django", "mongodb"),  # Django ORM not optimal for MongoDB
            ("sqlite", "kubernetes"),  # SQLite not suitable for distributed systems
        }
        
        for i, tech1 in enumerate(all_techs):
            for tech2 in all_techs[i+1:]:
                total_pairs += 1
                if (tech1, tech2) in incompatible_pairs or (tech2, tech1) in incompatible_pairs:
                    compatibility_issues += 1
        
        if total_pairs == 0:
            return 1.0
        
        compatibility_rate = 1.0 - (compatibility_issues / total_pairs)
        return max(0.0, compatibility_rate)
    
    def _estimate_tech_costs(self, recommendation: StackRecommendation) -> float:
        """Estimate monthly costs for technology stack"""
        
        # Simplified cost estimation (monthly USD)
        cost_estimates = {
            "postgresql": 50,  # Managed service
            "mongodb": 60,
            "redis": 30,
            "kubernetes": 200,  # Managed cluster
            "docker": 0,  # Self-hosted
            "nginx": 0
        }
        
        total_cost = 0
        
        for category_techs in [
            recommendation.database, recommendation.infrastructure, recommendation.monitoring
        ]:
            for tech in category_techs:
                cost = cost_estimates.get(tech.name.lower(), 20)  # Default cost
                total_cost += cost
        
        return total_cost
    
    def _get_languages_from_recommendation(self, recommendation: StackRecommendation) -> List[str]:
        """Extract programming languages from recommendation"""
        
        tech_languages = {
            "fastapi": "python",
            "django": "python",
            "flask": "python",
            "express": "javascript",
            "react": "javascript",
            "vue": "javascript",
            "angular": "typescript"
        }
        
        languages = set()
        
        for category_techs in [recommendation.backend, recommendation.frontend]:
            for tech in category_techs:
                lang = tech_languages.get(tech.name.lower())
                if lang:
                    languages.add(lang)
        
        return list(languages)
    
    def _load_tech_reliability_data(self) -> Dict[str, float]:
        """Load technology reliability/maturity scores"""
        
        return {
            # Frontend
            "react": 0.95, "vue": 0.85, "angular": 0.9, "svelte": 0.7,
            
            # Backend
            "fastapi": 0.85, "django": 0.9, "flask": 0.8, "express": 0.9,
            "spring": 0.95, "gin": 0.8, "asp.net": 0.9,
            
            # Database
            "postgresql": 0.95, "mysql": 0.9, "mongodb": 0.85, "redis": 0.9,
            "sqlite": 0.8, "elasticsearch": 0.8,
            
            # Infrastructure
            "docker": 0.9, "kubernetes": 0.85, "nginx": 0.95,
            "terraform": 0.8, "ansible": 0.8
        }
    
    def _load_compatibility_matrix(self) -> Dict[Tuple[str, str], float]:
        """Load technology compatibility matrix"""
        
        return {
            ("django", "postgresql"): 0.95,
            ("fastapi", "postgresql"): 0.9,
            ("react", "express"): 0.9,
            ("vue", "fastapi"): 0.85,
            ("mongodb", "express"): 0.9,
            ("redis", "fastapi"): 0.9
        }