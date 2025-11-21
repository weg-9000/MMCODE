# MMCODE Agent Testing Preparation Guide

## Overview

This document provides comprehensive test preparation for the MMCODE (DevStrategist AI) multi-agent system, including test scenarios, sample data, expected responses, and data flow verification for all agents.

**Test Environment**: Local development with A2A communication testing and Playwright end-to-end validation.

---

## System Architecture Test Overview

### Agent Workflow Test Chain
```
User Input → RequirementAnalyzer → [Architect, StackRecommender, Document] → Response
     ↓              ↓                           ↓                            ↓
 Frontend API → Analysis Engine → A2A Orchestration → Artifact Generation → UI Display
```

### Test Coverage Areas
1. **Unit Testing**: Individual agent capabilities and engines
2. **Integration Testing**: A2A communication between agents
3. **End-to-End Testing**: Complete workflow from frontend to backend
4. **Performance Testing**: Agent response times and throughput
5. **Quality Testing**: Artifact quality scores and validation

---

## Test Environment Prerequisites

### Infrastructure Requirements
```yaml
Test Environment Setup:
  Backend Services:
    - FastAPI server (port 8000) - RequirementAnalyzer
    - Agent servers (ports 8001-8003) - Individual agents
  Database:
    - PostgreSQL test database
    - Redis test instance for caching
  External Services:
    - OpenAI API key for testing (with rate limits)
    - Mock LLM responses for consistent testing
```

### Test Data Preparation
```yaml
Required Test Assets:
  - Sample requirement specifications (5 complexity levels)
  - Expected architecture patterns by complexity
  - Sample technology stack recommendations
  - Reference documentation templates
  - Quality threshold configurations
```

### Mock Services Setup
```python
# Mock LLM responses for predictable testing
MOCK_RESPONSES = {
    "requirement_analysis": "structured_analysis_response.json",
    "architecture_design": "architecture_patterns_response.json", 
    "stack_recommendation": "technology_stack_response.json",
    "documentation": "document_templates_response.json"
}
```

---

## Agent Test Scenarios

### 1. RequirementAnalyzer (Orchestrator) Tests

#### Test Scenario 1.1: Basic Requirements Analysis
**Input**:
```json
{
    "requirements": "Build a real-time chat application with user authentication, file sharing, and mobile support. The system should handle 10,000 concurrent users.",
    "session_id": "test-session-001"
}
```

**Expected Analysis Output**:
```json
{
    "entities": [
        "User", "Chat Room", "Message", "File", "Authentication Token"
    ],
    "use_cases": [
        "User registration and authentication",
        "Create and join chat rooms", 
        "Send and receive real-time messages",
        "Upload and share files",
        "Mobile client synchronization"
    ],
    "technical_constraints": {
        "concurrent_users": 10000,
        "real_time": true,
        "mobile_support": true,
        "file_sharing": true
    },
    "complexity_score": 0.75,
    "domain": "communication",
    "scalability_requirements": "high"
}
```

**Expected Orchestration Plan**:
```json
{
    "plan_id": "test-plan-001",
    "sequence": [
        {
            "agent": "architect",
            "task_type": "architecture_design",
            "priority": 1,
            "dependencies": []
        },
        {
            "agent": "stack_recommender", 
            "task_type": "stack_recommendation",
            "priority": 2,
            "dependencies": ["architect"]
        },
        {
            "agent": "documenter",
            "task_type": "document_generation", 
            "priority": 3,
            "dependencies": ["architect", "stack_recommender"]
        }
    ],
    "estimated_duration": 300,
    "parallel_execution": ["stack_recommender", "documenter"]
}
```

#### Test Scenario 1.2: Complex Enterprise System
**Input**:
```json
{
    "requirements": "Develop a microservices-based e-commerce platform with AI recommendations, real-time inventory management, multi-tenant architecture, and compliance with GDPR. Support 100,000+ concurrent users with global deployment.",
    "session_id": "test-session-002"
}
```

**Expected Analysis Characteristics**:
- `complexity_score`: > 0.8
- `scalability_requirements`: "enterprise" 
- `compliance_requirements`: ["GDPR"]
- `architecture_suggestions`: ["microservices", "event_driven"]

