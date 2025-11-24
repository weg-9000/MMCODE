"""
Stack recommendation data models for A2A integration.
Defines Pydantic models for stack recommendations, quality assessment, and artifacts.
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
from datetime import datetime, timezone


class StackCategory(str, Enum):
    """Technology stack categories"""
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"
    DEVOPS = "devops"
    MONITORING = "monitoring"


class QualityAttribute(str, Enum):
    """Quality attributes for stack evaluation"""
    SUITABILITY = "suitability"
    COMPLETENESS = "completeness"
    FEASIBILITY = "feasibility"
    SCALABILITY = "scalability"
    MAINTAINABILITY = "maintainability"


class TechnologyChoice(BaseModel):
    """Individual technology selection with rationale"""
    name: str = Field(..., description="Technology name")
    version: Optional[str] = Field(None, description="Recommended version")
    category: StackCategory = Field(..., description="Technology category")
    reason: str = Field(..., description="Selection rationale")
    alternatives: List[str] = Field(default_factory=list, description="Alternative options")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        return round(v, 2)


class StackRecommendation(BaseModel):
    """Complete technology stack recommendation"""
    backend: List[TechnologyChoice] = Field(default_factory=list)
    frontend: List[TechnologyChoice] = Field(default_factory=list) 
    database: List[TechnologyChoice] = Field(default_factory=list)
    infrastructure: List[TechnologyChoice] = Field(default_factory=list)
    devops: List[TechnologyChoice] = Field(default_factory=list)
    monitoring: List[TechnologyChoice] = Field(default_factory=list)
    
    @field_validator('*', mode='before')
    @classmethod
    def ensure_lists(cls, v):
        return v if isinstance(v, list) else [v] if v else []


class QualityScore(BaseModel):
    """Quality assessment metrics"""
    suitability: float = Field(..., ge=0.0, le=1.0, description="Architecture fit")
    completeness: float = Field(..., ge=0.0, le=1.0, description="Coverage of requirements")
    feasibility: float = Field(..., ge=0.0, le=1.0, description="Implementation practicality")
    scalability: float = Field(..., ge=0.0, le=1.0, description="Growth accommodation")
    maintainability: float = Field(..., ge=0.0, le=1.0, description="Long-term sustainability")
    
    @property
    def overall_score(self) -> float:
        """Calculate weighted overall quality score"""
        weights = {
            'suitability': 0.3,
            'completeness': 0.25,
            'feasibility': 0.2,
            'scalability': 0.15,
            'maintainability': 0.1
        }
        return round(sum(
            getattr(self, attr) * weight 
            for attr, weight in weights.items()
        ), 2)
    
    @field_validator('*')
    @classmethod
    def validate_scores(cls, v):
        return round(v, 2)


class ArchitectureContext(BaseModel):
    """Input context from ArchitectAgent"""
    components: List[str] = Field(..., description="System components")
    patterns: List[str] = Field(default_factory=list, description="Architecture patterns")
    quality_attributes: List[str] = Field(default_factory=list, description="Quality requirements")
    constraints: Dict[str, Union[str, int, float]] = Field(default_factory=dict, description="Technical constraints")
    domain: str = Field(..., description="Application domain")
    scale: str = Field(default="medium", description="Expected scale: small/medium/large/enterprise")


class StackArtifact(BaseModel):
    """Stack recommendation artifact for A2A response"""
    recommendation: StackRecommendation = Field(..., description="Technology stack choices")
    quality_score: QualityScore = Field(..., description="Quality assessment")
    rationale: str = Field(..., description="Overall recommendation rationale")
    implementation_notes: List[str] = Field(default_factory=list, description="Implementation guidance")
    cost_estimate: Optional[Dict[str, float]] = Field(None, description="Cost projections")
    risk_assessment: List[str] = Field(default_factory=list, description="Risk factors")
    next_steps: List[str] = Field(default_factory=list, description="Action items")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict()


class StackTemplate(BaseModel):
    """Predefined stack template for fallback"""
    name: str
    domain: str
    description: str
    technologies: StackRecommendation
    min_quality_score: float = Field(default=0.7)
    use_cases: List[str] = Field(default_factory=list)