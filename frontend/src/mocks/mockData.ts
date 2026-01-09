/**
 * Mock data for frontend testing without backend
 * Used for MVP validation of agent workflow visualization
 */

import type {
  Session,
  Artifact,
  AnalysisContent,
  ArchitectureContent,
  StackContent,
  DocumentationContent,
  BlockNode,
  MindMapNode,
} from '@/types';
import type { OrchestrationStatus } from '@/services/orchestrationService';

/**
 * Mock session data
 */
export const mockSessions: Session[] = [
  {
    id: 'session-001',
    title: 'E-Commerce Platform',
    description: 'Full-featured online shopping platform with user accounts, product catalog, cart, and checkout',
    requirements_text: `# E-Commerce Platform Requirements

## Overview
Build a modern e-commerce platform that supports:
- User registration and authentication
- Product browsing and search
- Shopping cart and checkout
- Order management
- Admin dashboard

## Functional Requirements
- Users can browse products by category
- Users can add items to cart
- Secure payment processing with Stripe
- Order tracking and history
- Admin can manage products and orders

## Non-Functional Requirements
- Load time under 3 seconds
- Support 10,000 concurrent users
- 99.9% uptime
- GDPR compliant`,
    status: 'completed',
    created_at: '2025-01-03T10:00:00Z',
    updated_at: '2025-01-03T12:30:00Z',
    tasks: [
      { id: 'task-001', task_type: 'requirement_analysis', agent_id: 'requirement_analyzer', status: 'completed', priority: 'high', created_at: '2025-01-03T10:00:00Z' },
      { id: 'task-002', task_type: 'architecture_design', agent_id: 'architect', status: 'completed', priority: 'high', created_at: '2025-01-03T10:30:00Z' },
      { id: 'task-003', task_type: 'stack_recommendation', agent_id: 'stack_recommender', status: 'completed', priority: 'high', created_at: '2025-01-03T11:00:00Z' },
      { id: 'task-004', task_type: 'documentation', agent_id: 'document_generator', status: 'completed', priority: 'high', created_at: '2025-01-03T11:30:00Z' },
    ],
    artifacts: [
      { id: 'artifact-001', artifact_type: 'analysis_result', title: 'Requirement Analysis', created_at: '2025-01-03T10:30:00Z', is_final: true },
      { id: 'artifact-002', artifact_type: 'architecture_design', title: 'System Architecture', created_at: '2025-01-03T11:00:00Z', is_final: true },
      { id: 'artifact-003', artifact_type: 'stack_recommendation', title: 'Technology Stack', created_at: '2025-01-03T11:30:00Z', is_final: true },
      { id: 'artifact-004', artifact_type: 'documentation_suite', title: 'Project Documentation', created_at: '2025-01-03T12:00:00Z', is_final: true },
    ],
  },
  {
    id: 'session-002',
    title: 'Task Management App',
    description: 'Project management tool with tasks, teams, and progress tracking',
    status: 'active',
    created_at: '2025-01-04T09:00:00Z',
    updated_at: '2025-01-04T09:30:00Z',
    tasks: [
      { id: 'task-005', task_type: 'requirement_analysis', agent_id: 'requirement_analyzer', status: 'completed', priority: 'high', created_at: '2025-01-04T09:00:00Z' },
      { id: 'task-006', task_type: 'architecture_design', agent_id: 'architect', status: 'processing', priority: 'high', created_at: '2025-01-04T09:30:00Z' },
    ],
    artifacts: [
      { id: 'artifact-005', artifact_type: 'analysis_result', title: 'Requirement Analysis', created_at: '2025-01-04T09:30:00Z', is_final: true },
    ],
  },
];

/**
 * Mock analysis content
 */
