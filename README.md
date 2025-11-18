# DevStrategist AI

🤖 **AI-powered development strategy automation platform**

> Transform your project requirements into comprehensive development strategies, tech stack recommendations, and documentation through multi-agent AI analysis.

## 🎯 Project Overview

DevStrategist AI automates the entire development planning process:

**Requirements** → **Multi-Agent Analysis** → **Strategy/Stack/Documentation** → **GitHub Integration**

### Core Features

- 📝 **Requirement Analysis**: Extract entities, use cases, and technical constraints
- 🏗️ **Architecture Design**: Generate system diagrams and component relationships
- 🔧 **Tech Stack Recommendations**: AI-powered framework and library suggestions
- 📚 **Auto Documentation**: OpenAPI specs, ERD diagrams, and project docs
- 🔍 **Vector Search**: pgvector-powered knowledge base for informed decisions
- 🔗 **GitHub Integration**: Direct repository setup and documentation deployment

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.109.0 + Python 3.11
- **Database**: PostgreSQL 15 (Supabase) + pgvector 0.6.0
- **ORM**: SQLAlchemy 2.0 (async)
- **AI/ML**: LangChain 0.1.0 + OpenAI GPT-3.5/4
- **Cache**: Redis 7 (agent state management)
- **Deployment**: Render (Docker)

### Frontend
- **Framework**: React 18 + Vite 5.0
- **State**: React Query 5.0
- **UI**: shadcn/ui + Tailwind CSS
- **Deployment**: GitHub Pages

### AI Agents
- **RequirementAnalyzer**: Extracts structured data from user input
- **ArchitectureAgent**: Designs system architecture and components
- **StackRecommender**: Recommends optimal tech stacks with reasoning
- **DocumentAgent**: Generates comprehensive project documentation

## 📁 Project Structure

```
MMCODE/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── agents/            # AI agents (LangChain)
│   │   ├── api/               # FastAPI routes
│   │   ├── core/              # Configuration & exceptions
│   │   ├── database/          # SQLAlchemy & pgvector
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── utils/             # Utilities
│   │   └── workers/           # Background tasks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                  # React application
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── hooks/             # React hooks
│   │   ├── lib/               # API client
│   │   ├── pages/             # Route components
│   │   └── types/             # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── docs/                      # Project documentation
├── scripts/                   # Deployment scripts
└── Project_plan.md           # Detailed project plan
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector
- Redis 7+
- OpenAI API key

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Environment Variables

```env
# Backend (.env)
SUPABASE_URL=postgresql://...
SUPABASE_KEY=your-supabase-key
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-32-character-secret-key

# Frontend (.env.local)
VITE_API_URL=http://localhost:8000
```

## 📊 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/v1/sessions` - Create new analysis session
- `GET /api/v1/sessions/{id}` - Get session status
- `POST /api/v1/agents/analyze` - Run multi-agent analysis
- `GET /api/v1/sessions/{id}/artifacts` - Get generated artifacts

## 🧪 Development Workflow

### Testing

```bash
# Backend tests
cd backend
pytest --cov=app tests/

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend
black app/
ruff app/
mypy app/

# Frontend
npm run lint
npm run type-check
```

## 🏗️ Architecture

### Multi-Agent System

```
[User Requirements] 
        ↓
[RequirementAnalyzer] → Extract entities, constraints
        ↓
[ArchitectureAgent] → Design system components
        ↓
[StackRecommender] → Suggest optimal tech stack
        ↓
[DocumentAgent] → Generate docs & diagrams
        ↓
[Generated Artifacts]
```

### Database Schema

- **users**: User management
- **sessions**: Analysis sessions
- **artifacts**: Generated content (JSON)
- **knowledge_base**: Vector embeddings for search
- **decision_logs**: Agent decision audit trail

## 📈 Roadmap

### Phase 1: Core Infrastructure (Weeks 1-2)
- ✅ FastAPI setup with PostgreSQL
- ✅ Basic agent implementation
- ✅ React frontend foundation

### Phase 2: Search & Knowledge (Weeks 3-4)
- 🔄 pgvector search pipeline
- 🔄 Automated knowledge collection
- 🔄 Frontend integration

### Phase 3: Multi-Agent System (Weeks 5-6)
- ⏳ 4-agent orchestration
- ⏳ Quality evaluation
- ⏳ Redis state management

### Phase 4: Production (Weeks 7-8)
- ⏳ Security & monitoring
- ⏳ Deployment automation
- ⏳ Performance optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [LangChain](https://python.langchain.com/)
- UI components from [shadcn/ui](https://ui.shadcn.com/)
- Vector search by [pgvector](https://github.com/pgvector/pgvector)

---

**DevStrategist AI** - Transforming project requirements into comprehensive development strategies through AI-powered analysis.