## 1. 프로젝트 개요 및 기술 스택 확정

### 1.1 핵심 목표
**Python 생태계 기반 AI 개발 전략 자동화 플랫폼**  
요구사항 입력 → 멀티에이전트 분석 → 전략/스택/문서 자동 생성 → GitHub 통합

### 1.2 최종 기술 스택
```yaml
# stack.yml
backend:
  framework: FastAPI 0.109.0
  language: Python 3.11
  database:
    - PostgreSQL 15 (Supabase)
    - pgvector 0.6.0 (벡터 검색)
  orm: SQLAlchemy 2.0 (async)
  validation: Pydantic v2
  agent: LangChain 0.1.0 (Python)
  cache: Redis 7 (agent 상태 관리)
  deployment: Render (Docker)
  testing: pytest 8.0
  docs: Swagger/OpenAPI (자동 생성)

frontend:
  framework: React 18 + Vite 5.0
  state: React Query 5.0
  ui: shadcn/ui + Tailwind CSS
  deployment: GitHub Pages
```

---

## 2. 데이터베이스 설계 (SQLAlchemy + pgvector)

### 2.1 Core Models (`app/models.py`)
```python
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sessions = relationship("Session", back_populates="user")

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    requirements = Column(Text, nullable=False)
    status = Column(String, default="draft")  # draft, analyzing, completed, failed
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="sessions")
    artifacts = relationship("Artifact", back_populates="session", cascade="all, delete-orphan")
    decision_logs = relationship("DecisionLog", back_populates="session")

class Artifact(Base):
    __tablename__ = "artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    type = Column(String, nullable=False)  # analysis, architecture, stack, openapi, erd, context
    content = Column(JSONB, nullable=False)  # Pydantic 모델을 JSON으로 저장
    quality_score = Column(JSONB)  # { completeness: 0.9, relevance: 0.8 }
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="artifacts")

class KnowledgeBase(Base):
    """외부 자료 저장 (검색용)"""
    __tablename__ = "knowledge_base"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    embedding = Vector(dim=1536)  # OpenAI text-embedding-3-small
    metadata = Column(JSONB)  # { url: "...", source: "github", license: "MIT" }
    scraped_at = Column(DateTime, default=datetime.utcnow)

class DecisionLog(Base):
    """에이전트 결정 추적 (감사용)"""
    __tablename__ = "decision_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    agent_name = Column(String, nullable=False)
    prompt_hash = Column(String)  # SHA256
    decision = Column(JSONB)  # { choice: "Next.js", reason: "...", alternatives: [...] }
    sources = Column(JSONB)  # [{ url: "...", relevance: 0.85 }]
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="decision_logs")
```

### 2.2 pgvector 검색 함수 (`app/db/vector.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import numpy as np

async def search_knowledge(
    db: AsyncSession,
    query_embedding: list[float],
    match_threshold: float = 0.7,
    match_count: int = 5
) -> list[KnowledgeBase]:
    stmt = text("""
        SELECT 
            id, content, metadata,
            1 - (embedding <=> :embedding) as similarity
        FROM knowledge_base
        WHERE 1 - (embedding <=> :embedding) > :threshold
        ORDER BY embedding <=> :embedding
        LIMIT :limit
    """).bindparams(
        embedding=query_embedding,
        threshold=match_threshold,
        limit=match_count
    )
    
    result = await db.execute(stmt)
    return result.fetchall()
