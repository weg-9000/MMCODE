"""Document Agent Models - Data structures for document generation"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class DocumentType(Enum):
    """Supported document types for generation"""
    OPENAPI = "openapi"
    ERD = "erd"
    README = "readme"
    CONTEXT_DIAGRAM = "context_diagram"
    API_DOCUMENTATION = "api_documentation"
    DEPLOYMENT_GUIDE = "deployment_guide"
    USER_MANUAL = "user_manual"
    TECHNICAL_SPECIFICATION = "technical_specification"


class DocumentFormat(Enum):
    """Supported document formats"""
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"
    MERMAID = "mermaid"
    PLANTUML = "plantuml"
    HTML = "html"
    PDF = "pdf"


class DocumentTemplate(BaseModel):
    """Document template definition"""
    template_id: str
    name: str
    description: str
    document_type: DocumentType
    format: DocumentFormat
    sections: List[str] = Field(default_factory=list)
    required_context: List[str] = Field(default_factory=list)
    example_content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentSection(BaseModel):
    """Individual document section"""
    section_id: str
    title: str
    content: str
    format: DocumentFormat
    order: int = 0
    subsections: List["DocumentSection"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeneratedDocument(BaseModel):
    """Generated document result"""
    document_id: str
    document_type: DocumentType
    format: DocumentFormat
    title: str
    content: str
    sections: List[DocumentSection] = Field(default_factory=list)
    
    # Quality metrics
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    readability_score: float = 0.0
    coverage_score: float = 0.0
    
    # Generation metadata
    template_used: Optional[str] = None
    generation_time: datetime = Field(default_factory=datetime.utcnow)
    word_count: int = 0
    character_count: int = 0
    
    # Source context
    source_analysis: Optional[Dict[str, Any]] = None
    source_architecture: Optional[Dict[str, Any]] = None
    source_stack: Optional[Dict[str, Any]] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def calculate_overall_quality(self) -> float:
        """Calculate overall quality score"""
        scores = [
            self.completeness_score,
            self.accuracy_score,
            self.readability_score,
            self.coverage_score
        ]
        valid_scores = [s for s in scores if s > 0]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "document_id": self.document_id,
            "document_type": self.document_type.value,
            "format": self.format.value,
            "title": self.title,
            "content": self.content,
            "sections": [section.dict() for section in self.sections],
            "quality_metrics": {
                "completeness": self.completeness_score,
                "accuracy": self.accuracy_score,
                "readability": self.readability_score,
                "coverage": self.coverage_score,
                "overall": self.calculate_overall_quality()
            },
            "metadata": {
                **self.metadata,
                "template_used": self.template_used,
                "generation_time": self.generation_time.isoformat(),
                "word_count": self.word_count,
                "character_count": self.character_count
            },
            "source_context": {
                "analysis": self.source_analysis,
                "architecture": self.source_architecture,
                "stack": self.source_stack
            }
        }


class DocumentGenerationRequest(BaseModel):
    """Request for document generation"""
    document_type: DocumentType
    format: DocumentFormat = DocumentFormat.MARKDOWN
    template_id: Optional[str] = None
    custom_sections: List[str] = Field(default_factory=list)
    
    # Source context
    analysis_data: Optional[Dict[str, Any]] = None
    architecture_data: Optional[Dict[str, Any]] = None
    stack_data: Optional[Dict[str, Any]] = None
    
    # Generation options
    include_examples: bool = True
    include_diagrams: bool = True
    include_templates: bool = False
    target_audience: str = "developer"  # developer, stakeholder, user
    detail_level: str = "detailed"  # brief, standard, detailed, comprehensive
    
    # Custom parameters
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class DocumentationSuite(BaseModel):
    """Complete documentation suite"""
    suite_id: str
    name: str
    description: str
    documents: List[GeneratedDocument] = Field(default_factory=list)
    
    # Suite metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    
    # Quality aggregation
    suite_quality_score: float = 0.0
    coverage_matrix: Dict[str, bool] = Field(default_factory=dict)
    
    def calculate_suite_quality(self) -> float:
        """Calculate overall suite quality"""
        if not self.documents:
            return 0.0
        
        total_quality = sum(doc.calculate_overall_quality() for doc in self.documents)
        return total_quality / len(self.documents)
    
    def update_coverage_matrix(self):
        """Update documentation coverage matrix"""
        doc_types = [doc.document_type.value for doc in self.documents]
        
        # Standard documentation requirements
        required_docs = [
            DocumentType.README.value,
            DocumentType.API_DOCUMENTATION.value,
            DocumentType.TECHNICAL_SPECIFICATION.value,
            DocumentType.DEPLOYMENT_GUIDE.value
        ]
        
        self.coverage_matrix = {
            doc_type: doc_type in doc_types for doc_type in required_docs
        }
    
    def add_document(self, document: GeneratedDocument):
        """Add document to suite"""
        self.documents.append(document)
        self.updated_at = datetime.utcnow()
        self.suite_quality_score = self.calculate_suite_quality()
        self.update_coverage_matrix()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "suite_id": self.suite_id,
            "name": self.name,
            "description": self.description,
            "documents": [doc.to_dict() for doc in self.documents],
            "metadata": {
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "version": self.version,
                "document_count": len(self.documents),
                "suite_quality_score": self.suite_quality_score,
                "coverage_matrix": self.coverage_matrix
            }
        }


# Update forward references
DocumentSection.model_rebuild()