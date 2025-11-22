import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
import os
from dotenv import load_dotenv

# --- [설정 로드] ---
# 스크립트 위치 기준으로 상위 폴더(backend)의 .env 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)  # backend 폴더를 파이썬 경로에 추가

dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}")

from app.core.config import settings
from app.models.models import Agent, Base 

# --- [DB URL 설정] ---
DATABASE_URL = settings.DATABASE_URL

# URL이 없거나 https(Supabase API URL)로 되어있으면 로컬 SQLite로 강제 전환
if not DATABASE_URL or str(DATABASE_URL).startswith("https://"):
    print("⚠️ Invalid or missing DATABASE_URL detected. Falling back to local SQLite.")
    DATABASE_URL = "sqlite+aiosqlite:///./devstrategist.db"

print(f"🔌 Connecting to database: {DATABASE_URL}")

async def seed_agents():
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    # --- [테이블 생성 로직 추가] ---
    print("🔨 Creating tables if they don't exist...")
    async with engine.begin() as conn:
        # Base에 정의된 모든 테이블(agents 포함) 생성
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    agents_data = [
        {
            "name": "RequirementAnalyzer",
            "role": "orchestrator",
            "description": "Analyzes user requirements and coordinates the strategy generation process.",
            "capabilities": {
                "skills": ["requirement_analysis", "task_decomposition", "quality_attribute_extraction"],
                "input_format": "natural_language",
                "output_format": "structured_json"
            },
            "endpoint_url": "local://requirement-analyzer",
            "status": "active"
        },
        {
            "name": "ArchitectAgent",
            "role": "architect",
            "description": "Designs system architecture and identifies patterns based on analysis.",
            "capabilities": {
                "skills": ["pattern_matching", "component_design", "diagram_generation"],
                "supported_patterns": ["microservices", "monolithic", "serverless", "event_driven"]
            },
            "endpoint_url": "local://architect-agent",
            "status": "active"
        },
        {
            "name": "StackRecommender",
            "role": "tech_lead",
            "description": "Recommends technology stacks based on architecture and constraints.",
            "capabilities": {
                "skills": ["stack_selection", "compatibility_check", "license_verification"],
                "languages": ["python", "javascript", "go", "java"]
            },
            "endpoint_url": "local://stack-recommender",
            "status": "active"
        },
        {
            "name": "DocumentAgent",
            "role": "technical_writer",
            "description": "Generates comprehensive technical documentation and specifications.",
            "capabilities": {
                "skills": ["markdown_generation", "openapi_spec", "erd_diagram"],
                "output_types": ["README", "API_SPEC", "ARCHITECTURE_DOC"]
            },
            "endpoint_url": "local://document-agent",
            "status": "active"
        }
    ]

    async with AsyncSessionLocal() as session:
        print("🌱 Seeding agents data...")
        for agent_info in agents_data:
            # 중복 데이터 생성 방지 로직은 생략 (테스트용)
            new_agent = Agent(
                id=str(uuid.uuid4()),
                name=agent_info["name"],
                role=agent_info["role"],
                description=agent_info["description"],
                capabilities=agent_info["capabilities"],
                endpoint_url=agent_info["endpoint_url"],
                status=agent_info["status"],
                created_at=datetime.utcnow()
                # updated_at 필드 제거됨
            )
            session.add(new_agent)
        
        await session.commit()
        print("✅ Agents seeded successfully!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_agents())