export const mockAnalysisContent: AnalysisContent = {
  entities: ['User', 'Product', 'Category', 'Cart', 'CartItem', 'Order', 'OrderItem', 'Payment', 'Review', 'Address'],
  use_cases: [
    'User Registration',
    'User Login/Logout',
    'Browse Products',
    'Search Products',
    'Filter by Category',
    'Add to Cart',
    'Update Cart',
    'Checkout',
    'Process Payment',
    'Track Order',
    'Leave Review',
    'Manage Profile',
  ],
  constraints: [
    'Must support HTTPS only',
    'Payment data must be PCI-DSS compliant',
    'User passwords must be hashed with bcrypt',
    'API rate limiting: 100 requests/minute',
    'Image uploads limited to 5MB',
  ],
  functional_requirements: [
    { id: 'FR-001', title: 'User Authentication', description: 'Users can register, login, and manage their accounts', priority: 'high', category: 'Authentication' },
    { id: 'FR-002', title: 'Product Catalog', description: 'Display products with filtering and search capabilities', priority: 'high', category: 'Product' },
    { id: 'FR-003', title: 'Shopping Cart', description: 'Users can add, update, and remove items from cart', priority: 'high', category: 'Cart' },
    { id: 'FR-004', title: 'Checkout Process', description: 'Secure checkout with payment integration', priority: 'high', category: 'Payment' },
    { id: 'FR-005', title: 'Order Management', description: 'View order history and track shipments', priority: 'medium', category: 'Order' },
  ],
  non_functional_requirements: [
    { id: 'NFR-001', title: 'Performance', description: 'Page load time under 3 seconds', category: 'performance', metric: 'Load Time', target: '< 3s' },
    { id: 'NFR-002', title: 'Scalability', description: 'Support 10,000 concurrent users', category: 'scalability', metric: 'Concurrent Users', target: '10,000' },
    { id: 'NFR-003', title: 'Availability', description: 'System uptime of 99.9%', category: 'reliability', metric: 'Uptime', target: '99.9%' },
    { id: 'NFR-004', title: 'Security', description: 'GDPR and PCI-DSS compliance', category: 'security' },
  ],
  domain_concepts: [
    { name: 'User', description: 'Customer or admin user of the platform', attributes: ['email', 'password', 'name', 'role'], relationships: ['has many Orders', 'has one Cart'] },
    { name: 'Product', description: 'Item available for purchase', attributes: ['name', 'price', 'description', 'stock'], relationships: ['belongs to Category', 'has many Reviews'] },
    { name: 'Order', description: 'Customer purchase transaction', attributes: ['total', 'status', 'shipping_address'], relationships: ['belongs to User', 'has many OrderItems'] },
  ],
  quality_score: 0.92,
  confidence: 0.88,
};

/**
 * Mock architecture content
 */