```

---

## 3. FastAPI 프로젝트 구조

### 3.1 디렉토리 구조
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 생성
│   ├── core/                   # 설정, 의존성
│   │   ├── config.py           # Pydantic Settings
│   │   └── dependencies.py     # DB, Redis DI
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── sessions.py     # CRUD 엔드포인트
│   │       └── agents.py       # 에이전트 실행
│   ├── models/                 # SQLAlchemy 모델
│   │   └── models.py
│   ├── schemas/                # Pydantic 스키마
│   │   ├── session.py
│   │   ├── artifact.py
│   │   └── agent.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # BaseAgent 추상 클래스
│   │   ├── analyzer.py         # 요구사항 분석
│   │   ├── architect.py        # 아키텍처 비교
│   │   ├── recommender.py      # 스택 추천
│   │   └── documenter.py       # 문서 생성
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_service.py  # 비즈니스 로직
│   │   ├── search_service.py   # 지식 검색
│   │   └── github_service.py   # GitHub 통합
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py          # DB 세션 관리
│   │   └── vector.py           # pgvector 유틸
│   └── utils/
│       ├── cache.py            # Redis 캐싱
│       ├── llm.py              # LangChain 초기화
│       └── security.py         # PII 마스킹
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest fixture
│   ├── test_sessions.py
│   └── test_agents.py
├── Dockerfile
├── requirements.txt
└── .env.example
```

### 3.2 FastAPI 메인 앱 (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import sessions, agents

