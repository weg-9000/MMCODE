<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 그럼 현재 이제 개발을 진행하려고 하는데 a2a로 재구성하여 기획을 진행하려고한다. a2a로 하느 것이 적합하고 더 좋은 방향인지 파악하고 더 좋은 방향에 알맞게 에이전트에 대해 재 기획을 진행한다.

A2A 기반 재구성이 **현재 프로젝트에 더 적합하고 확장성·유지보수성이 크게 개선되는 방향**입니다. 이유는 다음과 같습니다:

- **협업 중심 워크플로우**: RequirementAnalyzer → ArchitectAgent → StackRecommender → DocumentAgent는 명확한 파이프라인이지만, 각 단계가 독립적이고 자율적인 협업이 가능한 구조입니다. A2A는 이러한 **Task 기반 파이프라인에 최적화**되어 있습니다.[^1][^2][^3]
- **프레임워크/조직 경계 확장성**: 현재는 LangChain 기반이지만, 향후 외부 에이전트(보안 스캐너, 법무 검토 등)와 연동이 필요할 가능성이 높습니다. A2A는 표준 프로토콜로 이를 가능하게 합니다.[^2][^4]
- **운영 복잡도 감소**: 중앙 오케스트레이터는 단일 장애점이고 에이전트 추가 시마다 수정이 필요합니다. A2A는 **에이전트 자율 협업**으로 확장이 용이합니다.[^5][^6]
- **기존 설계와의 자연스러운 연결**: Redis 상태 관리, SSE 스트리밍, Artifact 저장은 A2A의 Task 상태·Artifact·스트리밍 메커니즘과 대체 가능합니다.[^3][^1]

***

## **A2A 기반 재기획: Agent Mesh 구조**

### **1. 전체 아키텍처 개요**

**이전**: `AgentOrchestrator`가 모든 에이전트를 순차/병렬로 실행하고 상태를 중앙에서 관리
**이후**: **Agent Mesh** 구조로 각 에이전트가 A2A 서버로 운영되며, RequirementAnalyzer가 **Task 생성 및 하위 에이전트 호출**을 주도

```
사용자 요구사항 → FastAPI (세션 관리) → RequirementAnalyzer (A2A Client)
    ↓ (A2A Task 생성)
ArchitectAgent ←→ StackRecommender ←→ DocumentAgent (각 A2A Server)
    ↓ (Artifact 수집)
FastAPI → 프론트엔드 (SSE 스트리밍)
```


***

## **2. 재설계된 에이전트 역할 및 A2A 통합**

### **2.1. RequirementAnalyzer (요구사항 분석 에이전트)**

**위치**: `app/agents/analyzer.py`
**역할**: A2A **Client + Orchestrator 역할**을 겸함. 사용자 요구사항을 분석하고, 하위 에이전트들에게 A2A Task를 발행·모니터링

#### **주요 기능**

- **A2A Client**: `a2a-sdk`를 사용하여 ArchitectAgent, StackRecommender, DocumentAgent에게 Task 생성
- **분석 및 Task 분해**: 요구사항을 분석하고, 각 하위 에이전트가 수행할 Task 목록 생성
- **의존성 관리**: ArchitectAgent Task 완료 후 StackRecommender Task 발행 등의 순서 제어
- **Artifact 수집**: 각 에이전트가 생성한 Artifact를 수집하여 세션에 저장


#### **구현 세부사항**

```python
from a2a import A2AClient, Task, AgentCard

class RequirementAnalyzer:
    def __init__(self):
        self.a2a_client = A2AClient()
        self.sub_agents = {
            "architect": AgentCard.from_url("https://architect-agent.dev/card"),
            "recommender": AgentCard.from_url("https://recommender-agent.dev/card"),
            "documenter": AgentCard.from_url("https://documenter-agent.dev/card")
        }
    
    async def run(self, requirements: str) -> SessionResult:
        # 1. 분석
        analysis = await self.analyze_requirements(requirements)
        
        # 2. A2A Task 생성 및 발행
        architect_task = await self.a2a_client.create_task(
            agent=self.sub_agents["architect"],
            context={"analysis": analysis.model_dump()}
        )
        
        # 3. Task 완료 대기 및 Artifact 수집
        result = await self.a2a_client.wait_for_task(architect_task.id)
        artifacts.append(result.artifact)
```


***

### **2.2. ArchitectAgent (아키텍처 설계 에이전트)**

**위치**: `app/agents/architect.py`
**역할**: A2A **Server**. RequirementAnalyzer로부터 Task를 받아 아키텍처 설계 수행

#### **주요 기능**

- **A2A Server**: `/a2a/tasks` 엔드포인트를 통해 Task 수신
- **설계 수행**: 분석 결과를 바탕으로 아키텍처 패턴 추천 및 컴포넌트 설계
- **Artifact 생성**: Mermaid 다이어그램, ADR 문서를 Artifact로 반환