export const mockArchitectureContent: ArchitectureContent = {
  architecture: {
    name: 'E-Commerce Microservices Architecture',
    description: 'Scalable microservices architecture with API Gateway and event-driven communication',
    architecture_style: 'Microservices with Event-Driven Architecture',
    layers: [
      { name: 'Presentation Layer', description: 'Frontend applications', components: ['React SPA', 'Mobile Apps'], technologies: ['React', 'TypeScript', 'Tailwind CSS'] },
      { name: 'API Gateway', description: 'Entry point for all client requests', components: ['Kong Gateway', 'Rate Limiter', 'Auth Middleware'] },
      { name: 'Service Layer', description: 'Business logic microservices', components: ['User Service', 'Product Service', 'Order Service', 'Payment Service', 'Notification Service'], technologies: ['Python', 'FastAPI'] },
      { name: 'Data Layer', description: 'Data storage and caching', components: ['PostgreSQL', 'Redis Cache', 'S3 Storage'], technologies: ['PostgreSQL', 'Redis', 'AWS S3'] },
      { name: 'Message Layer', description: 'Async communication', components: ['RabbitMQ', 'Event Bus'], technologies: ['RabbitMQ'] },
    ],
    complexity_level: 'high',
    scalability_tier: 'distributed',
    data_tier: 'PostgreSQL with Read Replicas',
  },
  patterns: [
    { name: 'API Gateway', category: 'Integration', description: 'Single entry point for all client requests', context: 'Microservices architecture requiring unified API access', benefits: ['Centralized authentication', 'Rate limiting', 'Request routing'], trade_offs: ['Single point of failure', 'Added latency'] },
    { name: 'CQRS', category: 'Data Management', description: 'Separate read and write operations', context: 'High-read, complex query requirements', benefits: ['Optimized reads', 'Scalable queries'], trade_offs: ['Eventual consistency', 'Increased complexity'] },
    { name: 'Event Sourcing', category: 'Data Management', description: 'Store state changes as events', context: 'Order and payment tracking', benefits: ['Full audit trail', 'Time travel debugging'], trade_offs: ['Storage overhead', 'Query complexity'] },
    { name: 'Circuit Breaker', category: 'Resilience', description: 'Prevent cascade failures', context: 'Inter-service communication', benefits: ['Fault isolation', 'Graceful degradation'], trade_offs: ['Added complexity', 'State management'] },
  ],
  components: [
    { name: 'User Service', type: 'service', description: 'Handles user authentication and profile management', responsibilities: ['User registration', 'Authentication', 'Profile CRUD'], interfaces: ['/api/users', '/api/auth'], dependencies: ['PostgreSQL', 'Redis'], technologies: ['Python', 'FastAPI', 'JWT'] },
    { name: 'Product Service', type: 'service', description: 'Manages product catalog and inventory', responsibilities: ['Product CRUD', 'Inventory tracking', 'Search'], interfaces: ['/api/products', '/api/categories'], dependencies: ['PostgreSQL', 'Elasticsearch'], technologies: ['Python', 'FastAPI'] },
    { name: 'Order Service', type: 'service', description: 'Handles order lifecycle', responsibilities: ['Order creation', 'Status tracking', 'History'], interfaces: ['/api/orders'], dependencies: ['PostgreSQL', 'RabbitMQ'], technologies: ['Python', 'FastAPI'] },
    { name: 'Payment Service', type: 'service', description: 'Processes payments via Stripe', responsibilities: ['Payment processing', 'Refunds', 'Receipts'], interfaces: ['/api/payments'], dependencies: ['Stripe API', 'PostgreSQL'], technologies: ['Python', 'FastAPI', 'Stripe SDK'] },
  ],
  diagrams: {
    'system-context': `graph TB
    User[Customer] --> FE[React Frontend]
    Admin[Admin] --> FE
    FE --> GW[API Gateway]
    GW --> US[User Service]
    GW --> PS[Product Service]
    GW --> OS[Order Service]
    GW --> PAY[Payment Service]`,
    'data-flow': `sequenceDiagram
    User->>+Frontend: Add to Cart
    Frontend->>+API Gateway: POST /cart
    API Gateway->>+Cart Service: Add Item
    Cart Service->>+Product Service: Check Stock
    Product Service-->>-Cart Service: Stock Available
    Cart Service-->>-API Gateway: Item Added
    API Gateway-->>-Frontend: Success
    Frontend-->>-User: Cart Updated`,
  },
  decisions: [
    { id: 'ADR-001', title: 'Use Microservices Architecture', status: 'accepted', context: 'Need for independent scaling and deployment', decision: 'Adopt microservices architecture', rationale: 'Enables team autonomy, independent scaling, and technology flexibility', consequences: 'Increased operational complexity, need for service mesh' },
    { id: 'ADR-002', title: 'PostgreSQL as Primary Database', status: 'accepted', context: 'Need for ACID transactions and complex queries', decision: 'Use PostgreSQL for transactional data', rationale: 'Mature, reliable, excellent JSON support', consequences: 'Vertical scaling limitations, need for read replicas' },
    { id: 'ADR-003', title: 'JWT for Authentication', status: 'accepted', context: 'Stateless authentication for microservices', decision: 'Use JWT tokens for authentication', rationale: 'Stateless, scalable, works well with microservices', consequences: 'Token revocation complexity, storage of refresh tokens' },
  ],
  metadata: {
    design_timestamp: '2025-01-03T11:00:00Z',
    complexity_level: 'high',
    scalability_tier: 'distributed',
    pattern_count: 4,
    component_count: 4,
  },
};

