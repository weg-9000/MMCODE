# MMCODE

AI-powered development strategy automation and security assessment platform with multi-agent orchestration.

## Project Overview

| Item | Description |
|------|-------------|
| **Project Name** | MMCODE (DevStrategist AI) |
| **Purpose** | AI-driven development strategy automation, requirement analysis, architecture design, and security assessment |
| **Core Technologies** | FastAPI, LangChain, PostgreSQL, Redis, React, TypeScript |

---

## Project Status

### Overall Completion

```
Backend Infrastructure:  ██████████████░  95%
Agent System:            ████████░░░░░░░  65%
Security Platform:       ████████████░░░  85%
Frontend MVP:            ████████████░░░  85%
Service Layer:           ████░░░░░░░░░░░  30%
```

### Backend Status

| Component | Status | Description |
|-----------|--------|-------------|
| **FastAPI Application** | ✅ Complete | REST API with async support |
| **Database Layer** | ✅ Complete | PostgreSQL + Redis with connection pooling |
| **Agent Framework** | ⚠️ 65% | Multi-agent system with A2A protocol |
| **Security Platform** | ✅ 85% | 3-layer validation, audit logging |
| **LLM Integration** | ✅ Complete | Multi-provider support (OpenAI, Claude) |

#### Agent Completion Status

| Agent | Completion | Core Features |
|-------|------------|---------------|
| Requirement Analyzer | 70% | NLP-based requirement analysis, entity extraction |
| Architect Agent | 65% | Architecture design, pattern matching, ADR generation |
| Document Agent | 75% | OpenAPI, ERD, README generation |
| Stack Recommender | 45% | Technology analysis (core logic pending) |
| Threat Analyzer | 75% | Pentesting workflow, scope validation |

### Frontend Status

| Component | Status | Description |
|-----------|--------|-------------|
| **Core Layout** | ✅ Complete | Header, Sidebar, MainContent |
| **Dashboard** | ✅ Complete | Session overview, statistics |
| **Block Visualization** | ✅ Complete | ERD-style block canvas with React Flow |
| **Mind Map View** | ✅ Complete | Hierarchical visualization |
| **Document Viewer** | ✅ Complete | Artifact rendering (JSON, Markdown, Mermaid) |
| **Requirement Input** | ✅ Complete | Text editor with orchestration trigger |
| **Mock Mode** | ✅ Complete | Full testing without backend |

---

## Architecture

### System Architecture

```
MMCODE/
├── backend/                 # Python FastAPI Backend
│   ├── app/
│   │   ├── api/v1/         # REST API Endpoints
│   │   ├── agents/         # Multi-Agent System
│   │   │   ├── shared/     # A2A Communication Layer
│   │   │   ├── requirement_analyzer/
│   │   │   ├── architect_agent/
│   │   │   ├── document_agent/
│   │   │   ├── stack_recommender/
│   │   │   └── threat_analyzer/
│   │   ├── core/           # Config, Dependencies
│   │   ├── db/             # Database Layer
│   │   ├── security/       # Security System
│   │   └── services/       # Service Layer
│   └── tests/              # E2E Tests
│
└── frontend/               # React TypeScript Frontend
    └── src/
        ├── components/     # Reusable UI components
        ├── hooks/          # Custom React hooks
        ├── pages/          # Page components
        ├── services/       # API service layer
        ├── stores/         # Zustand state management
        └── types/          # TypeScript definitions
```

### Agent Pipeline

```
[User Requirements]
       │
       ▼
┌─────────────────────────────────────────────────────┐
│               Orchestration Layer                    │
│              (API /orchestrate/)                     │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│              A2A Communication Layer                 │
│           (Agent-to-Agent Protocol)                  │
└──┬─────────┬─────────┬─────────┬─────────┬─────────┘
   │         │         │         │         │
┌──▼──┐  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐
│Req  │  │Arch │  │Doc  │  │Stack│  │Threat│
│Anlz │  │Agent│  │Agent│  │Rec  │  │Anlzr │
└─────┘  └─────┘  └─────┘  └─────┘  └─────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Enable mock mode for testing (optional)
echo "VITE_MOCK_MODE=true" > .env.local

# Start development server
npm run dev
```

### Mock Mode Testing

For frontend development without backend:

```bash
cd frontend
echo "VITE_MOCK_MODE=true" > .env.local
npm run dev
```

See [Frontend MVP Test Guide](frontend/MVP_TEST_GUIDE.md) for detailed testing instructions.

---

## Tech Stack

### Backend

| Category | Technology |
|----------|------------|
| Framework | FastAPI 0.109.0 |
| Database | PostgreSQL 15 + pgvector |
| Cache | Redis 7 |
| ORM | SQLAlchemy 2.0 (async) |
| AI/LLM | LangChain |
| Validation | Pydantic v2 |

### Frontend

| Category | Technology |
|----------|------------|
| Framework | React 18 |
| Language | TypeScript 5.x |
| Styling | Tailwind CSS |
| State | Zustand |
| Visualization | React Flow, Mermaid |
| HTTP | Axios |

---

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend type checking
cd frontend
npm run typecheck

# Frontend linting
npm run lint
```

### Building for Production

```bash
# Frontend production build
cd frontend
npm run build
```

---

## API Documentation

When the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/orchestration` | Start agent workflow |
| `GET /api/v1/orchestration/{id}/status` | Get workflow status |
| `GET /api/v1/sessions` | List sessions |
| `GET /api/v1/sessions/{id}` | Get session with artifacts |

---

## Project Documentation

- [Frontend Architecture Plan](docs/FRONTEND_ARCHITECTURE_PLAN.md)
- [Frontend MVP Test Guide](frontend/MVP_TEST_GUIDE.md)

---

## License

This project is proprietary and confidential.

---

## Contributing

Please refer to internal contribution guidelines.
