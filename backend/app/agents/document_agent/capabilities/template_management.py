"""Template Management - Document template handling and customization"""

from typing import Dict, Any, List, Optional
from ..models.document_models import DocumentTemplate, DocumentType, DocumentFormat


class TemplateManager:
    """Manages document templates and customization"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, DocumentTemplate]:
        """Load default document templates"""
        templates = {}
        
        # README template
        templates["default_readme"] = DocumentTemplate(
            template_id="default_readme",
            name="Default README Template",
            description="Standard README.md template with all essential sections",
            document_type=DocumentType.README,
            format=DocumentFormat.MARKDOWN,
            sections=[
                "title_and_description",
                "features",
                "technology_stack",
                "installation",
                "usage",
                "api_documentation",
                "contributing",
                "license"
            ],
            required_context=["analysis", "stack"],
            example_content="""# Project Name

Project description goes here.

## Features
- Feature 1
- Feature 2

## Installation
Instructions for installation.

## Usage
Usage examples and instructions.
"""
        )
        
        # OpenAPI template
        templates["openapi_3_0"] = DocumentTemplate(
            template_id="openapi_3_0",
            name="OpenAPI 3.0 Specification",
            description="Complete OpenAPI 3.0 specification template",
            document_type=DocumentType.OPENAPI,
            format=DocumentFormat.JSON,
            sections=[
                "info",
                "servers",
                "paths",
                "components",
                "security"
            ],
            required_context=["analysis"],
            example_content="""{
  "openapi": "3.0.0",
  "info": {
    "title": "API Title",
    "version": "1.0.0"
  },
  "paths": {}
}"""
        )
        
        # Deployment guide template
        templates["deployment_guide"] = DocumentTemplate(
            template_id="deployment_guide",
            name="Deployment Guide Template",
            description="Comprehensive deployment instructions",
            document_type=DocumentType.DEPLOYMENT_GUIDE,
            format=DocumentFormat.MARKDOWN,
            sections=[
                "introduction",
                "prerequisites",
                "environment_setup",
                "docker_deployment",
                "production_deployment",
                "troubleshooting"
            ],
            required_context=["stack", "architecture"],
            example_content="""# Deployment Guide

## Prerequisites
List of prerequisites.

## Docker Deployment
Docker deployment instructions.
"""
        )
        
        # API documentation template
        templates["api_documentation"] = DocumentTemplate(
            template_id="api_documentation",
            name="API Documentation Template",
            description="Comprehensive API documentation",
            document_type=DocumentType.API_DOCUMENTATION,
            format=DocumentFormat.MARKDOWN,
            sections=[
                "overview",
                "authentication",
                "endpoints",
                "rate_limiting",
                "sdks",
                "support"
            ],
            required_context=["analysis"],
            example_content="""# API Documentation

## Overview
API overview and base information.

## Authentication
Authentication methods and examples.
"""
        )
        
        # Technical specification template
        templates["technical_specification"] = DocumentTemplate(
            template_id="technical_specification",
            name="Technical Specification Template",
            description="Detailed technical specification document",
            document_type=DocumentType.TECHNICAL_SPECIFICATION,
            format=DocumentFormat.MARKDOWN,
            sections=[
                "document_info",
                "executive_summary",
                "requirements",
                "architecture",
                "technology_stack",
                "security",
                "performance",
                "implementation",
                "deployment"
            ],
            required_context=["analysis", "architecture", "stack"],
            example_content="""# Technical Specification

## Executive Summary
High-level technical overview.

## System Requirements
Functional and non-functional requirements.
"""
        )
        
        # ERD template
        templates["mermaid_erd"] = DocumentTemplate(
            template_id="mermaid_erd",
            name="Mermaid ERD Template",
            description="Entity Relationship Diagram in Mermaid format",
            document_type=DocumentType.ERD,
            format=DocumentFormat.MERMAID,
            sections=[
                "entities",
                "relationships",
                "constraints"
            ],
            required_context=["analysis"],
            example_content="""erDiagram
    ENTITY1 {
        UUID id PK
        VARCHAR name
    }
"""
        )
        
        # Context diagram template
        templates["mermaid_context"] = DocumentTemplate(
            template_id="mermaid_context",
            name="Mermaid Context Diagram Template",
            description="System context diagram in Mermaid format",
            document_type=DocumentType.CONTEXT_DIAGRAM,
            format=DocumentFormat.MERMAID,
            sections=[
                "system",
                "external_entities",
                "relationships"
            ],
            required_context=["analysis"],
            example_content="""flowchart TB
    System[System Name]
    User[User]
    
    User --> System