app = FastAPI(
    title="DevStrategist AI API",
    version="0.1.0",
    description="AI 기반 개발 전략 자동화 플랫폼"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
```

### 3.3 Pydantic 설정 (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevStrategist AI"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://devstrategist.ai"]
    
    # Database
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # LLM
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # LangChain
    LANGCHAIN_TRACING: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 4. 의존성 주입 (DI) 구현

### 4.1 DB 세션 의존성 (`app/core/dependencies.py`)
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# PostgreSQL + pgvector
engine = create_async_engine(
    settings.SUPABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Redis
import redis.asyncio as redis

async def get_redis():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
```

### 4.2 FastAPI 엔드포인트에서 사용 (`app/api/v1/sessions.py`)
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_redis
from app.services.session_service import SessionService

router = APIRouter()

@router.post("/", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    service = SessionService(db, redis_client)
    session = await service.create_session(request.requirements)
    return session
```

---

## 5. 멀티에이전트 구현 (LangChain Python)

### 5.1 BaseAgent 추상 클래스 (`app/agents/base.py`)
```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from langchain.chat_models import ChatOpenAI
from app.core.config import settings

class AgentInput(BaseModel):
    requirements: str
    context: dict = {}

class AgentOutput(BaseModel):
    output: dict
    sources: list[dict] = []
    token_usage: int = 0

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY
        )
    
    @abstractmethod
    async def run(self, input_data: AgentInput) -> AgentOutput:
        pass
    
    def log_decision(self, decision: dict, sources: list):
        # DecisionLog에 저장 (비동기)
        from app.services.session_service import log_decision
        asyncio.create_task(log_decision(self.name, decision, sources))
```

### 5.2 요구사항 분석 에이전트 (`app/agents/analyzer.py`)
```python
from langchain.prompts import ChatPromptTemplate
from app.agents.base import BaseAgent, AgentInput, AgentOutput

class RequirementAnalyzer(BaseAgent):
    def __init__(self):
        super().__init__("requirement_analyzer")
        
        self.prompt = ChatPromptTemplate.from_template(
            """
            You are a senior requirement analyst. Extract structured data.
            
            Requirements: {requirements}
            
            Output JSON:
            {{
                "entities": ["PascalCase names"],
                "use_cases": ["action-oriented names"],
                "quality_attributes": ["performance", "security"],
                "ambiguous_items": [{{"text": "...", "question": "..."}}]
            }}
            """
        )
        self.chain = self.prompt | self.llm
    
    async def run(self, input_data: AgentInput) -> AgentOutput:
        response = await self.chain.ainvoke({
            "requirements": input_data.requirements
        })
        
        # Pydantic으로 파싱 검증
        from app.schemas.analysis import AnalysisResult
        result = AnalysisResult.model_validate_json(response.content)
        
        # 출처 검색 (예: "Next.js" → knowledge_base 검색)
        sources = await self._search_sources(result.entities)
        
        return AgentOutput(
            output=result.model_dump(),
            sources=sources,
            token_usage=response.response_metadata["token_usage"]["total_tokens"]
        )
    
    async def _search_sources(self, entities: list[str]) -> list[dict]:
        from app.services.search_service import search_by_keywords
        all_sources = []
        for entity in entities[:3]:  # 상위 3개만
            sources = await search_by_keywords(entity, limit=2)
            all_sources.extend(sources)
        return all_sources
```

---

## 6. CRUD 서비스 구현 (SQLAlchemy Async)

### 6.1 세션 서비스 (`app/services/session_service.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.models import Session, Artifact
from app.schemas.session import SessionCreate, SessionResponse
from app.schemas.artifact import ArtifactCreate

class SessionService:
    def __init__(self, db: AsyncSession, redis):
        self.db = db
        self.redis = redis
    
    async def create_session(self, requirements: str) -> Session:
        session = Session(requirements=requirements)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
    
    async def get_session(self, session_id: str) -> SessionResponse:
        stmt = select(Session).where(Session.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Redis에서 진행 상태 조회
        agent_status = await self.redis.hgetall(f"session:{session_id}:agents")
        
        return SessionResponse(
            id=session.id,
            requirements=session.requirements,
            status=session.status,
            version=session.version,
            created_at=session.created_at,
            agent_status=agent_status
        )
    
    async def update_session_status(self, session_id: str, status: str):
        stmt = update(Session).where(Session.id == session_id).values(status=status)
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def create_artifact(self, session_id: str, artifact: ArtifactCreate):
        db_artifact = Artifact(
            session_id=session_id,
            type=artifact.type,
            content=artifact.content,
            quality_score=artifact.quality_score
        )
        self.db.add(db_artifact)
        await self.db.commit()
```

---

## 7. 검색·수집 파이프라인 (Python)

### 7.1 스케줄러 (APScheduler) (`app/services/crawl_scheduler.py`)
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.crawl_service import crawl_docs

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', day_of_week='mon,wed,fri', hour=9)
async def scheduled_crawl():
    """매주 월,수,금 오전 9시 실행"""
    await crawl_docs([
        "https://nodejs.org/en/docs/guides/",
        "https://nextjs.org/docs",
        "https://supabase.com/docs"
    ])

def start_scheduler():
    scheduler.start()
```

### 7.2 크롤러 (`app/services/crawl_service.py`)
```python
import httpx
from bs4 import BeautifulSoup
from app.schemas.knowledge import KnowledgeCreate
from app.services.search_service import add_knowledge

async def crawl_docs(urls: list[str]):
    async with httpx.AsyncClient() as client:
        for url in urls:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 메인 콘텐츠 추출
            main_content = soup.select_one('main') or soup.select_one('article')
            if not main_content:
                continue
            
            text = main_content.get_text(separator='\n', strip=True)
            
            # 임베딩 생성
            from app.services.llm import create_embedding
            embedding = await create_embedding(text)
            
            # 저장
            knowledge = KnowledgeCreate(
                content=text[:8000],  # 8KB 제한
                embedding=embedding,
                metadata={
                    "url": url,
                    "source": "official_docs",
                    "scraped_at": datetime.utcnow().isoformat()
                }
            )
            await add_knowledge(knowledge)
```

---

## 8. 프론트엔드 통합 (React ↔ FastAPI)

### 8.1 API 클라이언트 (`frontend/src/api/client.ts`)
```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 1000 * 60 * 5 } // 5분 캐시
  }
});

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function createSession(requirements: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ requirements })
  });
  return response.json();
}

export async function getSession(sessionId: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`);
  return response.json();
}