### 2. ArchitectAgent Tests

#### Test Scenario 2.1: Microservices Architecture Design
**Input Context**:
```json
{
    "analysis": {
        "entities": ["User", "Product", "Order", "Payment", "Inventory"],
        "complexity_score": 0.8,
        "scalability_requirements": "high",
        "domain": "e-commerce"
    }
}
```

**Expected Architecture Output**:
```json
{
    "architecture": {
        "design_id": "arch-001",
        "name": "E-commerce Microservices Architecture",
        "primary_pattern": "microservices",
        "secondary_patterns": ["event_driven", "cqrs"],
        "presentation_tier": "React/Next.js with API Gateway",
        "business_tier": "Microservices with Service Mesh",
        "data_tier": "Polyglot Persistence (PostgreSQL + MongoDB + Redis)",
        "scalability_tier": "large",
        "complexity_level": 0.8
    },
    "patterns": [
        {
            "name": "Microservices Architecture",
            "pattern_type": "microservices",
            "confidence_score": 0.9,
            "benefits": ["Independent scaling", "Technology diversity", "Fault isolation"],
            "trade_offs": ["Increased complexity", "Network latency", "Data consistency challenges"],
            "implementation_complexity": 0.8
        }
    ],
    "components": [
        {
            "name": "UserService",
            "component_type": "business_logic",
            "responsibilities": ["User management", "Authentication", "Profile management"],
            "interfaces": ["IUserService", "UserAPI"],
            "dependencies": ["UserRepository", "AuthService"],
            "technologies": ["FastAPI", "JWT", "PostgreSQL"]
        },
        {
            "name": "ProductCatalogService", 
            "component_type": "business_logic",
            "responsibilities": ["Product management", "Catalog search", "Inventory tracking"],
            "interfaces": ["IProductService", "ProductAPI"],
            "dependencies": ["ProductRepository", "SearchEngine"],
            "technologies": ["FastAPI", "Elasticsearch", "MongoDB"]
        }
    ],
    "diagrams": {
        "system_architecture": "mermaid_system_diagram",
        "component_relations": "mermaid_component_diagram", 
        "data_flow": "mermaid_dataflow_diagram"
    },
    "quality_score": 0.85
}
```

#### Test Scenario 2.2: Pattern Recommendation for Simple System
**Input Context**:
```json
{
    "analysis": {
        "entities": ["User", "Task", "Project"],
        "complexity_score": 0.3,
        "scalability_requirements": "small",
        "domain": "productivity"
    }
}
```

**Expected Pattern Recommendations**:
- Primary: "layered" or "monolithic"
- Complexity alignment: Low implementation complexity
- Scalability match: Small to medium scale patterns

### 3. StackRecommender Tests

#### Test Scenario 3.1: High-Scale Web Application Stack
**Input Context**:
```json
{
    "architecture": {
        "primary_pattern": "microservices",
        "scalability_tier": "large",
        "complexity_level": 0.8,
        "domain": "e-commerce"
    },
    "requirements": {
        "real_time": true,
        "concurrent_users": 100000,
        "global_deployment": true
    },
    "constraints": {
        "budget": "enterprise",
        "team_expertise": ["Python", "JavaScript", "Docker"]
    }
}
```

**Expected Stack Recommendation**:
```json
{
    "recommendation": {
        "frontend": {
            "framework": "Next.js",
            "state_management": "Redux Toolkit",
            "ui_library": "Material-UI",
            "mobile": "React Native",
            "rationale": "Scalable React ecosystem with SSR support"
        },
        "backend": {
            "api_framework": "FastAPI",
            "async_framework": "asyncio", 
            "message_broker": "Apache Kafka",
            "api_gateway": "Kong",
            "rationale": "High-performance async Python with event streaming"
        },
        "database": {
            "primary": "PostgreSQL",
            "cache": "Redis",
            "search": "Elasticsearch",
            "rationale": "ACID compliance with performance optimization"
        },
        "infrastructure": {
            "containerization": "Docker",
            "orchestration": "Kubernetes",
            "cloud_provider": "AWS/Azure/GCP",
            "cdn": "CloudFlare",
            "rationale": "Enterprise-scale container orchestration"
        },
        "devops": {
            "ci_cd": "GitHub Actions",
            "monitoring": "Prometheus + Grafana",
            "logging": "ELK Stack",
            "security": "OAuth2 + JWT",
            "rationale": "Complete DevOps automation pipeline"
        }
    },
    "quality_assessment": {
        "overall_score": 0.88,
        "suitability": 0.9,
        "completeness": 0.85,
        "feasibility": 0.9,
        "performance_rating": "excellent",
        "scalability_rating": "excellent",
        "complexity_rating": "high"
    },
    "implementation_guidance": {
        "phase_1": ["Setup core API services", "Database design", "Authentication"],
        "phase_2": ["Message broker integration", "Service mesh", "Monitoring"],
        "phase_3": ["Performance optimization", "Global deployment", "Analytics"],
        "estimated_timeline": "6-9 months",
        "team_requirements": "8-12 developers"
    }
}
```

