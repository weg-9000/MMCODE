import uuid
import pytest
import asyncio
import logging
import sys
import os

# 프로젝트 루트 경로 추가 (backend 폴더 기준)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 에이전트 및 설정 임포트
from app.agents.requirement_analyzer.core.agent import RequirementAnalyzer
from app.agents.requirement_analyzer.config.settings import RequirementAnalyzerSettings

from app.agents.architect_agent.core.agent import ArchitectAgent
from app.agents.architect_agent.config.settings import ArchitectAgentSettings

from app.agents.stack_recommender.core.agent import StackRecommenderAgent
from app.agents.stack_recommender.config.settings import StackRecommenderSettings

from app.agents.document_agent.core.agent import DocumentAgent
from app.agents.document_agent.config.settings import DocumentAgentSettings

from app.agents.shared.a2a_client.mock_client import InMemoryA2AClient


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_full_system_flow():
    """
    전체 시스템 흐름 통합 테스트
    User Input -> Requirement Analyzer -> Architect -> Stack Recommender -> Document -> Output
    """
    print("\n=== Starting Full System Flow Test ===")

    # 1. 설정 인스턴스 생성 (환경변수 로드)
    req_settings = RequirementAnalyzerSettings()
    arch_settings = ArchitectAgentSettings()
    stack_settings = StackRecommenderSettings()
    doc_settings = DocumentAgentSettings()

    # 디버깅: 설정값 확인
    print(f"DEBUG: Architect LLM Model: {arch_settings.llm_model}")
    print(f"DEBUG: Stack LLM Model: {stack_settings.llm_model}")

    # 2. 하위 에이전트 생성 (설정 딕셔너리 주입)
    # 각 에이전트는 model_dump()로 딕셔너리 변환된 설정을 받습니다.
    architect = ArchitectAgent(arch_settings.model_dump())
    stack = StackRecommenderAgent(stack_settings.model_dump())
    document = DocumentAgent(doc_settings.model_dump())

    # 3. Mock A2A Client 설정 및 에이전트 등록
    # 실제 HTTP 통신 대신 메모리 내에서 직접 객체를 호출합니다.
    mock_client = InMemoryA2AClient()
    

    mock_client.register("architect-agent", architect)
    mock_client.register("stack-recommender", stack)  # 혹은 stack-recommender-agent
    mock_client.register("document-agent", document)
    
    # StackRecommender가 stack-recommender-agent로 등록되어야 할 수도 있음 (Config 확인)
    mock_client.register("stack-recommender-agent", stack) 

    print("✅ Agents registered to Mock Client")

    analyzer = RequirementAnalyzer(
        agent_config=req_settings.model_dump(),
        a2a_client=mock_client
    )
    print("✅ Requirement Analyzer initialized")

    # 5. 테스트 시나리오 실행
    user_input = "Python과 React를 사용하여 확장 가능한 이커머스 쇼핑몰을 구축하고 싶습니다. MSA 구조를 선호합니다."
    print(f"\nInput: {user_input}")
    session_id = str(uuid.uuid4())
    
    try:
        
        result = await analyzer.analyze_and_orchestrate(
            requirements=user_input,
            session_id=session_id
        )

        # 6. 결과 검증
        print("\n=== Test Result ===")
        print(f"Status: {result['status']}")
        assert result['status'] == "completed"
        
        # 결과는 Dict[str, Any] 형태이므로 딕셔너리 키로 접근
        if result.get("status") == "completed":
            print("✅ Analysis completed successfully")
            if "orchestration_result" in result:
                print("✅ Orchestration completed")
        elif result.get("status") == "failed":
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
        
        # Check analysis content
        if "analysis" in result:
            analysis = result["analysis"]
            print(f"✅ Analysis generated with domain: {analysis.get('domain', 'unknown')}")
        
        assert result.get("status") == "completed", f"Expected completed status, got {result.get('status')}: {result.get('error', '')}"
        print("✅ Test Passed Successfully")

    except Exception as e:
        logger.exception("Test Failed with Exception")
        pytest.fail(f"System flow test failed: {e}")

if __name__ == "__main__":
    # 직접 실행 가능하도록 설정
    asyncio.run(test_full_system_flow())