/**
 * Mock stack content
 */
export const mockStackContent: StackContent = {
  recommendation: {
    backend: [
      { name: 'Python', version: '3.11', category: 'Language', description: 'Primary backend language', rationale: 'Excellent for AI/ML integration, fast development', alternatives: ['Node.js', 'Go'], compatibility_score: 0.95 },
      { name: 'FastAPI', version: '0.109', category: 'Framework', description: 'Async web framework', rationale: 'High performance, automatic OpenAPI docs', alternatives: ['Django', 'Flask'], compatibility_score: 0.92 },
      { name: 'SQLAlchemy', version: '2.0', category: 'ORM', description: 'Database ORM', rationale: 'Mature, flexible, async support', alternatives: ['Tortoise ORM'], compatibility_score: 0.90 },
    ],
    frontend: [
      { name: 'React', version: '18.x', category: 'Framework', description: 'UI library', rationale: 'Large ecosystem, component-based', alternatives: ['Vue.js', 'Svelte'], compatibility_score: 0.94 },
      { name: 'TypeScript', version: '5.x', category: 'Language', description: 'Type-safe JavaScript', rationale: 'Better maintainability, IDE support', compatibility_score: 0.96 },
      { name: 'Tailwind CSS', version: '3.x', category: 'Styling', description: 'Utility-first CSS', rationale: 'Rapid development, consistent design', compatibility_score: 0.92 },
    ],
    database: [
      { name: 'PostgreSQL', version: '15', category: 'Primary Database', description: 'ACID-compliant relational database', rationale: 'Reliable, feature-rich, JSON support', alternatives: ['MySQL'], compatibility_score: 0.95 },
      { name: 'Redis', version: '7.x', category: 'Cache', description: 'In-memory data store', rationale: 'Fast caching, session storage', alternatives: ['Memcached'], compatibility_score: 0.93 },
    ],
    infrastructure: [
      { name: 'Docker', version: 'latest', category: 'Containerization', description: 'Container runtime', rationale: 'Consistent environments, easy deployment', compatibility_score: 0.98 },
      { name: 'Kubernetes', version: '1.28', category: 'Orchestration', description: 'Container orchestration', rationale: 'Auto-scaling, self-healing', alternatives: ['Docker Swarm'], compatibility_score: 0.90 },
    ],
    ai_ml: [
      { name: 'LangChain', version: '0.1.x', category: 'AI Framework', description: 'LLM application framework', rationale: 'Easy LLM integration, chain composition', compatibility_score: 0.88 },
      { name: 'OpenAI API', category: 'LLM Provider', description: 'GPT models', rationale: 'Best-in-class language models', alternatives: ['Anthropic Claude'], compatibility_score: 0.92 },
    ],
  },
  quality_assessment: {
    overall_score: 0.91,
    suitability: 0.93,
    completeness: 0.89,
    feasibility: 0.92,
    maintainability: 0.88,
    security: 0.90,
  },
  architecture_context: {
    architecture_style: 'Microservices',
    deployment_target: 'Kubernetes on AWS',
    team_size: '5-10 developers',
  },
  implementation_guidance: {
    rationale: 'Stack optimized for scalable e-commerce with AI capabilities',
    implementation_notes: [
      'Start with monolith, extract microservices gradually',
      'Implement CI/CD pipeline early',
      'Use feature flags for gradual rollouts',
      'Set up monitoring from day one',
    ],
    next_steps: [
      'Set up development environment with Docker Compose',
      'Create initial FastAPI project structure',
      'Set up PostgreSQL with initial schema',
      'Configure CI/CD with GitHub Actions',
    ],
    risks: [
      'Kubernetes learning curve for team',
      'Microservices complexity for small team initially',
    ],
    prerequisites: [
      'Docker and Docker Compose installed',
      'Python 3.11+ installed',
      'Node.js 18+ for frontend development',
    ],
  },
  metadata: {
    analysis_timestamp: '2025-01-03T11:30:00Z',
    agent_version: '1.0.0',
    complexity_assessment: 'High',
    confidence_level: 0.89,
  },
};