#### **구현 세부사항**

```python
from a2a import A2AServer, TaskHandler

class ArchitectAgent(A2AServer):
    def __init__(self):
        super().__init__(agent_card=self.create_agent_card())
    
    def create_agent_card(self) -> AgentCard:
        return AgentCard(
            name="architect-agent",
            description="Designs software architecture based on requirements",
            url="https://architect-agent.dev",
            skills=[{
                "id": "architecture-design",
                "description": "Generates architecture patterns and component diagrams"
            }],
            authentication={"type": "OAuth2"}
        )
    
    @TaskHandler()
    async def handle_architecture_task(self, task: Task) -> Artifact:
        analysis = task.context["analysis"]
        architecture = await self.design_architecture(analysis)
        return Artifact(
            type="architecture",
            content=architecture.model_dump(),
            metadata={"quality_score": 0.92}
        )
```


***

### **2.3. StackRecommender (기술 스택 추천 에이전트)**

**위치**: `app/agents/recommender.py`
**역할**: A2A **Server**. 아키텍처 설계를 바탕으로 기술 스택 추천

#### **주요 기능**

- **A2A Server**: `/a2a/tasks` 엔드포인트를 통해 Task 수신
- **스택 선정**: 아키텍처 정보를 분석하여 프레임워크·데이터베이스·인프라 추천
- **Artifact 생성**: `stack.yml` 형식의 스택 정의서 및 품질 점수 반환


#### **구현 세부사항**

```python
class StackRecommender(A2AServer):
    @TaskHandler()
    async def handle_stack_task(self, task: Task) -> Artifact:
        architecture = task.context["architecture"]
        stack = await self.recommend_stack(architecture)
        return Artifact(
            type="stack",
            content=stack.model_dump(),
            metadata={"quality_score": 0.88}
        )
```


***

### **2.4. DocumentAgent (문서 자동 생성 에이전트)**

**위치**: `app/agents/documenter.py`
**역할**: A2A **Server**. 분석·아키텍처·스택 정보를 종합하여 문서 생성

#### **주요 기능**

- **A2A Server**: `/a2a/tasks` 엔드포인트를 통해 Task 수신
- **문서 생성**: OpenAPI, ERD, 컨텍스트 다이어그램, README 초안 생성
- **Artifact 생성**: 다양한 문서 타입의 Artifact 반환


#### **구현 세부사항**

```python
class DocumentAgent(A2AServer):
    @TaskHandler()
    async def handle_document_task(self, task: Task) -> Artifact:
        # context에 analysis, architecture, stack 모두 포함
        documents = await self.generate_documents(task.context)
        return Artifact(
            type="documents",
            content=documents.model_dump(),
            metadata={"quality_score": 0.90}
        )
```


***

## **3. A2A 통합을 위한 인프라 변경사항**

### **3.1. FastAPI 서버 구조**

**변경 전**: `AgentOrchestrator`가 에이전트 실행을 직접 제어
**변경 후**: **A2A Agent Registry + Task Broker** 역할로 축소

```python
# app/api/v1/agents.py
from fastapi import APIRouter
from app.core.a2a_registry import A2ARegistry

router = APIRouter()
registry = A2ARegistry()

@router.post("/sessions/{session_id}/analyze")
async def start_analysis(session_id: str):
    # RequirementAnalyzer에게 A2A Client 역할 수행
    analyzer = RequirementAnalyzer()
    task = await analyzer.run_for_session(session_id)
    return {"task_id": task.id}

@router.get("/sessions/{session_id}/stream")
async def stream_status(session_id: str):
    # A2A Task 상태를 Redis에서 조회하여 SSE 스트리밍
    return EventSourceResponse(generate_sse(session_id))
```


### **3.2. Agent Registry \& Discovery**

```python
# app/core/a2a_registry.py
class A2ARegistry:
    def __init__(self):
        self.agents: Dict[str, AgentCard] = {}
    
    async def register_agent(self, agent_card: AgentCard):
        # Redis에 Agent Card 저장
        await redis.set(f"agent:{agent_card.name}", agent_card.json())
    
    async def discover_agent(self, name: str) -> AgentCard:
        # Redis 또는 HTTP를 통해 Agent Card 검색
        return AgentCard.parse_raw(await redis.get(f"agent:{name}"))
```


### **3.3. Redis 상태 관리 개선**

**기존**: `session:{session_id}:agents` 해시맵에 에이전트 상태 저장
**변경**: `task:{task_id}` 형식으로 A2A Task 상태 저장

```python
# Redis key structure
task:{task_id}:status  # "submitted", "working", "completed", "failed"
task:{task_id}:context # Task context (analysis, architecture, etc.)
task:{task_id}:artifacts # List of artifact IDs
task:{task_id}:parent_id # Parent task ID for hierarchical tasks
```