export async function streamAgentStatus(sessionId: string, onMessage: (data: any) => void) {
  const eventSource = new EventSource(`${API_BASE_URL}/api/v1/agents/${sessionId}/stream`);
  eventSource.onmessage = (e) => onMessage(JSON.parse(e.data));
  return () => eventSource.close();
}
```

### 8.2 React Query 훅 (`frontend/src/hooks/useSession.ts`)
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createSession, getSession, streamAgentStatus } from '../api/client';

export function useCreateSession() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (requirements: string) => createSession(requirements),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    }
  });
}

export function useSession(sessionId: string) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => getSession(sessionId),
    enabled: !!sessionId,
    refetchInterval: (data) => data?.status === 'completed' ? false : 2000
  });
}
```

---

## 9. 배포 전략 (Render + Docker)

### 9.1 Dockerfile (`backend/Dockerfile`)
```dockerfile
FROM python:3.11-slim

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY ./app /app/app

# 포트 노출
EXPOSE 10000

# 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
```

### 9.2 Render 설정 (`render.yaml`)
```yaml
services:
  - type: web
    name: devstrategist-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port 10000"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: DATABASE_URL
        fromDatabase:
          name: devstrategist-db
          property: connectionString
      - key: OPENAI_API_KEY
        sync: false
      - key: SUPABASE_KEY
        sync: false

databases:
  - name: devstrategist-db
    plan: free  # PostgreSQL 무료 티어
```

---

## 10. 테스트 전략 (pytest)

### 10.1 pytest 설정 (`tests/conftest.py`)
```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models.models import Base
from app.db.session import AsyncSessionLocal

@pytest_asyncio.fixture
async def test_db():
    """테스트용 in-memory SQLite"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest_asyncio.fixture
async def client():
    """테스트용 FastAPI 클라이언트"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    with TestClient(app) as client:
        yield client
```

### 10.2 에이전트 테스트 (`tests/test_agents.py`)
```python
import pytest
from app.agents.analyzer import RequirementAnalyzer

@pytest.mark.asyncio
async def test_requirement_analyzer():
    agent = RequirementAnalyzer()
    input_data = AgentInput(requirements="Build a Next.js ecommerce platform")
    
    output = await agent.run(input_data)
    
    assert "analysis" in output.output
    assert len(output.output["entities"]) > 0
    assert output.token_usage > 0
```

---

## 11. 실행 단계별 상세 로드맵 (총 8주)

### Phase 1: 코어 인프라 구축 (1~2주차)

**1주차: DB + FastAPI 기본 구조**

| 작업 | 상세 내용 | 산출물 |
|------|-----------|--------|
| **Day 1** | Supabase 계정 생성, PostgreSQL + pgvector 활성화 | `.env` (SUPABASE_URL, KEY) |
| **Day 2** | SQLAlchemy 모델 작성, Alembic 마이그레이션 설정 | `app/models.py`, `alembic/` |
| **Day 3** | FastAPI 메인 앱, 의존성 주입 설정 | `app/main.py`, `app/core/` |
| **Day 4** | 단일 엔드포인트 `POST /sessions` 구현 | `app/api/v1/sessions.py` |
| **Day 5** | 테스트 DB 설정, pytest로 CRUD 테스트 | `tests/test_sessions.py` |

**2주차: 단일 에이전트 PoC**

| 작업 | 상세 내용 | 산출물 |
|------|-----------|--------|
| **Day 6** | LangChain 초기화, BaseAgent 추상 클래스 | `app/agents/base.py` |
| **Day 7** | RequirementAnalyzer 구현 (단일 프롬프트) | `app/agents/analyzer.py` |
| **Day 8** | `/analyze` 엔드포인트, 서비스 계층 연동 | `app/api/v1/agents.py` |
| **Day 9** | React 개발 환경 설정, CORS 연결 | `frontend/` + FastAPI CORS |
| **Day 10** | E2E 테스트 (요구사항 → 결과) | `curl` 테스트 스크립트 |

---

### Phase 2: 검색 및 확장 (3~4주차)

**3주차: pgvector 검색 파이프라인**