"""
        )
        
        return templates
    
    def get_template(self, template_id: str) -> Optional[DocumentTemplate]:
        """Get a specific template by ID"""
        return self._templates.get(template_id)
    
    def get_templates_by_type(self, doc_type: DocumentType) -> List[DocumentTemplate]:
        """Get all templates for a specific document type"""
        return [
            template for template in self._templates.values()
            if template.document_type == doc_type
        ]
    
    def get_all_templates(self) -> List[DocumentTemplate]:
        """Get all available templates"""
        return list(self._templates.values())
    
    def validate_template_context(self, template_id: str, context: Dict[str, Any]) -> Dict[str, bool]:
        """Validate if context has required data for template"""
        template = self.get_template(template_id)
        if not template:
            return {"valid": False, "error": "Template not found"}
        
        validation_result = {"valid": True}
        missing_context = []
        
        for required_ctx in template.required_context:
            if required_ctx not in context or not context[required_ctx]:
                missing_context.append(required_ctx)
        
        if missing_context:
            validation_result = {
                "valid": False,
                "missing_context": missing_context,
                "error": f"Missing required context: {', '.join(missing_context)}"
            }
        
        return validation_result
    
    def customize_template(self, 
                          base_template_id: str,
                          customizations: Dict[str, Any]) -> Optional[DocumentTemplate]:
        """Create a customized template based on a base template"""
        base_template = self.get_template(base_template_id)
        if not base_template:
            return None
        
        # Create customized template
        custom_template = DocumentTemplate(
            template_id=f"{base_template_id}_custom",
            name=customizations.get("name", f"{base_template.name} (Custom)"),
            description=customizations.get("description", base_template.description),
            document_type=base_template.document_type,
            format=customizations.get("format", base_template.format),
            sections=customizations.get("sections", base_template.sections.copy()),
            required_context=customizations.get("required_context", base_template.required_context.copy()),
            example_content=customizations.get("example_content", base_template.example_content),
            metadata={
                **base_template.metadata,
                **customizations.get("metadata", {}),
                "base_template": base_template_id,
                "customized": True
            }
        )
        
        return custom_template
    
    def add_custom_template(self, template: DocumentTemplate) -> bool:
        """Add a custom template to the manager"""
        try:
            self._templates[template.template_id] = template
            return True
        except Exception:
            return False
    
    def get_template_suggestions(self, 
                               context: Dict[str, Any],
                               doc_type: Optional[DocumentType] = None) -> List[str]:
        """Get template suggestions based on available context"""
        suggestions = []
        
        available_templates = (
            self.get_templates_by_type(doc_type) if doc_type 
            else self.get_all_templates()
        )
        
        for template in available_templates:
            validation = self.validate_template_context(template.template_id, context)
            if validation["valid"]:
                suggestions.append(template.template_id)
        
        return suggestions
    
    def get_section_templates(self, doc_type: DocumentType) -> Dict[str, str]:
        """Get section templates for a specific document type"""
        section_templates = {
            DocumentType.README: {
                "title_and_description": "# {project_name}\n\n{description}",
                "features": "## Features\n\n{features_list}",
                "installation": "## Installation\n\n{install_instructions}",
                "usage": "## Usage\n\n{usage_instructions}",
                "api_documentation": "## API Documentation\n\n{api_info}",
                "contributing": "## Contributing\n\n{contributing_guidelines}",
                "license": "## License\n\n{license_info}"
            },
            DocumentType.API_DOCUMENTATION: {
                "overview": "# {api_name} API Documentation\n\n{overview}",
                "authentication": "## Authentication\n\n{auth_methods}",
                "endpoints": "## Endpoints\n\n{endpoint_docs}",
                "rate_limiting": "## Rate Limiting\n\n{rate_limit_info}",
                "sdks": "## SDKs and Libraries\n\n{sdk_info}",
                "support": "## Support\n\n{support_info}"
            },
            DocumentType.DEPLOYMENT_GUIDE: {
                "introduction": "# Deployment Guide\n\n{intro}",
                "prerequisites": "## Prerequisites\n\n{prerequisites}",
                "environment_setup": "## Environment Setup\n\n{env_setup}",
                "docker_deployment": "## Docker Deployment\n\n{docker_instructions}",
                "production_deployment": "## Production Deployment\n\n{prod_instructions}",
                "troubleshooting": "## Troubleshooting\n\n{troubleshooting_info}"
            },
            DocumentType.TECHNICAL_SPECIFICATION: {
                "document_info": "# {title}\n\n## Document Information\n{doc_info}",
                "executive_summary": "## Executive Summary\n\n{summary}",
                "requirements": "## System Requirements\n\n{requirements}",
                "architecture": "## System Architecture\n\n{architecture}",
                "security": "## Security Specifications\n\n{security_specs}",
                "performance": "## Performance Requirements\n\n{performance_reqs}",
                "implementation": "## Implementation Guidelines\n\n{implementation_guidelines}",
                "deployment": "## Deployment Specifications\n\n{deployment_specs}"
            }
        }
        
        return section_templates.get(doc_type, {})
    
    def render_section(self, 
                      doc_type: DocumentType,
                      section_name: str,
                      variables: Dict[str, Any]) -> str:
        """Render a specific section using template and variables"""
        section_templates = self.get_section_templates(doc_type)
        template_str = section_templates.get(section_name, "{content}")
        
        try:
            return template_str.format(**variables)
        except KeyError as e:
            # Handle missing variables gracefully
            return template_str.replace(f"{{{e.args[0]}}}", f"[{e.args[0].upper()}_NOT_PROVIDED]")
    
    def get_template_metadata(self, template_id: str) -> Dict[str, Any]:
        """Get metadata for a specific template"""
        template = self.get_template(template_id)
        if not template:
            return {}
        
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "document_type": template.document_type.value,
            "format": template.format.value,
            "sections": template.sections,
            "required_context": template.required_context,
            "metadata": template.metadata
        }
    
    def export_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Export template configuration for sharing or backup"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "document_type": template.document_type.value,
            "format": template.format.value,
            "sections": template.sections,
            "required_context": template.required_context,
            "example_content": template.example_content,
            "metadata": template.metadata
        }
    
    def import_template(self, template_data: Dict[str, Any]) -> bool:
        """Import template from configuration data"""
        try:
            template = DocumentTemplate(
                template_id=template_data["template_id"],
                name=template_data["name"],
                description=template_data["description"],
                document_type=DocumentType(template_data["document_type"]),
                format=DocumentFormat(template_data["format"]),
                sections=template_data.get("sections", []),
                required_context=template_data.get("required_context", []),
                example_content=template_data.get("example_content"),
                metadata=template_data.get("metadata", {})
            )
            
            return self.add_custom_template(template)
        except Exception:
            return False