#### Test Scenario 3.2: Simple CRUD Application Stack
**Input Context**:
```json
{
    "architecture": {
        "primary_pattern": "layered", 
        "scalability_tier": "small",
        "complexity_level": 0.3,
        "domain": "business_app"
    }
}
```

**Expected Stack Characteristics**:
- Simple, proven technologies
- Lower operational complexity
- Cost-effective solutions
- Faster development cycle

### 4. DocumentAgent Tests

#### Test Scenario 4.1: Comprehensive Documentation Suite
**Input Context**:
```json
{
    "analysis": "e-commerce system analysis",
    "architecture": "microservices architecture design",
    "stack": "technology stack recommendation"
}
```

**Expected Documentation Output**:
```json
{
    "documentation_suite": {
        "suite_id": "docs-001",
        "name": "E-commerce Platform Documentation",
        "documents": [
            {
                "document_type": "readme",
                "format": "markdown",
                "content": "# E-commerce Platform\n\nA microservices-based...",
                "quality_score": 0.85
            },
            {
                "document_type": "openapi",
                "format": "json", 
                "content": {"openapi": "3.0.0", "info": {...}},
                "quality_score": 0.9
            },
            {
                "document_type": "erd",
                "format": "mermaid",
                "content": "erDiagram\n    User ||--o{ Order : places",
                "quality_score": 0.8
            },
            {
                "document_type": "deployment_guide",
                "format": "markdown",
                "content": "# Deployment Guide\n\n## Prerequisites...",
                "quality_score": 0.85
            }
        ],
        "suite_quality_score": 0.875
    }
}
```

#### Test Scenario 4.2: API-Only Documentation
**Input Context**:
```json
{
    "analysis": {"api_endpoints": [...], "entities": [...]},
    "architecture": {"api_focused": true},
    "stack": {"api_technology": "FastAPI"}
}
```

**Expected Focus**: OpenAPI specification with detailed endpoint documentation

---

## A2A Communication Test Flows

### Complete Workflow Data Flow Test

#### Test Flow 1: End-to-End Success Scenario
```mermaid
sequenceDiagram
    participant U as User/Frontend
    participant R as RequirementAnalyzer
    participant A as ArchitectAgent
    participant S as StackRecommender  
    participant D as DocumentAgent

    U->>R: POST /api/v1/sessions {requirements}
    R->>R: analyze_requirements()
    R->>A: POST /a2a/tasks {task_type: architecture_design}
    A->>A: handle_architecture_design()
    A->>R: Return Artifact{architecture_design}
    R->>S: POST /a2a/tasks {task_type: stack_recommendation}
    S->>S: handle_stack_recommendation()
    S->>R: Return Artifact{stack_recommendation}
    R->>D: POST /a2a/tasks {task_type: document_generation}
    D->>D: handle_document_generation()
    D->>R: Return Artifact{documentation_suite}
    R->>U: Complete orchestration result
```

#### Test Flow 2: Error Handling Scenario
```mermaid
sequenceDiagram
    participant R as RequirementAnalyzer
    participant A as ArchitectAgent
    participant S as StackRecommender

    R->>A: POST /a2a/tasks {architecture_design}
    A->>A: Processing fails (LLM timeout)
    A->>R: Error Response {agent_error, retry_suggestion}
    R->>S: POST /a2a/tasks {stack_recommendation} (with fallback data)
    S->>S: handle_stack_recommendation()
    S->>R: Return Artifact{limited_recommendation}
    R->>R: Compile partial results with error context
```

