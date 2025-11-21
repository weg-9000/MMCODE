<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 테스트에 대한 질문과 답변에 대한 예시를 시스템 분석을 통해 만들어 봤다. 올바른 흐름인지 파악하고 이제 진짜 테스트 하기 위한 방안을 설명한다.

`AGENT_TEST_PREPARATION.md` 문서를 분석한 결과, 시스템의 복잡도와 A2A 아키텍처의 특성을 잘 반영한 체계적인 테스트 계획이 수립되었습니다. **흐름은 매우 올바르며**, 특히 복잡도별 시나리오(Simple ~ Enterprise)와 각 에이전트별 예상 입출력(Mock Data)을 상세히 정의한 점은 테스트의 신뢰성을 크게 높여줄 것입니다.

이제 이 계획을 **"어떻게 효율적으로 실행할 것인가?"**에 초점을 맞춰, 테스트 실행 방안을 단계별로 설명합니다.

***

## 🚀 실전 테스트 실행 가이드 (Execution Strategy)

테스트는 **`단위(Unit)` → `통합(Integration)` → `E2E(End-to-End)`** 순서로 진행하여, 작은 문제를 먼저 잡고 시스템 전체를 검증하는 전략을 취합니다.

### Phase 1: 모의 객체(Mock) 기반 단위 테스트 (D-Day)

**목표**: 실제 LLM 호출 없이 각 에이전트의 로직이 정상 작동하는지 1초 이내에 검증합니다.

1. **Mock LLM Engine 구현**:
    * `app/core/llm/mock_engine.py`를 생성합니다.
    * `AGENT_TEST_PREPARATION.md`에 정의된 `MOCK_RESPONSES` JSON 파일들을 로드하여, 요청된 프롬프트 유형에 따라 미리 정의된 응답을 반환하게 합니다.
    * *이유*: OpenAI API 비용 절감 및 네트워크 변수 제거.
2. **에이전트별 로직 검증 (pytest)**:
    * **RequirementAnalyzer**: 입력 텍스트가 주어졌을 때 `AnalysisResult` 모델로 파싱되는지 확인.
    * **StackRecommender**: 아키텍처 입력값에 따라 `stack.yml` 포맷이 정확히 생성되는지 확인.
    * **실행 명령어**: `pytest tests/unit/`

### Phase 2: A2A 통신 통합 테스트 (D+1)

**목표**: 에이전트 간의 "대화"가 끊기지 않고 이어지는지 확인합니다. (실제 서버 구동)

1. **로컬 A2A Mesh 구성**:
    * `docker-compose.test.yml`을 작성하여 Redis, PostgreSQL, 그리고 4개의 에이전트 컨테이너를 띄웁니다.
    * 각 에이전트는 `http://architect-agent:8001` 등 내부 네트워크로 통신하도록 설정합니다.
2. **HTTP Client 테스트 (Test Script)**:
    * `tests/integration/test_a2a_flow.py` 작성.
    * **시나리오**:

3. RequirementAnalyzer에 `POST /task` 요청 전송.
4. `task_id`를 받아 `GET /tasks/{task_id}`로 1초마다 폴링.
5. 상태가 `analyzing` → `architecting` → `recommending` → `documenting` → `completed`로 변하는지 로그 확인.

### Phase 3: Playwright 기반 E2E 테스트 (D+2)

**목표**: 사용자가 웹 브라우저에서 겪을 경험을 검증합니다.

1. **UI 시나리오 자동화**:
    * `frontend/e2e/workflow.spec.ts` 작성.
    * 사용자 입력("채팅 앱 만들어줘") → "분석 시작" 클릭 → 로딩 바 진행 → 결과 화면 표시까지 자동화.
    * **핵심 검증**: 결과 화면에 `Architecture Diagram`, `Stack Table`, `API Docs` 3가지 요소가 모두 렌더링되었는지 `toBeVisible()`로 확인.

### Phase 4: 내구성(Resilience) 테스트 (D+3)

**목표**: 시스템이 망가졌을 때 어떻게 반응하는지 확인합니다. (카오스 엔지니어링)

1. **에이전트 강제 종료**:
    * `ArchitectAgent` 컨테이너를 `docker stop`으로 중지시킵니다.
    * `RequirementAnalyzer`가 이를 감지하고 `Status: Failed` 및 "아키텍처 에이전트 응답 없음" 에러 메시지를 반환하는지 확인합니다.
    * 다시 컨테이너를 시작했을 때, "재시도" 버튼을 통해 작업이 재개되는지 확인합니다.

***

## 🔍 테스트 실행 중점 체크리스트

테스트를 진행하면서 다음 사항들을 반드시 점검해야 합니다.


| 테스트 단계 | 체크 포인트 (Check Point) | 성공 기준 (Success Criteria) |
| :-- | :-- | :-- |
| **Unit** | **데이터 모델 일치성** | 모든 에이전트의 출력 JSON이 Pydantic 스키마 유효성 검사를 통과해야 함. |
| **Integration** | **Task Context 전달** | ArchitectAgent가 만든 설계 데이터가 손실 없이 StackRecommender에게 전달되는가? |
| **E2E** | **SSE 실시간성** | 브라우저에서 진행률(%)이 0%에서 100%까지 멈춤 없이 부드럽게 업데이트되는가? |
| **Performance** | **타임아웃 처리** | LLM 응답이 60초 이상 지연될 때, 무한 대기하지 않고 적절한 Timeout 에러를 뱉는가? |

## 🛠️ 바로 시작할 작업 (Action Item)

1. **Test Data 생성**: `AGENT_TEST_PREPARATION.md`에 있는 JSON 예시들을 `tests/data/` 폴더에 파일로 저장하세요.
2. **Mock Engine 작성**: 실제 OpenAI를 호출하지 않고 저장된 JSON을 반환하는 `MockLLMEngine` 클래스를 가장 먼저 구현하세요. 이것이 없으면 테스트 속도가 매우 느려집니다.

이 계획대로 진행하면, 시스템의 기능적 완성도뿐만 아니라 운영 안정성까지 확실하게 검증할 수 있습니다. 준비된 문서가 완벽하니 자신 있게 실행으로 옮기셔도 좋습니다
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: AGENT_TEST_PREPARATION.md