/**
 * Mock documentation content
 */
export const mockDocumentationContent: DocumentationContent = {
  documentation_suite: {
    suite_id: 'docs-001',
    name: 'E-Commerce Platform Documentation',
    description: 'Complete documentation suite for the e-commerce platform',
    documents: [
      {
        id: 'doc-001',
        document_type: 'openapi',
        title: 'API Specification',
        format: 'json',
        content: {
          openapi: '3.0.0',
          info: { title: 'E-Commerce API', version: '1.0.0' },
          paths: {
            '/api/products': { get: { summary: 'List products' } },
            '/api/orders': { post: { summary: 'Create order' } },
          },
        },
        quality_score: 0.92,
      },
      {
        id: 'doc-002',
        document_type: 'erd',
        title: 'Entity Relationship Diagram',
        format: 'mermaid',
        content: `erDiagram
    USER ||--o{ ORDER : places
    USER ||--|| CART : has
    ORDER ||--|{ ORDER_ITEM : contains
    PRODUCT ||--o{ ORDER_ITEM : includes
    PRODUCT }o--|| CATEGORY : belongs_to`,
        quality_score: 0.90,
      },
      {
        id: 'doc-003',
        document_type: 'readme',
        title: 'README',
        format: 'markdown',
        content: `# E-Commerce Platform

## Overview
Modern e-commerce platform built with React and FastAPI.

## Quick Start
\`\`\`bash
docker-compose up -d
\`\`\`

## Features
- User authentication
- Product catalog
- Shopping cart
- Order management`,
        quality_score: 0.88,
      },
      {
        id: 'doc-004',
        document_type: 'deployment_guide',
        title: 'Deployment Guide',
        format: 'markdown',
        content: `# Deployment Guide

## Prerequisites
- Kubernetes cluster
- Helm 3.x
- kubectl configured

## Steps
1. Build Docker images
2. Push to container registry
3. Apply Kubernetes manifests
4. Configure ingress`,
        quality_score: 0.85,
      },
    ],
    suite_quality_score: 0.89,
    coverage_matrix: {
      api_documentation: true,
      erd: true,
      readme: true,
      deployment_guide: true,
      technical_spec: true,
    },
  },
  quality_assessment: {
    completeness: 0.92,
    accuracy: 0.88,
    clarity: 0.90,
    consistency: 0.87,
  },
  generation_summary: {
    total_documents: 4,
    document_types: ['openapi', 'erd', 'readme', 'deployment_guide'],
    overall_quality: 0.89,
    coverage_matrix: {
      api_documentation: true,
      erd: true,
      readme: true,
      deployment_guide: true,
    },
    generation_time: '2025-01-03T12:00:00Z',
  },
};

/**
 * Mock artifacts
 */