### A2A Task Communication Tests

#### Task Creation Test
**Endpoint**: `POST /a2a/tasks`
**Sample Request**:
```json
{
    "task_type": "architecture_design",
    "context": {
        "analysis": {...},
        "session_id": "test-session-001"
    },
    "correlation_id": "corr-001"
}
```

**Expected Response**:
```json
{
    "task_id": "task-12345",
    "status": "in_progress",
    "artifact": {
        "artifact_type": "architecture_design",
        "content": {...},
        "quality_score": 0.85,
        "metadata": {...}
    }
}
```

#### Task Status Monitoring Test
**Endpoint**: `GET /a2a/tasks/{task_id}`
**Expected Status Progression**:
1. "submitted" → "in_progress" → "completed"
2. Progress tracking with meaningful step descriptions
3. Error states with recovery suggestions

---

## End-to-End Test Scenarios (Playwright)

### E2E Test 1: Complete User Journey
```javascript
test('Complete requirement analysis workflow', async ({ page }) => {
    // 1. Navigate to homepage
    await page.goto('http://localhost:3000');
    
    // 2. Enter requirements
    await page.fill('[data-testid="requirements-input"]', 
        'Build a real-time chat application with 10,000 concurrent users'
    );
    
    // 3. Start analysis
    await page.click('[data-testid="start-analysis-button"]');
    
    // 4. Wait for session creation and redirect
    await page.waitForURL(/\/session\/[a-z0-9-]+/);
    
    // 5. Monitor real-time progress
    await page.waitForSelector('[data-testid="analysis-progress"]');
    await page.waitForSelector('[data-testid="architecture-progress"]');
    await page.waitForSelector('[data-testid="stack-progress"]');
    await page.waitForSelector('[data-testid="documentation-progress"]');
    
    // 6. Verify completion
    await page.waitForSelector('[data-testid="results-ready"]', { timeout: 300000 });
    
    // 7. Validate results structure
    const architectureResult = await page.locator('[data-testid="architecture-result"]');
    await expect(architectureResult).toBeVisible();
    
    const stackResult = await page.locator('[data-testid="stack-result"]');
    await expect(stackResult).toBeVisible();
    
    const documentationResult = await page.locator('[data-testid="documentation-result"]');
    await expect(documentationResult).toBeVisible();
});
```

### E2E Test 2: Error Recovery Flow
```javascript
test('System error recovery', async ({ page }) => {
    // Mock agent failure
    await page.route('**/api/v1/agents/analyze', route => {
        route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({
                error: {
                    code: "AGENT_COMMUNICATION_ERROR",
                    message: "Architect agent temporarily unavailable"
                }
            })
        });
    });
    
    // Perform analysis and verify error handling
    await page.goto('http://localhost:3000');
    await page.fill('[data-testid="requirements-input"]', 'Test requirements');
    await page.click('[data-testid="start-analysis-button"]');
    
    // Verify error display
    await page.waitForSelector('[data-testid="error-message"]');
    const errorMessage = await page.textContent('[data-testid="error-message"]');
    expect(errorMessage).toContain('temporarily unavailable');
    
    // Verify retry option
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
});
```

---

## Performance Test Scenarios

### Load Testing Parameters
```yaml
Performance Targets:
  Single Agent Response: < 30 seconds
  Complete Workflow: < 5 minutes  
  Concurrent Sessions: 10 simultaneous
  Memory Usage: < 2GB per agent
  CPU Usage: < 80% sustained

Load Test Scenarios:
  1. Single user, complex requirements
  2. 5 concurrent users, medium requirements
  3. 10 concurrent users, simple requirements
  4. Stress test: 20+ concurrent users
```

### Response Time Monitoring
```python
# Performance test markers
PERFORMANCE_THRESHOLDS = {
    "requirement_analysis": 15,  # seconds
    "architecture_design": 45,
    "stack_recommendation": 30, 
    "document_generation": 60,
    "complete_workflow": 300
}
```

---

## Test Data Sets

### Sample Requirements by Complexity

#### Simple (Complexity: 0.1-0.3)
```
"Create a personal task management application with user authentication and task CRUD operations."
```