| 작업 | 상세 내용 | 산출물 |
|------|-----------|--------|
| **Day 11** | knowledge_base 테이블, 임베딩 함수 | `app/models.py` 수정 |
| **Day 12** | 크롤러 구현 (httpx + BeautifulSoup) | `app/services/crawl_service.py` |
| **Day 13** | APScheduler로 주 3회 자동 수집 | `app/services/crawl_scheduler.py` |
| **Day 14** | 검색 서비스, 유사도 계산 로직 | `app/services/search_service.py` |
| **Day 15** | StackRecommender에 검색 연동 | `app/agents/recommender.py` |

**4주차: 프론트엔드 고도화**

| 작업 | 상세 내용 | 산출물 |
|------|-----------|--------|
| **Day 16** | React Query로 상태 관리, SSE 연결 | `frontend/src/hooks/useSession.ts` |
| **Day 17** | 결과 화면 (탭 UI), Markdown 렌더링 | `frontend/src/pages/ResultPage.tsx` |
| **Day 18** | 히스토리 화면 (세션 리스트, 버전) | `frontend/src/pages/HistoryPage.tsx` |
| **Day 19** | PWA 설정, 오프라인 IndexedDB 저장 | `frontend/vite.config.ts` |
| **Day 20** | GitHub Pages 배포 테스트 | `.github/workflows/deploy-pages.yml` |

---

### Phase 3: 멀티에이전트 안정화 (5~6주차)

**5주차: 4개 에이전트 체이닝**

| 작업 | 상세 내용 | 산출물 |
|------|-----------|--------|
| **Day 21** | ArchitectAgent, StackAgent 구현 | `app/agents/architect.py` |
| **Day 22** | DocumentAgent (OpenAPI/ERD 생성) | `app/agents/documenter.py` |
| **Day 23** | AgentOrchestrator 병렬 실행 로직 | `app/core/orchestrator.py` |
| **Day 24** | Redis 상태 관리, 진행률 추적 | `app/core/dependencies.py` + Redis |
| **Day 25** | 에이전트 재시도, 타임아웃, fallback | `app/agents/utils/retry.py` |

**6주차: 품질 평가 및 피드백**

| 작업 | 상세 내용 | 산출물 |
|------|-----------|--------|
| **Day 26** | DecisionLog 저장 로직 | `app/services/decision_logger.py` |
| **Day 27** | 품질 자동 채점 (완결성, 적합성) | `app/services/quality_evaluator.py` |
| **Day 28** | 사용자 피드백 API, 👍/👎 버튼 | `frontend/src/components/FeedbackButtons.tsx` |
| **Day 29** | E2E 테스트 (Cypress) | `cypress/e2e/fullflow.cy.ts` |
| **Day 30** | 성능 테스트 (k6) | `k6-script.js` |

---

### Phase 4: 프로덕션 배포 (7~8주차)

**7주차: 보안 및 모니터링**

| 작업 | 상세 내용 | 산출물 |
|------|-----------|--------|
| **Day 31** | Rate limiting (60req/min) | `app/middleware/rate_limit.py` |
| **Day 32** | PII 마스킹 (Presidio) | `app/utils/security.py` |
| **Day 33** | 라이선스 검증 (OSS Gadget) | `app/utils/license_checker.py` |
| **Day 34** | Grafana Cloud 연동, 메트릭 노출 | `app/middleware/metrics.py` |
| **Day 35** | 감사 로그 (`audit_logs` 테이블) | `app/models.py` 추가 |

**8주차: MVP 출시**

| 작업 | 상세 내용 | 산출물 |
|------|-----------|--------|
| **Day 36** | Docker 이미지 빌드, Render 배포 | `Dockerfile`, `render.yaml` |
| **Day 37** | 커스텀 도메인 연결 (Cloudflare) | `devstrategist.ai` |
| **Day 38** | 최종 문서 작성 (README, API Docs) | `README.md`, Swagger UI |
| **Day 39** | 베타 테스터 10명 초대, 피드백 수집 | 베타 프로그램 운영 |
| **Day 40** | MVP 출시 및 회고 | Notion 회고 페이지 |