export const mockArtifacts: Artifact[] = [
  {
    id: 'artifact-001',
    session_id: 'session-001',
    task_id: 'task-001',
    artifact_type: 'analysis_result',
    title: 'Requirement Analysis Result',
    description: 'Comprehensive analysis of project requirements',
    content: mockAnalysisContent,
    content_format: 'json',
    quality_score: 0.92,
    confidence_score: 0.88,
    version: '1.0.0',
    created_by: 'requirement_analyzer',
    created_at: '2025-01-03T10:30:00Z',
    updated_at: '2025-01-03T10:30:00Z',
    is_final: true,
    is_public: false,
  },
  {
    id: 'artifact-002',
    session_id: 'session-001',
    task_id: 'task-002',
    artifact_type: 'architecture_design',
    title: 'System Architecture Design',
    description: 'Microservices architecture with patterns and components',
    content: mockArchitectureContent,
    content_format: 'json',
    quality_score: 0.89,
    confidence_score: 0.85,
    version: '1.0.0',
    created_by: 'architect_agent',
    created_at: '2025-01-03T11:00:00Z',
    updated_at: '2025-01-03T11:00:00Z',
    is_final: true,
    is_public: false,
  },
  {
    id: 'artifact-003',
    session_id: 'session-001',
    task_id: 'task-003',
    artifact_type: 'stack_recommendation',
    title: 'Technology Stack Recommendation',
    description: 'Recommended technologies with quality assessment',
    content: mockStackContent,
    content_format: 'json',
    quality_score: 0.91,
    confidence_score: 0.89,
    version: '1.0.0',
    created_by: 'stack_recommender',
    created_at: '2025-01-03T11:30:00Z',
    updated_at: '2025-01-03T11:30:00Z',
    is_final: true,
    is_public: false,
  },
  {
    id: 'artifact-004',
    session_id: 'session-001',
    task_id: 'task-004',
    artifact_type: 'documentation_suite',
    title: 'Project Documentation Suite',
    description: 'Complete documentation including OpenAPI, ERD, README',
    content: mockDocumentationContent,
    content_format: 'json',
    quality_score: 0.89,
    confidence_score: 0.87,
    version: '1.0.0',
    created_by: 'document_generator',
    created_at: '2025-01-03T12:00:00Z',
    updated_at: '2025-01-03T12:00:00Z',
    is_final: true,
    is_public: false,
  },
];

/**
 * Mock block nodes for visualization
 */
export const mockBlockNodes: BlockNode[] = [
  {
    id: 'block-session',
    type: 'default',
    position: { x: 400, y: 50 },
    data: {
      id: 'block-session',
      type: 'session',
      title: 'E-Commerce Platform',
      status: 'completed',
      techStack: ['React', 'FastAPI', 'PostgreSQL'],
      qualityScore: 0.90,
      taskCount: 4,
      completedTasks: 4,
      artifactCount: 4,
      overallProgress: 100,
    },
  },
  {
    id: 'block-analysis',
    type: 'default',
    position: { x: 100, y: 200 },
    data: {
      id: 'block-analysis',
      type: 'analysis',
      title: 'Requirement Analysis',
      status: 'completed',
      techStack: ['NLP', 'LangChain'],
      qualityScore: 0.92,
      useCases: ['User Registration', 'Browse Products', 'Add to Cart', 'Checkout', 'Track Order'],
      constraints: ['HTTPS only', 'PCI-DSS compliance', 'Rate limiting'],
    },
  },
  {
    id: 'block-architecture',
    type: 'default',
    position: { x: 350, y: 200 },
    data: {
      id: 'block-architecture',
      type: 'architecture',
      title: 'System Architecture',
      status: 'completed',
      techStack: ['Microservices', 'Event-Driven'],
      qualityScore: 0.89,
      patterns: ['API Gateway', 'CQRS', 'Event Sourcing', 'Circuit Breaker'],
      architectureStyle: 'Microservices',
      scalability: 'distributed',
    },
  },
  {
    id: 'block-stack',
    type: 'default',
    position: { x: 600, y: 200 },
    data: {
      id: 'block-stack',
      type: 'stack',
      title: 'Technology Stack',
      status: 'completed',
      techStack: ['Python', 'React', 'PostgreSQL'],
      qualityScore: 0.91,
      suitabilityScore: 0.93,
      feasibilityScore: 0.92,
      backend: ['Python', 'FastAPI', 'SQLAlchemy'],
      frontend: ['React', 'TypeScript', 'Tailwind CSS'],
      database: ['PostgreSQL', 'Redis'],
    },
  },
  {
    id: 'block-docs',
    type: 'default',
    position: { x: 400, y: 350 },
    data: {
      id: 'block-docs',
      type: 'document',
      title: 'Documentation Suite',
      status: 'completed',
      techStack: ['OpenAPI', 'Mermaid', 'Markdown'],
      qualityScore: 0.89,
      documentTypes: ['OpenAPI Spec', 'ERD', 'README', 'Deployment Guide'],
      formats: ['json', 'mermaid', 'markdown'],
      coveragePercentage: 100,
    },
  },
];

