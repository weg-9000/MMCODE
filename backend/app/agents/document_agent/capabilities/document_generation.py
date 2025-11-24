"""Document Generation Engine - Core document creation capabilities"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..models.document_models import (
    GeneratedDocument, DocumentType, DocumentFormat, DocumentSection
)


class DocumentGenerationEngine:
    """Core engine for generating various types of documentation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    async def generate_readme(self,
                            analysis_data: Optional[Dict[str, Any]],
                            architecture_data: Optional[Dict[str, Any]],
                            stack_data: Optional[Dict[str, Any]]) -> GeneratedDocument:
        """Generate comprehensive README.md file"""
        
        # Extract key information
        project_name = self._extract_project_name(analysis_data)
        entities = analysis_data.get("entities", []) if analysis_data else []
        use_cases = analysis_data.get("use_cases", []) if analysis_data else []
        tech_stack = self._extract_tech_stack(stack_data)
        architecture_summary = self._extract_architecture_summary(architecture_data)
        
        # Build README content
        readme_sections = []
        
        # Title and description
        description = self._generate_project_description(entities, use_cases)
        title_section = f"# {project_name}\n\n{description}"
        readme_sections.append(title_section)
        
        # Features section
        if use_cases:
            features_content = "## Features\n\n"
            for use_case in use_cases[:10]:  # Limit to top 10
                features_content += f"- {use_case}\n"
            readme_sections.append(features_content)
        
        # Technology Stack
        if tech_stack:
            tech_content = "## Technology Stack\n\n"
            for category, technologies in tech_stack.items():
                if technologies:
                    tech_content += f"### {category.title()}\n"
                    for tech in technologies:
                        tech_content += f"- {tech}\n"
                    tech_content += "\n"
            readme_sections.append(tech_content)
        
        # Architecture Overview
        if architecture_summary:
            arch_content = "## Architecture\n\n"
            arch_content += architecture_summary + "\n"
            readme_sections.append(arch_content)
        
        # Installation section
        install_content = self._generate_installation_section(tech_stack)
        readme_sections.append(install_content)
        
        # Usage section
        usage_content = self._generate_usage_section(use_cases)
        readme_sections.append(usage_content)
        
        # API section if applicable
        if self._has_api_components(entities, use_cases):
            api_content = "## API Documentation\n\n"
            api_content += "API documentation is available at `/docs` when running the server.\n"
            readme_sections.append(api_content)
        
        # Contributing section
        contributing_content = """## Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
"""
        readme_sections.append(contributing_content)
        
        # License section
        license_content = "## License\n\nDistributed under the MIT License. See `LICENSE` for more information.\n"
        readme_sections.append(license_content)
        
        # Combine all sections
        full_content = "\n".join(readme_sections)
        
        # Calculate metrics
        word_count = len(full_content.split())
        character_count = len(full_content)
        
        return GeneratedDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.README,
            format=DocumentFormat.MARKDOWN,
            title=f"{project_name} - README",
            content=full_content,
            completeness_score=0.9,
            accuracy_score=0.8,
            readability_score=0.85,
            coverage_score=0.9,
            word_count=word_count,
            character_count=character_count,
            source_analysis=analysis_data,
            source_architecture=architecture_data,
            source_stack=stack_data,
            template_used="default_readme"
        )
    
    async def generate_openapi_spec(self,
                                  analysis_data: Optional[Dict[str, Any]],
                                  architecture_data: Optional[Dict[str, Any]],
                                  stack_data: Optional[Dict[str, Any]]) -> GeneratedDocument:
        """Generate OpenAPI 3.0 specification"""
        
        project_name = self._extract_project_name(analysis_data)
        entities = analysis_data.get("entities", []) if analysis_data else []
        use_cases = analysis_data.get("use_cases", []) if analysis_data else []
        
        # Build OpenAPI specification
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{project_name} API",
                "description": f"API specification for {project_name}",
                "version": "1.0.0",
                "contact": {
                    "name": "API Support",
                    "email": "support@example.com"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                },
                {
                    "url": "https://api.example.com",
                    "description": "Production server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            },
            "security": [
                {"bearerAuth": []}
            ]
        }
        
        # Generate schemas from entities
        for entity in entities:
            schema_name = entity.replace(" ", "").replace("-", "")
            openapi_spec["components"]["schemas"][schema_name] = {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid",
                        "description": f"Unique identifier for {entity}"
                    },
                    "name": {
                        "type": "string",
                        "description": f"Name of the {entity}"
                    },
                    "created_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Creation timestamp"
                    },
                    "updated_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Last update timestamp"
                    }
                },
                "required": ["id", "name", "created_at"]
            }
        
        # Generate paths from use cases and entities
        for entity in entities:
            entity_path = entity.lower().replace(" ", "-")
            schema_name = entity.replace(" ", "").replace("-", "")
            
            # CRUD operations
            openapi_spec["paths"][f"/{entity_path}"] = {
                "get": {
                    "summary": f"List {entity}s",
                    "description": f"Retrieve a list of {entity}s",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": f"#/components/schemas/{schema_name}"}
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": f"Create {entity}",
                    "description": f"Create a new {entity}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                                }
                            }
                        }
                    }
                }
            }
            
            openapi_spec["paths"][f"/{entity_path}/{{id}}"] = {
                "get": {
                    "summary": f"Get {entity} by ID",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "format": "uuid"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                                }
                            }
                        },
                        "404": {
                            "description": f"{entity} not found"
                        }
                    }
                },
                "put": {
                    "summary": f"Update {entity}",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "format": "uuid"}
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Updated successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                                }
                            }
                        }
                    }
                },
                "delete": {
                    "summary": f"Delete {entity}",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "format": "uuid"}
                        }
                    ],
                    "responses": {
                        "204": {
                            "description": "Deleted successfully"
                        },
                        "404": {
                            "description": f"{entity} not found"
                        }
                    }
                }
            }
        
        # Convert to JSON string
        openapi_content = json.dumps(openapi_spec, indent=2)
        
        return GeneratedDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.OPENAPI,
            format=DocumentFormat.JSON,
            title=f"{project_name} OpenAPI Specification",
            content=openapi_content,
            completeness_score=0.85,
            accuracy_score=0.9,
            readability_score=0.8,
            coverage_score=0.85,
            word_count=len(openapi_content.split()),
            character_count=len(openapi_content),
            source_analysis=analysis_data,
            source_architecture=architecture_data,
            source_stack=stack_data,
            template_used="openapi_3_0"
        )
    
    async def generate_deployment_guide(self,
                                      architecture_data: Optional[Dict[str, Any]],
                                      stack_data: Optional[Dict[str, Any]]) -> GeneratedDocument:
        """Generate deployment guide"""
        
        tech_stack = self._extract_tech_stack(stack_data)
        
        deployment_sections = []
        
        # Introduction
        intro = """# Deployment Guide

This guide provides step-by-step instructions for deploying the application in different environments.

## Prerequisites

Before deploying, ensure you have the following:

- Docker and Docker Compose installed
- Access to target deployment environment
- Required environment variables configured
- Database connection details
"""
        deployment_sections.append(intro)
        
        # Environment setup
        env_setup = """## Environment Setup

### Development Environment

1. Clone the repository:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Install dependencies:
"""
        
        if "python" in str(tech_stack).lower() or "fastapi" in str(tech_stack).lower():
            env_setup += """
```bash
pip install -r requirements.txt
```
"""
        elif "node" in str(tech_stack).lower() or "javascript" in str(tech_stack).lower():
            env_setup += """
```bash
npm install
```
"""
        
        env_setup += """
3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```
"""
        deployment_sections.append(env_setup)
        
        # Docker deployment
        docker_section = """## Docker Deployment

### Using Docker Compose

1. Build and start services:
```bash
docker-compose up --build
```

2. Run database migrations (if applicable):
```bash
docker-compose exec api python -m alembic upgrade head
```

### Using Docker

1. Build the image:
```bash
docker build -t app-name .
```

2. Run the container:
```bash
docker run -p 8000:8000 --env-file .env app-name
```
"""
        deployment_sections.append(docker_section)
        
        # Production deployment
        prod_section = """## Production Deployment

### Prerequisites
- Production server with Docker support
- SSL certificate configured
- Database server running
- Environment variables secured

### Steps

1. Clone repository on production server
2. Configure production environment variables
3. Build and deploy using Docker Compose:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. Verify deployment:
```bash
curl https://your-domain.com/health
```

### Monitoring
- Check application logs: `docker-compose logs app`
- Monitor resource usage: `docker stats`
- Database health: `docker-compose logs db`
"""
        deployment_sections.append(prod_section)
        
        # Troubleshooting
        troubleshooting = """## Troubleshooting

### Common Issues

1. **Port already in use**
   - Check running processes: `lsof -i :8000`
   - Kill conflicting processes or change port

2. **Database connection failed**
   - Verify database credentials in .env
   - Check database server status
   - Ensure network connectivity

3. **Permission denied errors**
   - Check file permissions: `ls -la`
   - Fix ownership: `sudo chown -R $USER:$USER .`

4. **Out of memory errors**
   - Monitor memory usage: `free -h`
   - Increase server resources or optimize application

### Getting Help
- Check application logs for error details
- Review documentation and README
- Contact support team if issues persist
"""
        deployment_sections.append(troubleshooting)
        
        full_content = "\n".join(deployment_sections)
        
        return GeneratedDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.DEPLOYMENT_GUIDE,
            format=DocumentFormat.MARKDOWN,
            title="Deployment Guide",
            content=full_content,
            completeness_score=0.9,
            accuracy_score=0.85,
            readability_score=0.9,
            coverage_score=0.85,
            word_count=len(full_content.split()),
            character_count=len(full_content),
            source_architecture=architecture_data,
            source_stack=stack_data,
            template_used="deployment_guide"
        )
    
    async def generate_api_documentation(self,
                                       analysis_data: Optional[Dict[str, Any]],
                                       architecture_data: Optional[Dict[str, Any]],
                                       stack_data: Optional[Dict[str, Any]]) -> GeneratedDocument:
        """Generate comprehensive API documentation"""
        
        project_name = self._extract_project_name(analysis_data)
        entities = analysis_data.get("entities", []) if analysis_data else []
        
        api_sections = []
        
        # API Introduction
        intro = f"""# {project_name} API Documentation

## Overview
This document provides comprehensive documentation for the {project_name} REST API.

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://api.example.com`

## Authentication
All API endpoints require authentication using Bearer tokens.

### Getting a Token
```bash
curl -X POST /auth/login \\
  -H "Content-Type: application/json" \\
  -d '{{"email": "user@example.com", "password": "password"}}'
```

### Using the Token
Include the token in the Authorization header:
```bash
Authorization: Bearer <your-token-here>
```

## Response Format
All responses follow this standard format:

```json
{{
  "success": true,
  "data": {{}},
  "message": "Optional message",
  "timestamp": "2024-01-01T00:00:00Z"
}}
```

## Error Handling
Errors return appropriate HTTP status codes with error details:

```json
{{
  "success": false,
  "error": {{
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {{}}
  }},
  "timestamp": "2024-01-01T00:00:00Z"
}}
```
"""
        api_sections.append(intro)
        
        # Generate API endpoints for each entity
        for entity in entities:
            entity_name = entity.replace(" ", "").replace("-", "")
            endpoint_path = entity.lower().replace(" ", "-")
            
            entity_section = f"""
## {entity} Endpoints

### List {entity}s
**GET** `/{endpoint_path}`

Retrieve a list of {entity}s with optional filtering and pagination.

#### Query Parameters
- `page` (integer): Page number (default: 1)
- `limit` (integer): Items per page (default: 10, max: 100)
- `search` (string): Search term for filtering
- `sort` (string): Sort field (default: created_at)
- `order` (string): Sort order (asc|desc, default: desc)

#### Response
```json
{{
  "success": true,
  "data": {{
    "items": [
      {{
        "id": "uuid",
        "name": "string",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }}
    ],
    "pagination": {{
      "page": 1,
      "limit": 10,
      "total": 100,
      "pages": 10
    }}
  }}
}}
```

### Get {entity} by ID
**GET** `/{endpoint_path}/{{id}}`

Retrieve a specific {entity} by its ID.

#### Path Parameters
- `id` (uuid): {entity} identifier

#### Response
```json
{{
  "success": true,
  "data": {{
    "id": "uuid",
    "name": "string",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }}
}}
```

### Create {entity}
**POST** `/{endpoint_path}`

Create a new {entity}.

#### Request Body
```json
{{
  "name": "string"
}}
```

#### Response
```json
{{
  "success": true,
  "data": {{
    "id": "uuid",
    "name": "string",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }},
  "message": "{entity} created successfully"
}}
```

### Update {entity}
**PUT** `/{endpoint_path}/{{id}}`

Update an existing {entity}.

#### Path Parameters
- `id` (uuid): {entity} identifier

#### Request Body
```json
{{
  "name": "string"
}}
```

#### Response
```json
{{
  "success": true,
  "data": {{
    "id": "uuid",
    "name": "string",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }},
  "message": "{entity} updated successfully"
}}
```

### Delete {entity}
**DELETE** `/{endpoint_path}/{{id}}`

Delete a {entity}.

#### Path Parameters
- `id` (uuid): {entity} identifier

#### Response
```json
{{
  "success": true,
  "message": "{entity} deleted successfully"
}}
```
"""
            api_sections.append(entity_section)
        
        # Rate limiting section
        rate_limit_section = """
## Rate Limiting

API requests are rate limited to prevent abuse:

- **Free tier**: 100 requests per hour
- **Premium tier**: 1000 requests per hour

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Request limit per hour
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

## SDKs and Libraries

### JavaScript/Node.js
```bash
npm install @company/api-client
```

```javascript
import ApiClient from '@company/api-client';

const client = new ApiClient('your-api-token');
const users = await client.users.list();
```

### Python
```bash
pip install company-api-client
```

```python
from company_api import ApiClient

client = ApiClient('your-api-token')
users = client.users.list()
```

## Support

For API support and questions:
- **Email**: api-support@company.com
- **Documentation**: https://docs.company.com
- **Status Page**: https://status.company.com
"""
        api_sections.append(rate_limit_section)
        
        full_content = "\n".join(api_sections)
        
        return GeneratedDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.API_DOCUMENTATION,
            format=DocumentFormat.MARKDOWN,
            title=f"{project_name} API Documentation",
            content=full_content,
            completeness_score=0.95,
            accuracy_score=0.9,
            readability_score=0.9,
            coverage_score=0.9,
            word_count=len(full_content.split()),
            character_count=len(full_content),
            source_analysis=analysis_data,
            source_architecture=architecture_data,
            source_stack=stack_data,
            template_used="api_documentation"
        )
    
    async def generate_technical_specification(self,
                                             analysis_data: Optional[Dict[str, Any]],
                                             architecture_data: Optional[Dict[str, Any]],
                                             stack_data: Optional[Dict[str, Any]]) -> GeneratedDocument:
        """Generate technical specification document"""
        
        project_name = self._extract_project_name(analysis_data)
        
        spec_sections = []
        
        # Title and overview
        overview = f"""# {project_name} Technical Specification

## Document Information
- **Version**: 1.0.0
- **Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
- **Status**: Draft

## Executive Summary
This document provides the technical specification for {project_name}, including system architecture, technology stack, and implementation details.

## Scope
This specification covers:
- System architecture and design
- Technology stack and dependencies
- Data models and API specifications
- Security and performance requirements
- Deployment and operational considerations
"""
        spec_sections.append(overview)
        
        # Requirements section
        if analysis_data:
            entities = analysis_data.get("entities", [])
            use_cases = analysis_data.get("use_cases", [])
            quality_attributes = analysis_data.get("quality_attributes", [])
            
            requirements = """## System Requirements

### Functional Requirements
"""
            for i, use_case in enumerate(use_cases[:10], 1):
                requirements += f"{i}. {use_case}\n"
            
            requirements += "\n### Non-Functional Requirements\n"
            for i, qa in enumerate(quality_attributes, 1):
                requirements += f"{i}. {qa}\n"
            
            if entities:
                requirements += "\n### Core Entities\n"
                for entity in entities:
                    requirements += f"- {entity}\n"
            
            spec_sections.append(requirements)
        
        # Architecture section
        if architecture_data:
            arch_section = """## System Architecture

### Overview
The system follows a modern, scalable architecture pattern designed for maintainability and performance.

### Architecture Patterns
- **Pattern**: Microservices / Monolithic (based on analysis)
- **Communication**: RESTful APIs
- **Data Layer**: Relational/NoSQL database
- **Caching**: Redis for session and data caching
- **Authentication**: JWT-based authentication

### System Components
1. **Presentation Layer**: Frontend application
2. **Application Layer**: Business logic and API endpoints
3. **Data Layer**: Database and data access
4. **Integration Layer**: External service integrations

### Deployment Architecture
- **Containerization**: Docker containers
- **Orchestration**: Docker Compose / Kubernetes
- **Load Balancing**: Application load balancer
- **Database**: Managed database service
"""
            spec_sections.append(arch_section)
        
        # Technology stack
        if stack_data:
            tech_section = "## Technology Stack\n\n"
            tech_stack = self._extract_tech_stack(stack_data)
            
            for category, technologies in tech_stack.items():
                if technologies:
                    tech_section += f"### {category.title()}\n"
                    for tech in technologies:
                        tech_section += f"- {tech}\n"
                    tech_section += "\n"
            
            spec_sections.append(tech_section)
        
        # Security section
        security_section = """## Security Specifications

### Authentication & Authorization
- **Authentication Method**: JWT tokens
- **Session Management**: Stateless JWT with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Password Policy**: Minimum 8 characters, complexity requirements

### Data Protection
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Encryption at Rest**: AES-256 for sensitive data
- **Data Validation**: Input validation and sanitization
- **SQL Injection Prevention**: Parameterized queries

### Security Headers
- Content Security Policy (CSP)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block

### Audit and Monitoring
- Request/response logging
- Security event monitoring
- Failed authentication tracking
- Regular security assessments
"""
        spec_sections.append(security_section)
        
        # Performance section
        performance_section = """## Performance Requirements

### Response Time Requirements
- **API Endpoints**: < 200ms for 95% of requests
- **Database Queries**: < 100ms for simple queries
- **Page Load Time**: < 2 seconds for initial load

### Scalability Requirements
- **Concurrent Users**: Support 1000+ concurrent users
- **Request Throughput**: 10,000+ requests per minute
- **Data Volume**: Handle 1TB+ of data
- **Horizontal Scaling**: Support auto-scaling

### Resource Requirements
- **Memory**: 2GB minimum, 8GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended
- **Storage**: SSD recommended for database
- **Network**: 100 Mbps minimum bandwidth
"""
        spec_sections.append(performance_section)
        
        # Implementation details
        implementation_section = """## Implementation Guidelines

### Code Standards
- Follow language-specific style guides
- Use consistent naming conventions
- Implement comprehensive error handling
- Write unit tests for all business logic
- Document public APIs and functions

### Database Design
- Use normalized database schema
- Implement proper indexing strategy
- Use migrations for schema changes
- Implement backup and recovery procedures

### API Design
- Follow RESTful API principles
- Use consistent error response format
- Implement proper HTTP status codes
- Version APIs appropriately
- Provide comprehensive API documentation

### Testing Strategy
- **Unit Tests**: 80%+ code coverage
- **Integration Tests**: API endpoint testing
- **End-to-End Tests**: Critical user workflows
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability scanning
"""
        spec_sections.append(implementation_section)
        
        # Deployment section
        deployment_section = """## Deployment Specifications

### Environment Configuration
- **Development**: Local development environment
- **Testing**: Staging environment for testing
- **Production**: High-availability production environment

### Infrastructure Requirements
- **Load Balancer**: Application load balancer with health checks
- **Application Servers**: Auto-scaling group with multiple instances
- **Database**: Managed database service with backup and monitoring
- **Caching**: Redis cluster for caching and sessions

### Monitoring and Logging
- **Application Monitoring**: Performance and error tracking
- **Infrastructure Monitoring**: Server metrics and alerts
- **Log Aggregation**: Centralized logging solution
- **Alerting**: Automated alerts for critical issues

### Backup and Recovery
- **Database Backups**: Daily automated backups with retention
- **Application Backups**: Code and configuration backups
- **Disaster Recovery**: Recovery procedures and testing
- **Data Recovery**: Point-in-time recovery capabilities
"""
        spec_sections.append(deployment_section)
        
        full_content = "\n".join(spec_sections)
        
        return GeneratedDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.TECHNICAL_SPECIFICATION,
            format=DocumentFormat.MARKDOWN,
            title=f"{project_name} Technical Specification",
            content=full_content,
            completeness_score=0.95,
            accuracy_score=0.85,
            readability_score=0.8,
            coverage_score=0.9,
            word_count=len(full_content.split()),
            character_count=len(full_content),
            source_analysis=analysis_data,
            source_architecture=architecture_data,
            source_stack=stack_data,
            template_used="technical_specification"
        )
    
    async def generate_erd(self,
                          analysis_data: Optional[Dict[str, Any]],
                          architecture_data: Optional[Dict[str, Any]],
                          stack_data: Optional[Dict[str, Any]]) -> GeneratedDocument:
        """Generate Entity Relationship Diagram in Mermaid format"""
        
        entities = analysis_data.get("entities", []) if analysis_data else []
        
        # Create ERD in Mermaid format
        erd_content = "erDiagram\n"
        
        # Add entities with basic attributes
        for entity in entities:
            entity_name = entity.replace(" ", "_").upper()
            erd_content += f"    {entity_name} {{\n"
            erd_content += f"        UUID id PK\n"
            erd_content += f"        VARCHAR name\n"
            erd_content += f"        TIMESTAMP created_at\n"
            erd_content += f"        TIMESTAMP updated_at\n"
            erd_content += f"    }}\n\n"
        
        # Add relationships (simplified)
        if len(entities) > 1:
            for i, entity1 in enumerate(entities[:-1]):
                for entity2 in entities[i+1:]:
                    entity1_name = entity1.replace(" ", "_").upper()
                    entity2_name = entity2.replace(" ", "_").upper()
                    # Add a potential relationship
                    erd_content += f"    {entity1_name} ||--o{{ {entity2_name} : \"relates to\"\n"
        
        return GeneratedDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.ERD,
            format=DocumentFormat.MERMAID,
            title="Entity Relationship Diagram",
            content=erd_content,
            completeness_score=0.8,
            accuracy_score=0.7,
            readability_score=0.9,
            coverage_score=0.8,
            word_count=len(erd_content.split()),
            character_count=len(erd_content),
            source_analysis=analysis_data,
            source_architecture=architecture_data,
            source_stack=stack_data,
            template_used="mermaid_erd"
        )
    
    async def generate_context_diagram(self,
                                     analysis_data: Optional[Dict[str, Any]],
                                     architecture_data: Optional[Dict[str, Any]],
                                     stack_data: Optional[Dict[str, Any]]) -> GeneratedDocument:
        """Generate system context diagram in Mermaid format"""
        
        project_name = self._extract_project_name(analysis_data)
        use_cases = analysis_data.get("use_cases", []) if analysis_data else []
        
        # Create context diagram
        context_content = "flowchart TB\n"
        context_content += f"    System[{project_name}]\n"
        context_content += f"    User[User/Client]\n"
        context_content += f"    Database[(Database)]\n"
        context_content += f"    ExtAPI[External APIs]\n\n"
        
        # Add relationships
        context_content += f"    User --> System\n"
        context_content += f"    System --> Database\n"
        context_content += f"    System --> ExtAPI\n"
        context_content += f"    System --> User\n"
        
        # Add use case annotations
        if use_cases:
            context_content += f"\n    %% Use Cases:\n"
            for use_case in use_cases[:5]:  # Limit to first 5
                context_content += f"    %% - {use_case}\n"
        
        return GeneratedDocument(
            document_id=str(uuid.uuid4()),
            document_type=DocumentType.CONTEXT_DIAGRAM,
            format=DocumentFormat.MERMAID,
            title="System Context Diagram",
            content=context_content,
            completeness_score=0.8,
            accuracy_score=0.85,
            readability_score=0.9,
            coverage_score=0.75,
            word_count=len(context_content.split()),
            character_count=len(context_content),
            source_analysis=analysis_data,
            source_architecture=architecture_data,
            source_stack=stack_data,
            template_used="mermaid_context"
        )
    
    # Helper methods
    def _extract_project_name(self, analysis_data: Optional[Dict[str, Any]]) -> str:
        """Extract project name from analysis data"""
        if not analysis_data:
            return "Project"
        
        entities = analysis_data.get("entities", [])
        if entities:
            # Try to find a main entity that could be the project name
            main_entities = [e for e in entities if any(keyword in e.lower() for keyword in ["system", "app", "platform", "service"])]
            if main_entities:
                return main_entities[0]
            return entities[0]
        
        return "Project"
    
    def _extract_tech_stack(self, stack_data: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract organized technology stack from stack data"""
        if not stack_data:
            return {}
        
        # Default categories
        categories = {
            "backend": [],
            "frontend": [],
            "database": [],
            "infrastructure": [],
            "tools": []
        }
        
        # Extract from stack data (assuming it's structured)
        if isinstance(stack_data, dict):
            for key, value in stack_data.items():
                if isinstance(value, list):
                    if key.lower() in categories:
                        categories[key.lower()] = value
                    elif key.lower() in ["db", "data"]:
                        categories["database"] = value
                    elif key.lower() in ["infra", "deploy"]:
                        categories["infrastructure"] = value
                    else:
                        categories["tools"].extend(value if isinstance(value, list) else [value])
                elif isinstance(value, str):
                    # Categorize based on technology type
                    tech = value.lower()
                    if any(t in tech for t in ["python", "fastapi", "django", "flask", "node", "express"]):
                        categories["backend"].append(value)
                    elif any(t in tech for t in ["react", "vue", "angular", "javascript", "typescript"]):
                        categories["frontend"].append(value)
                    elif any(t in tech for t in ["postgresql", "mysql", "mongodb", "sqlite", "redis"]):
                        categories["database"].append(value)
                    elif any(t in tech for t in ["docker", "kubernetes", "aws", "gcp", "azure"]):
                        categories["infrastructure"].append(value)
                    else:
                        categories["tools"].append(value)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _extract_architecture_summary(self, architecture_data: Optional[Dict[str, Any]]) -> str:
        """Extract architecture summary from architecture data"""
        if not architecture_data:
            return "The system follows a modern, scalable architecture pattern."
        
        # Try to extract key architecture information
        summary_parts = []
        
        if "patterns" in architecture_data:
            patterns = architecture_data["patterns"]
            if patterns and isinstance(patterns, list):
                main_pattern = patterns[0].get("name", "unknown pattern") if isinstance(patterns[0], dict) else str(patterns[0])
                summary_parts.append(f"The system implements a {main_pattern} architecture")
        
        if "layers" in architecture_data or "tiers" in architecture_data:
            summary_parts.append("with clearly defined layers for separation of concerns")
        
        if "scalability" in str(architecture_data).lower():
            summary_parts.append("designed for scalability and high availability")
        
        if summary_parts:
            return ". ".join(summary_parts) + "."
        else:
            return "The system follows a modern, scalable architecture pattern designed for maintainability and performance."
    
    def _generate_project_description(self, entities: List[str], use_cases: List[str]) -> str:
        """Generate project description from entities and use cases"""
        if not entities and not use_cases:
            return "A modern application built with best practices and scalable architecture."
        
        if entities:
            main_entity = entities[0]
            description = f"A comprehensive system for managing {main_entity.lower()}"
            
            if use_cases:
                # Add primary functionality
                primary_functions = use_cases[:3]
                if len(primary_functions) == 1:
                    description += f" that enables {primary_functions[0].lower()}"
                elif len(primary_functions) == 2:
                    description += f" that enables {primary_functions[0].lower()} and {primary_functions[1].lower()}"
                else:
                    description += f" that enables {', '.join(uc.lower() for uc in primary_functions[:-1])}, and {primary_functions[-1].lower()}"
            
            description += ". Built with modern technologies for performance, scalability, and maintainability."
        else:
            # Use cases only
            description = f"An application that provides {use_cases[0].lower()}"
            if len(use_cases) > 1:
                description += f" and {len(use_cases)-1} other key functionalities"
            description += ". Designed with user experience and performance in mind."
        
        return description
    
    def _generate_installation_section(self, tech_stack: Dict[str, List[str]]) -> str:
        """Generate installation section based on tech stack"""
        install_section = "## Installation\n\n"
        
        # Check for main technologies
        has_python = any("python" in str(tech).lower() for tech in tech_stack.get("backend", []))
        has_node = any("node" in str(tech).lower() for tech in tech_stack.get("frontend", []))
        has_docker = any("docker" in str(tech).lower() for tech in tech_stack.get("infrastructure", []))
        
        # Prerequisites
        install_section += "### Prerequisites\n\n"
        if has_python:
            install_section += "- Python 3.8 or higher\n"
            install_section += "- pip (Python package manager)\n"
        if has_node:
            install_section += "- Node.js 16 or higher\n"
            install_section += "- npm or yarn\n"
        if has_docker:
            install_section += "- Docker and Docker Compose\n"
        install_section += "- Git\n\n"
        
        # Installation steps
        install_section += "### Quick Start\n\n"
        install_section += "1. Clone the repository:\n"
        install_section += "```bash\n"
        install_section += "git clone <repository-url>\n"
        install_section += "cd <project-directory>\n"
        install_section += "```\n\n"
        
        if has_docker:
            install_section += "2. Using Docker (Recommended):\n"
            install_section += "```bash\n"
            install_section += "docker-compose up --build\n"
            install_section += "```\n\n"
            install_section += "3. Manual Installation:\n"
        else:
            install_section += "2. Install dependencies:\n"
        
        if has_python:
            install_section += "```bash\n"
            install_section += "pip install -r requirements.txt\n"
            install_section += "```\n\n"
        
        if has_node:
            install_section += "```bash\n"
            install_section += "npm install\n"
            install_section += "```\n\n"
        
        install_section += "4. Configure environment:\n"
        install_section += "```bash\n"
        install_section += "cp .env.example .env\n"
        install_section += "# Edit .env with your configuration\n"
        install_section += "```\n\n"
        
        install_section += "5. Run the application:\n"
        install_section += "```bash\n"
        if has_python:
            install_section += "python -m uvicorn app.main:app --reload\n"
        elif has_node:
            install_section += "npm start\n"
        else:
            install_section += "# See specific instructions in documentation\n"
        install_section += "```\n\n"
        
        install_section += "The application will be available at `http://localhost:8000`\n"
        
        return install_section
    
    def _generate_usage_section(self, use_cases: List[str]) -> str:
        """Generate usage section based on use cases"""
        usage_section = "## Usage\n\n"
        
        if not use_cases:
            usage_section += "Detailed usage instructions will be provided in the user documentation.\n"
            return usage_section
        
        usage_section += "### Main Features\n\n"
        for i, use_case in enumerate(use_cases[:5], 1):  # Limit to 5 main features
            usage_section += f"{i}. **{use_case}**: Detailed instructions available in the user guide.\n"
        
        usage_section += "\n### Quick Start Guide\n\n"
        usage_section += "1. **Access the application**: Navigate to the application URL\n"
        usage_section += "2. **Authentication**: Log in with your credentials\n"
        usage_section += "3. **Explore features**: Use the navigation menu to access different functions\n"
        usage_section += "4. **Get help**: Click the help icon for detailed instructions\n\n"
        
        usage_section += "### API Usage\n\n"
        usage_section += "For programmatic access, refer to the API documentation at `/docs`\n\n"
        
        return usage_section
    
    def _has_api_components(self, entities: List[str], use_cases: List[str]) -> bool:
        """Check if the system has API components"""
        all_text = " ".join(entities + use_cases).lower()
        api_indicators = ["api", "endpoint", "rest", "service", "web service", "integration"]
        return any(indicator in all_text for indicator in api_indicators)