***

## **4. 프론트엔드 통합**

### **4.1. SSE 스트리밍 유지**

현재의 SSE 스트리밍 방식은 A2A의 Task 스트리밍과 호환됩니다.[^1][^3]

```typescript
// frontendsrchooksuseSession.ts
export function useAgentStream(sessionId: string) {
  const eventSource = new EventSource(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/stream`
  );
  
  eventSource.onmessage = (event) => {
    const taskUpdate = JSON.parse(event.data);
    // taskUpdate: {task_id, status, agent_name, progress, artifact}
    onMessage(taskUpdate);
  };
}
```


### **4.2. 진행 상황 표시 개선**

A2A Task의 계층 구조를 시각화하여 하위 에이전트별 진행 상황을 표시

```typescript
// Task hierarchy visualization
- Requirement Analysis (root task)
  └── Architecture Design (sub-task)
      └── Stack Recommendation (sub-task)
          └── Documentation Generation (sub-task)
```


***

## **5. 운영 및 모니터링**

### **5.1. 분산 트레이싱**

A2A 작업을 추적하기 위해 OpenTelemetry 통합

```python
# app/core/telemetry.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def trace_a2a_task(task_id: str):
    with tracer.start_as_current_span("a2a_task") as span:
        span.set_attribute("task.id", task_id)
        span.set_attribute("agent.name", "requirement-analyzer")
```


### **5.2. 품질 평가 및 피드백**

각 에이전트의 Artifact 품질 점수를 A2A 메타데이터에 포함하여 중앙에서 집계

```python
# Quality aggregator
async def calculate_session_quality(session_id: str):
    artifacts = await get_artifacts_by_session(session_id)
    total_score = sum(a.metadata["quality_score"] for a in artifacts)
    return total_score / len(artifacts)
```


***

## **6. 전환 로드맵 (4주)**

### **Week 1: A2A 기반 구조 마련**

- Day 1-2: `a2a-sdk` 설치 및 POC (Python)
- Day 3-4: 각 에이전트에 A2A 서버/클라이언트 기본 구조 추가
- Day 5: Agent Registry 구현 및 Redis 연동


### **Week 2: RequirementAnalyzer 오케스트레이션 이관**

- Day 6-7: RequirementAnalyzer가 A2A 클라이언트로 Task 생성하도록 수정
- Day 8-9: ArchitectAgent, StackRecommender에 A2A 서버 핸들러 추가
- Day 10: 의존성 관리 및 Task 순서 제어 로직 구현


### **Week 3: DocumentAgent 및 통합**

- Day 11-12: DocumentAgent에 A2A 서버 핸들러 추가
- Day 13-14: FastAPI를 A2A Agent Registry + Task Broker로 개조
- Day 15: SSE 스트리밍을 A2A Task 상태와 연동


### **Week 4: 테스트 및 검증**

- Day 16-17: E2E 테스트 (A2A 전체 워크플로우)
- Day 18-19: 에러 처리, 재시도, fallback 로직 검증
- Day 20: 문서화 및 배포

***

## **7. 결록 및 권장사항**

**A2A 기반 재구성을 적극 권장**합니다. 이유는:

1. **기술적 적합성**: 현재 파이프라인 구조가 A2A Task 기반 협업과 완벽히 일치합니다.[^2][^1]
2. **확장성**: 외부 에이전트(보안, 법무, 비용 최적화 등) 추가가 용이해집니다.[^4][^7]
3. **운영 효율성**: 중앙 오케스트레이터 제거로 단일 장애점을 없애고, 에이전트별 독립 배포·스케일링이 가능합니다.[^6][^5]
4. **표준 준수**: Google 주도 오픈 표준으로, 커뮤니티 지원과 생태계 성장이 기대됩니다.[^3][^2]

**위험 완화 전략**:

- 초기 2주는 얇은 오케스트레이터(세션 관리, 감사)를 유지하면서 A2A 협업을 검증
- 에이전트별 단위 테스트와

<div align="center">⁂</div>

[^1]: Project_plan.md

[^2]: https://a2a-protocol.org/latest/

[^3]: https://www.projectpro.io/article/google-agent-to-agent-protocol/1172

[^4]: https://www.wwt.com/blog/agent-2-agent-protocol-a2a-a-deep-dive

[^5]: https://www.wethinkapp.ai/blog/design-patterns-for-multi-agent-orchestration

[^6]: https://www.getdynamiq.ai/post/agent-orchestration-patterns-in-multi-agent-systems-linear-and-adaptive-approaches-with-dynamiq

[^7]: https://www.everestgrp.com/uncategorized/the-rise-of-agent-protocols-exploring-mcp-a2a-and-acp-blog.html