/**
 * Mock mind map nodes
 */
export const mockMindMapNodes: MindMapNode[] = [
  {
    id: 'root',
    type: 'session',
    label: 'E-Commerce Platform',
    status: 'completed',
    qualityScore: 0.90,
    techStack: ['React', 'FastAPI', 'PostgreSQL'],
    children: [
      {
        id: 'analysis',
        type: 'analysis',
        label: 'Requirement Analysis',
        status: 'completed',
        qualityScore: 0.92,
        techStack: ['NLP', 'LangChain'],
        children: [
          { id: 'entities', type: 'entity', label: 'Entities (10)', status: 'completed' },
          { id: 'use-cases', type: 'use-case', label: 'Use Cases (12)', status: 'completed' },
          { id: 'constraints', type: 'pattern', label: 'Constraints (5)', status: 'completed' },
        ],
      },
      {
        id: 'architecture',
        type: 'architecture',
        label: 'System Architecture',
        status: 'completed',
        qualityScore: 0.89,
        techStack: ['Microservices', 'Event-Driven'],
        children: [
          { id: 'patterns', type: 'pattern', label: 'Patterns (4)', status: 'completed' },
          { id: 'components', type: 'component', label: 'Components (4)', status: 'completed' },
          { id: 'adrs', type: 'document', label: 'ADRs (3)', status: 'completed' },
        ],
      },
      {
        id: 'stack',
        type: 'stack',
        label: 'Technology Stack',
        status: 'completed',
        qualityScore: 0.91,
        techStack: ['Python', 'React', 'PostgreSQL'],
        children: [
          { id: 'backend', type: 'technology', label: 'Backend (3)', status: 'completed' },
          { id: 'frontend', type: 'technology', label: 'Frontend (3)', status: 'completed' },
          { id: 'infra', type: 'technology', label: 'Infrastructure (2)', status: 'completed' },
        ],
      },
      {
        id: 'docs',
        type: 'document',
        label: 'Documentation',
        status: 'completed',
        qualityScore: 0.89,
        techStack: ['OpenAPI', 'Mermaid'],
        children: [
          { id: 'openapi', type: 'document', label: 'OpenAPI Spec', status: 'completed' },
          { id: 'erd', type: 'document', label: 'ERD Diagram', status: 'completed' },
          { id: 'readme', type: 'document', label: 'README', status: 'completed' },
        ],
      },
    ],
  },
];

/**
 * Mock orchestration status for progress simulation
 */
export function createMockOrchestrationStatus(
  sessionId: string,
  step: number
): OrchestrationStatus {
  const steps = [
    { status: 'in_progress' as const, current_step: 'Analyzing Requirements', progress: 25, tasks_completed: 0 },
    { status: 'in_progress' as const, current_step: 'Designing Architecture', progress: 50, tasks_completed: 1 },
    { status: 'in_progress' as const, current_step: 'Recommending Stack', progress: 75, tasks_completed: 2 },
    { status: 'in_progress' as const, current_step: 'Generating Documentation', progress: 90, tasks_completed: 3 },
    { status: 'completed' as const, current_step: 'Complete', progress: 100, tasks_completed: 4 },
  ];

  const currentStep = steps[Math.min(step, steps.length - 1)];

  return {
    session_id: sessionId,
    status: currentStep.status,
    progress_percentage: currentStep.progress,
    current_step: currentStep.current_step,
    estimated_completion_minutes: step < 4 ? (4 - step) * 2 : 0,
    tasks_completed: currentStep.tasks_completed,
    tasks_total: 4,
    artifacts_generated: currentStep.tasks_completed,
  };
}

/**
 * Check if mock mode is enabled
 */
export function isMockMode(): boolean {
  return import.meta.env.VITE_MOCK_MODE === 'true' ||
         import.meta.env.DEV && !import.meta.env.VITE_API_URL;
}