---

## 12. 최우선 작업 (Day 1~3)

### Day 1: 환경 구성
```bash
# 1. Python 3.11 설치 확인
python --version  # 3.11.x

# 2. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt  # 아래 내용 참고

# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
pgvector==0.2.4
pydantic==2.5.3
pydantic-settings==2.1.0
langchain==0.1.0
langchain-openai==0.0.2
redis==5.0.1
httpx==0.26.0
beautifulsoup4==4.12.2
pytest==8.0.0
pytest-asyncio==0.23.3
```

### Day 2: Supabase + SQLAlchemy
```python
# app/db/session.py (의존성 주입용)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.SUPABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Day 3: 최소 FastAPI 앱 실행
```python
# app/main.py
from fastapi import FastAPI
from app.api.v1 import sessions

app = FastAPI()
app.include_router(sessions.router, prefix="/api/v1/sessions")

@app.get("/")
async def root():
    return {"message": "DevStrategist API"}
```

**실행 확인**:
```bash
uvicorn app.main:app --reload --port 8000
# http://localhost:8000/docs 에서 Swagger UI 확인
```

---

## 13. 성공 지표 (Python 기준 재설정)

### Phase 1 (2주차)
- [ ] **기능**: `/api/v1/sessions` CRUD 완료, 단일 에이전트 동작
- [ ] **품질**: pytest 커버리지 70% 이상, Pydantic 검증 100%
- [ ] **성능**: API 응답 시간 < 200ms (DB 쿼리 포함)
- [ ] **배포**: Render에 Docker 배포 성공

### Phase 2 (4주차)
- [ ] **기능**: pgvector 검색 기반 스택 추천 제공
- [ ] **품질**: 10개 샘플 중 7개가 만족스러운 추천
- [ ] **성능**: 검색 포함 평균 5초 이내 (캐싱 미적용)
- [ ] **사용자**: 베타 신청 20명 모집

### Phase 3 (6주차)
- [ ] **기능**: 4개 에이전트 체이닝, 재시도 로직 정상 작동
- [ ] **품질**: DecisionLog 기록 완료, 품질 점수 0.7+ 달성률 75%
- [ ] **성능**: 에이전트 실패율 < 5%, 평균 45초 이내
- [ ] **모니터링**: Grafana 메트릭 수집 시작

### Phase 4 (8주차)
- [ ] **배포**: `devstrategist.ai` 도메인 연결, HTTPS 적용
- [ ] **보안**: Rate limiting, PII 마스킹 적용
- [ ] **사용자**: 50명 베타 테스트 완료, 피드백 100개 수집
- [ ] **비용**: 월간 $10 이내 유지

---

## 14. 최종 결정 및 다음 행동

### 14.1 승인 요청
- [ ] **기술 스택 확정**: FastAPI + SQLAlchemy + pgvector
- [ ] **예산 승인**: OpenAI API $20/월, Render $7/월 (선택)
- [ ] **일정 승인**: 2024년 2월 1일 ~ 3월 22일 (8주)

### 14.2 즉시 실행 (금일)
```bash
# 1. GitHub Repository 생성 (금일 18:00까지)
gh repo create devstrategist-ai --public --clone

# 2. Supabase 계정 생성 및 프로젝트 설정
# 3. 로컬 개발 환경 구성 (Python 3.11 + venv)
# 4. 팀원 초대 (GitHub + Slack)
```

### 14.3 1주차 회의
- **일시**: 2024년 2월 2일 (금) 오전 10시
- **목적**: Day 1~5 진행 상황 점검, 블로커 공유
- **준비물**: 로컬 실행 화면 데모 (GitHub PR)

**본 기획서는 Python/FastAPI 기반으로 2024년 2월 1일부로 확정되며, 모든 개발은 이 문서를 기준으로 진행됩니다.**