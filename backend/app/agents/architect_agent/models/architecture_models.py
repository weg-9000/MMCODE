"""Architecture Models for Architect Agent"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime


class ArchitecturePattern(Enum):
    """Common architecture patterns"""
    LAYERED = "layered"
    MICROSERVICES = "microservices"  
    MONOLITHIC = "monolithic"
    EVENT_DRIVEN = "event_driven"
    SERVERLESS = "serverless"
    HEXAGONAL = "hexagonal"
    CQRS = "cqrs"
    SAGA = "saga"
    MVC = "mvc"
    MVP = "mvp"
    MVVM = "mvvm"


class ComponentType(Enum):
    """Component classification types"""
    PRESENTATION = "presentation"
    BUSINESS_LOGIC = "business_logic"
    DATA_ACCESS = "data_access"
    INTEGRATION = "integration"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    MONITORING = "monitoring"


class ScalabilityTier(Enum):
    """Scalability requirements"""
    SMALL = "small"          # < 1K users
    MEDIUM = "medium"        # 1K - 10K users
    LARGE = "large"          # 10K - 100K users
    ENTERPRISE = "enterprise" # > 100K users


@dataclass
class ArchitecturalPattern:
    """Detailed architecture pattern specification"""
    name: str
    pattern_type: ArchitecturePattern
    description: str
    benefits: List[str] = field(default_factory=list)
    trade_offs: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    context: str = ""
    implementation_complexity: float = 0.5  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "benefits": self.benefits,
            "trade_offs": self.trade_offs,
            "use_cases": self.use_cases,
            "context": self.context,
            "implementation_complexity": self.implementation_complexity
        }


@dataclass
class Component:
    """System component specification"""
    name: str
    component_type: ComponentType
    description: str
    responsibilities: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    data_entities: List[str] = field(default_factory=list)
    quality_attributes: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "component_type": self.component_type.value,
            "description": self.description,
            "responsibilities": self.responsibilities,
            "interfaces": self.interfaces,
            "dependencies": self.dependencies,
            "technologies": self.technologies,
            "data_entities": self.data_entities,
            "quality_attributes": self.quality_attributes
        }


@dataclass
class ArchitectureDesign:
    """Complete architecture design specification"""
    design_id: str
    name: str
    description: str
    primary_pattern: ArchitecturePattern
    secondary_patterns: List[ArchitecturePattern] = field(default_factory=list)
    
    # Architecture tiers
    presentation_tier: Optional[str] = None
    business_tier: Optional[str] = None  
    data_tier: Optional[str] = None
    
    # Quality attributes
    scalability_tier: ScalabilityTier = ScalabilityTier.MEDIUM
    complexity_level: float = 0.5  # 0.0 to 1.0
    maintainability_score: float = 0.5
    performance_requirements: Dict[str, str] = field(default_factory=dict)
    security_requirements: Dict[str, str] = field(default_factory=dict)
    
    # Design decisions
    key_decisions: List[Dict[str, str]] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    risks: List[Dict[str, str]] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "design_id": self.design_id,
            "name": self.name,
            "description": self.description,
            "primary_pattern": self.primary_pattern.value,
            "secondary_patterns": [p.value for p in self.secondary_patterns],
            "presentation_tier": self.presentation_tier,
            "business_tier": self.business_tier,
            "data_tier": self.data_tier,
            "scalability_tier": self.scalability_tier.value,
            "complexity_level": self.complexity_level,
            "maintainability_score": self.maintainability_score,
            "performance_requirements": self.performance_requirements,
            "security_requirements": self.security_requirements,
            "key_decisions": self.key_decisions,
            "assumptions": self.assumptions,
            "constraints": self.constraints,
            "risks": self.risks,
            "created_at": self.created_at.isoformat(),
            "version": self.version
        }


@dataclass
class LayerSpec:
    """Architecture layer specification"""
    name: str
    purpose: str
    components: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Other layers this depends on
    technologies: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "components": self.components,
            "interfaces": self.interfaces,
            "dependencies": self.dependencies,
            "technologies": self.technologies,
            "patterns": self.patterns
        }


@dataclass
class IntegrationSpec:
    """Integration point specification"""
    name: str
    integration_type: str  # api, database, message_queue, file, etc.
    source_component: str
    target_component: str
    protocol: str  # HTTP, gRPC, AMQP, etc.
    data_format: str  # JSON, XML, Binary, etc.
    authentication: str  # OAuth, API Key, etc.
    error_handling: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "integration_type": self.integration_type,
            "source_component": self.source_component,
            "target_component": self.target_component,
            "protocol": self.protocol,
            "data_format": self.data_format,
            "authentication": self.authentication,
            "error_handling": self.error_handling
        }


@dataclass
class DeploymentSpec:
    """Deployment architecture specification"""
    deployment_pattern: str  # monolith, microservices, serverless
    hosting_model: str  # cloud, on-premise, hybrid
    containerization: bool = False
    orchestration: Optional[str] = None  # kubernetes, docker-compose
    load_balancing: Optional[str] = None
    auto_scaling: bool = False
    monitoring: List[str] = field(default_factory=list)
    backup_strategy: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_pattern": self.deployment_pattern,
            "hosting_model": self.hosting_model,
            "containerization": self.containerization,
            "orchestration": self.orchestration,
            "load_balancing": self.load_balancing,
            "auto_scaling": self.auto_scaling,
            "monitoring": self.monitoring,
            "backup_strategy": self.backup_strategy
        }