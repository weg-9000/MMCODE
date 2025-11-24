"""Document Agent - A2A Server for comprehensive documentation generation"""

import logging
import uuid
from typing import Any, Dict, List
from datetime import datetime, timezone

from ...shared.a2a_server.server import A2AServer, TaskHandler
from ...shared.models.a2a_models import AgentCard, A2ATask, Artifact, AgentFramework
from ..capabilities.document_generation import DocumentGenerationEngine
from ..capabilities.template_management import TemplateManager
from ..capabilities.quality_assessment import QualityAssessment
from ..models.document_models import (
    DocumentType, DocumentFormat, GeneratedDocument, 
    DocumentationSuite, DocumentGenerationRequest
)


class DocumentAgent(A2AServer):
    """
    Document generation agent that receives analysis, architecture, and stack data
    and creates comprehensive documentation including OpenAPI specs, ERDs, README files,
    deployment guides, and technical specifications.
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Create agent card
        agent_card = AgentCard(
            agent_id="document-agent",
            agent_name="Documentation Generation Agent",
            framework=AgentFramework.LANGCHAIN,
            capabilities=[
                "openapi_generation",
                "erd_generation",
                "readme_generation",
                "api_documentation",
                "deployment_guides",
                "technical_specifications",
                "context_diagrams",
                "user_manuals",
                "template_management",
                "quality_assessment"
            ],
            endpoint_url=config.get("own_endpoint", "http://localhost:8003"),
            version="1.0.0",
            metadata={
                "role": "documenter",
                "specializations": [
                    "openapi", "erd", "markdown", "technical_writing",
                    "api_docs", "deployment", "user_guides"
                ],
                "output_formats": [
                    "markdown", "json", "yaml", "mermaid", "plantuml", "html"
                ],
                "supported_document_types": [dt.value for dt in DocumentType]
            }
        )
        
        super().__init__(agent_card)
        
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize capabilities
        self.document_engine = DocumentGenerationEngine(config)
        self.template_manager = TemplateManager(config)
        self.quality_assessor = QualityAssessment(config)
    
    @TaskHandler("document_generation")
    async def handle_document_generation(self, task: A2ATask) -> Artifact:
        """
        Main document generation task handler.
        Creates comprehensive documentation suite from analysis, architecture, and stack data.
        """
        self.logger.info(f"Starting document generation for task {task.task_id}")
        
        try:
            # Extract context data
            analysis_data = task.context.get("analysis")
            architecture_data = task.context.get("architecture")
            stack_data = task.context.get("stack")
            
            if not any([analysis_data, architecture_data, stack_data]):
                raise ValueError("No source data provided for documentation generation")
            
            # Create documentation suite
            suite = await self._create_documentation_suite(
                analysis_data, architecture_data, stack_data, task
            )
            
            # Assess documentation quality
            quality_metrics = await self.quality_assessor.assess_suite_quality(suite)
            
            # Prepare result
            doc_result = {
                "documentation_suite": suite.to_dict(),
                "quality_assessment": quality_metrics,
                "generation_summary": {
                    "total_documents": len(suite.documents),
                    "document_types": [doc.document_type.value for doc in suite.documents],
                    "overall_quality": suite.suite_quality_score,
                    "coverage_matrix": suite.coverage_matrix,
                    "generation_time": datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Calculate overall quality score
            overall_quality = suite.suite_quality_score
            
            self.logger.info(f"Documentation generation completed with {len(suite.documents)} documents, quality: {overall_quality}")
            
            return Artifact(
                artifact_type="documentation_suite",
                content=doc_result,
                quality_score=overall_quality,
                metadata={
                    "task_id": task.task_id,
                    "agent_id": self.agent_card.agent_id,
                    "document_count": len(suite.documents),
                    "processing_time": (datetime.now(timezone.utc) - task.created_at).total_seconds(),
                    "coverage_complete": all(suite.coverage_matrix.values()),
                    "formats_generated": list(set(doc.format.value for doc in suite.documents))
                },
                created_by=self.agent_card.agent_id
            )
            
        except Exception as e:
            self.logger.error(f"Document generation failed for task {task.task_id}: {e}")
            raise
    
    @TaskHandler("openapi_generation")
    async def handle_openapi_generation(self, task: A2ATask) -> Artifact:
        """
        Focused OpenAPI specification generation.
        """
        self.logger.info(f"Starting OpenAPI generation for task {task.task_id}")
        
        try:
            analysis_data = task.context.get("analysis")
            architecture_data = task.context.get("architecture")
            stack_data = task.context.get("stack")
            
            # Generate OpenAPI specification
            openapi_doc = await self.document_engine.generate_openapi_spec(
                analysis_data, architecture_data, stack_data
            )
            
            # Quality assessment
            quality_score = await self.quality_assessor.assess_document_quality(openapi_doc)
            
            return Artifact(
                artifact_type="openapi_specification",
                content=openapi_doc.to_dict(),
                quality_score=quality_score,
                metadata={
                    "task_id": task.task_id,
                    "document_type": "openapi",
                    "format": "json"
                },
                created_by=self.agent_card.agent_id
            )
            
        except Exception as e:
            self.logger.error(f"OpenAPI generation failed for task {task.task_id}: {e}")
            raise
    
    @TaskHandler("readme_generation")
    async def handle_readme_generation(self, task: A2ATask) -> Artifact:
        """
        Focused README generation.
        """
        self.logger.info(f"Starting README generation for task {task.task_id}")
        
        try:
            analysis_data = task.context.get("analysis")
            architecture_data = task.context.get("architecture")
            stack_data = task.context.get("stack")
            
            # Generate README
            readme_doc = await self.document_engine.generate_readme(
                analysis_data, architecture_data, stack_data
            )
            
            # Quality assessment
            quality_score = await self.quality_assessor.assess_document_quality(readme_doc)
            
            return Artifact(
                artifact_type="readme",
                content=readme_doc.to_dict(),
                quality_score=quality_score,
                metadata={
                    "task_id": task.task_id,
                    "document_type": "readme",
                    "format": "markdown"
                },
                created_by=self.agent_card.agent_id
            )
            
        except Exception as e:
            self.logger.error(f"README generation failed for task {task.task_id}: {e}")
            raise
    
    @TaskHandler("deployment_guide_generation")
    async def handle_deployment_guide_generation(self, task: A2ATask) -> Artifact:
        """
        Focused deployment guide generation.
        """
        self.logger.info(f"Starting deployment guide generation for task {task.task_id}")
        
        try:
            architecture_data = task.context.get("architecture")
            stack_data = task.context.get("stack")
            
            if not stack_data:
                raise ValueError("Stack data required for deployment guide generation")
            
            # Generate deployment guide
            deploy_doc = await self.document_engine.generate_deployment_guide(
                architecture_data, stack_data
            )
            
            # Quality assessment
            quality_score = await self.quality_assessor.assess_document_quality(deploy_doc)
            
            return Artifact(
                artifact_type="deployment_guide",
                content=deploy_doc.to_dict(),
                quality_score=quality_score,
                metadata={
                    "task_id": task.task_id,
                    "document_type": "deployment_guide",
                    "format": "markdown"
                },
                created_by=self.agent_card.agent_id
            )
            
        except Exception as e:
            self.logger.error(f"Deployment guide generation failed for task {task.task_id}: {e}")
            raise
    
    async def _create_documentation_suite(self,
                                        analysis_data: Dict[str, Any],
                                        architecture_data: Dict[str, Any],
                                        stack_data: Dict[str, Any],
                                        task: A2ATask) -> DocumentationSuite:
        """
        Create comprehensive documentation suite.
        """
        suite_id = str(uuid.uuid4())
        suite = DocumentationSuite(
            suite_id=suite_id,
            name=f"Documentation Suite - Task {task.task_id}",
            description="Comprehensive documentation generated from system analysis"
        )
        
        # Generate core documents
        documents_to_generate = [
            (DocumentType.README, "generate_readme"),
            (DocumentType.API_DOCUMENTATION, "generate_api_documentation"),
            (DocumentType.TECHNICAL_SPECIFICATION, "generate_technical_specification"),
            (DocumentType.DEPLOYMENT_GUIDE, "generate_deployment_guide")
        ]
        
        # Add OpenAPI if REST API detected
        if self._has_rest_api(analysis_data, architecture_data):
            documents_to_generate.append((DocumentType.OPENAPI, "generate_openapi_spec"))
        
        # Add ERD if database detected
        if self._has_database(architecture_data, stack_data):
            documents_to_generate.append((DocumentType.ERD, "generate_erd"))
        
        # Add context diagram
        documents_to_generate.append((DocumentType.CONTEXT_DIAGRAM, "generate_context_diagram"))
        
        # Generate each document
        for doc_type, method_name in documents_to_generate:
            try:
                method = getattr(self.document_engine, method_name)
                document = await method(analysis_data, architecture_data, stack_data)
                suite.add_document(document)
                self.logger.info(f"Generated {doc_type.value} document")
            except Exception as e:
                self.logger.warning(f"Failed to generate {doc_type.value}: {e}")
        
        return suite
    
    def _has_rest_api(self, analysis_data: Dict[str, Any], architecture_data: Dict[str, Any]) -> bool:
        """Check if system has REST API components"""
        if not analysis_data:
            return False
        
        # Check for API-related entities and use cases
        entities = analysis_data.get("entities", [])
        use_cases = analysis_data.get("use_cases", [])
        
        api_indicators = ["api", "endpoint", "rest", "service", "controller"]
        
        # Check entities and use cases for API indicators
        all_text = " ".join(entities + use_cases).lower()
        return any(indicator in all_text for indicator in api_indicators)
    
    def _has_database(self, architecture_data: Dict[str, Any], stack_data: Dict[str, Any]) -> bool:
        """Check if system has database components"""
        if stack_data:
            # Check for database in technology stack
            stack_content = str(stack_data).lower()
            db_indicators = ["database", "postgresql", "mysql", "mongodb", "sqlite", "redis"]
            if any(indicator in stack_content for indicator in db_indicators):
                return True
        
        if architecture_data:
            # Check for data layer in architecture
            arch_content = str(architecture_data).lower()
            return "data" in arch_content or "database" in arch_content or "persistence" in arch_content
        
        return False
    
    async def get_supported_document_types(self) -> List[Dict[str, Any]]:
        """Get list of supported document types and formats"""
        return [
            {
                "type": doc_type.value,
                "description": self._get_document_description(doc_type),
                "formats": self._get_supported_formats(doc_type)
            }
            for doc_type in DocumentType
        ]
    
    def _get_document_description(self, doc_type: DocumentType) -> str:
        """Get description for document type"""
        descriptions = {
            DocumentType.OPENAPI: "OpenAPI 3.0 specification for REST APIs",
            DocumentType.ERD: "Entity Relationship Diagram for database design",
            DocumentType.README: "Project README with setup and usage instructions",
            DocumentType.CONTEXT_DIAGRAM: "System context diagram showing external interactions",
            DocumentType.API_DOCUMENTATION: "Comprehensive API documentation",
            DocumentType.DEPLOYMENT_GUIDE: "Step-by-step deployment instructions",
            DocumentType.USER_MANUAL: "End-user manual and guides",
            DocumentType.TECHNICAL_SPECIFICATION: "Technical specification document"
        }
        return descriptions.get(doc_type, "Documentation")
    
    def _get_supported_formats(self, doc_type: DocumentType) -> List[str]:
        """Get supported formats for document type"""
        format_map = {
            DocumentType.OPENAPI: ["json", "yaml"],
            DocumentType.ERD: ["mermaid", "plantuml"],
            DocumentType.README: ["markdown"],
            DocumentType.CONTEXT_DIAGRAM: ["mermaid", "plantuml"],
            DocumentType.API_DOCUMENTATION: ["markdown", "html"],
            DocumentType.DEPLOYMENT_GUIDE: ["markdown"],
            DocumentType.USER_MANUAL: ["markdown", "html"],
            DocumentType.TECHNICAL_SPECIFICATION: ["markdown"]
        }
        return format_map.get(doc_type, ["markdown"])