#### Medium (Complexity: 0.4-0.6)  
```
"Build a real-time collaborative document editor with user management, version control, and file sharing capabilities for teams of up to 100 users."
```

#### Complex (Complexity: 0.7-0.8)
```
"Develop a microservices-based e-commerce platform with AI recommendations, real-time inventory, payment processing, and multi-vendor support for 50,000+ concurrent users."
```

#### Enterprise (Complexity: 0.9+)
```
"Create a global financial trading platform with real-time market data, algorithmic trading, risk management, regulatory compliance (MiFID II, GDPR), multi-currency support, and 99.99% uptime for institutional clients."
```

### Expected Quality Score Ranges

| Complexity | Architecture | Stack | Documentation |
|------------|-------------|--------|---------------|
| Simple     | 0.7-0.8    | 0.8-0.9| 0.8-0.9      |
| Medium     | 0.75-0.85  | 0.8-0.9| 0.8-0.9      |
| Complex    | 0.8-0.9    | 0.85-0.95| 0.85-0.9   |
| Enterprise | 0.85-0.95  | 0.9-0.95| 0.9-0.95    |

---

## Test Environment Setup

### Backend Test Services
```bash
# Start test environment
cd backend

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Setup test database
export DATABASE_URL="postgresql://test:test@localhost:5432/mmcode_test"
export REDIS_URL="redis://localhost:6379/1"

# Run database migrations
alembic upgrade head

# Start individual agent servers for testing
uvicorn app.agents.requirement_analyzer.main:app --port 8000 --reload &
uvicorn app.agents.architect_agent.main:app --port 8001 --reload &
uvicorn app.agents.stack_recommender.main:app --port 8002 --reload &  
uvicorn app.agents.document_agent.main:app --port 8003 --reload &
```

### Frontend Test Environment
```bash
cd frontend

# Install dependencies
npm install
npm install @playwright/test

# Setup environment
cp .env.example .env.test

# Start development server
npm run dev &

# Install Playwright browsers
npx playwright install
```

### Test Execution Commands

#### Unit Tests
```bash
# Backend unit tests
cd backend
pytest tests/unit/ -v --cov=app --cov-report=html

# Agent-specific tests
pytest tests/test_agents.py -v -k "test_requirement_analyzer"
pytest tests/test_agents.py -v -k "test_architect_agent"
```

#### Integration Tests
```bash
# A2A communication tests
pytest tests/integration/test_a2a_communication.py -v

# End-to-end workflow tests  
pytest tests/integration/test_agent_orchestration.py -v
```

#### E2E Tests with Playwright
```bash
# Frontend E2E tests
cd frontend
npx playwright test

# Specific test suites
npx playwright test --grep "workflow"
npx playwright test --grep "error-recovery"

# Visual regression tests
npx playwright test --update-snapshots
```

#### Performance Tests
```bash
# Load testing with locust
pip install locust
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Memory profiling
pytest tests/performance/test_memory_usage.py -v
```

### Test Coverage Goals
- **Unit Test Coverage**: >80% for all agent modules
- **Integration Test Coverage**: >90% for A2A communication
- **E2E Test Coverage**: >95% for critical user workflows  
- **Performance Test Coverage**: All agents under load

---

## Quality Assurance Checklist

### Pre-Test Validation
- [ ] All agents start successfully on designated ports
- [ ] Database connections established
- [ ] Redis cache accessible
- [ ] OpenAI API key valid with sufficient credits
- [ ] Frontend can communicate with backend APIs

### Test Execution Validation
- [ ] All unit tests pass with >80% coverage
- [ ] A2A communication tests complete successfully
- [ ] End-to-end workflows complete within time thresholds
- [ ] Error scenarios handle gracefully with appropriate messages
- [ ] Performance tests meet response time requirements

### Post-Test Analysis
- [ ] Quality scores meet expected ranges
- [ ] Agent outputs contain required fields and formats
- [ ] Documentation generation includes all expected document types
- [ ] No memory leaks or resource exhaustion
- [ ] Log files contain structured error information without sensitive data

---

This comprehensive test preparation guide ensures thorough validation of all agent behaviors, data flows, and system integration points before production deployment.