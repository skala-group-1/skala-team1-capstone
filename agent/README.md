# agent — FastAPI + LangGraph

AI 상담 에이전트(메인 그래프 + 병원 서브그래프), Harness, 큐 워커(AI 작업·번역)가 들어가는 서비스입니다.
병원 서브에이전트는 LLM·MCP 조회와 웹 채팅 큐에 연결되어 있습니다. 메인 AI와 번역 워커,
실제 예약 변경 실행은 아직 골격입니다. 남은 작업은 `# TODO(agent):`로 표시합니다.

병원 선택 전 노드·프롬프트·테스트는 [`coordinator/`](../coordinator/README.md)에서 관리합니다.
공통 실행 환경은 이 폴더에 두며, 로컬 실행은 `PYTHONPATH=..`로 저장소 루트의 역할 패키지를 읽습니다.

- 설계 기준: Notion 「AI Agent 설계」(그래프·State), 「Harness 명세」, 「공통 계약서」(큐 메시지·SSE), 「MCP 설계」(도구 이름)
- 남은 일 찾기: `rg -n "TODO\\(agent\\)" app prompts`

## 병원 상세 → 서브에이전트 웹 채팅

프론트의 **병원 상세 → 이 병원에 물어보기**로 진입합니다.
backend가 보낸 `conversation.mode=HOSPITAL`과 `hospitalId`를 사용하며 메인 LLM을 호출하지 않습니다.
`conversationId`별로 대화를 보존하고 `STATUS`, `DONE`, `APPROVAL_REQUIRED`, `FAILED`를
`ai.task.event`로 보내면 backend가 SSE로 프론트에 전달합니다. 답변은 완성된 뒤 표시됩니다.

backend/Postgres/RabbitMQ를 먼저 실행한 뒤, 각각 별도 터미널에서 실행합니다.
다음 명령은 저장소 루트 기준이며, API 키와 서비스 토큰은 기존 루트 `.env`를 읽습니다.

```bash
# 업무 MCP: backend /internal 및 업무 DB 조회
cd mcp
USE_STUB=false MCP_HOST=127.0.0.1 BACKEND_INTERNAL_URL=http://localhost:8080/internal \
  uv run --frozen python -m business_mcp.server
```

```bash
# RAG MCP: 현재는 mock 문서 키워드 검색 (pgvector 미구현)
cd mcp
USE_STUB=true MCP_HOST=127.0.0.1 uv run --frozen python -m rag_mcp.server
```

```bash
cd agent
USE_FAKE_TOOLS=false BUSINESS_MCP_URL=http://127.0.0.1:9101/mcp \
  RAG_MCP_URL=http://127.0.0.1:9102/mcp \
  PYTHONPATH=.. uv run --frozen uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
VITE_USE_MSW=false npm run dev
```

- 브라우저는 backend 개발 CORS 설정에 맞춰 `http://localhost:5173`으로 접속합니다.
- `RABBITMQ_URL`은 실제 RabbitMQ 노출 포트에 맞춥니다. 현재 별도 `skala-hospital-chat`
  테스트 환경은 localhost **15675**, 일반 compose 기본값은 **5672**입니다.
- 현재 워커는 **1개 프로세스**로 실행합니다. MAIN 전용 워커를 같은 AI 큐에 동시에 붙이면
  메시지가 무작위 분배됩니다. 통합 시 공통 소비자에서 모드별로 분기하거나 별도 큐 계약을 합의해야 합니다.
  현재는 MAIN/HUMAN 요청에 `FAILED`를 보내며 번역 큐는 소비하지 않습니다.
- `DATABASE_URL`이 비어 있으면 대화·승인·이벤트 순번은 메모리 저장이라 재시작하면 사라집니다.
- 예약 승인 카드는 표시할 수 있지만 **실제 저장은 연결 전**입니다. 웹에서 승인해도
  변경 노드의 임시 성공 경로를 실행하지 않고, 미접수를 알리는 `FAILED`를 반환합니다.
- `uv run --frozen pytest -q`는 서비스 없이 실행하는 결정적 테스트입니다.
  예약 2개는 실제 그래프의 비동기 조회·승인·거절 경로를 검증하되 외부 LLM/MCP와 변경 실행은
  테스트 대역을 사용합니다. 테스트 통과가 DB 예약 저장을 의미하지 않습니다.

## 실행

```bash
cd agent
uv sync                                   # Python 3.12 가상환경 + 의존성
uv run pytest                             # 단위·그래프 테스트 (MCP·DB·큐 없이 실행)
PYTHONPATH=.. uv run python -m app.cli --thread t1      # CLI 대화 (MAIN 모드)
PYTHONPATH=.. uv run python -m app.cli --thread h1 --mode HOSPITAL --hospital-id 1   # 기본 fake 모드 병원 대화 (LLM 키 필요)
PYTHONPATH=.. uv run python -m app.cli --conditions '{"procedure_code":"JAW_BOTOX","date_from":"2026-10-20"}'  # planner 경로
PYTHONPATH=.. uv run uvicorn app.api.main:app --port 8000   # 큐 워커 + GET /health (RabbitMQ 필요)
```

환경변수는 저장소 루트 `.env`를 읽습니다 (`app/config.py`, 「공통 계약서」 9장). 주요 값:

| env | 기본값 | 설명 |
| --- | --- | --- |
| `OPENAI_API_KEY`, `LLM_PRIMARY_MODEL`, `LLM_FAST_MODEL`, `LLM_FALLBACK_MODEL` | gpt-5-nano | D-18 |
| `USE_FAKE_TOOLS` | `true` | 아래 "가짜 도구" 참고 |
| `BUSINESS_MCP_URL` / `RAG_MCP_URL` | `http://business-mcp:9101/mcp` / `http://rag-mcp:9102/mcp` | `USE_FAKE_TOOLS=false` 일 때 |
| `MCP_PROJECT_DIR` | `../mcp` | stdio 로 띄울 MCP 프로젝트 위치 |
| `DATABASE_URL` | (비어 있음) | 비어 있으면 MemorySaver(재시작 시 사라짐). 넣으면 PostgresSaver/PostgresStore (schema agent) |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | 큐 워커 |

## 가짜 도구 (D-31)

agent 안에 별도의 가짜 도구를 만들지 않습니다. `USE_FAKE_TOOLS=true`면 `app/mcp_client/client.py`가
**business-mcp·rag-mcp를 stdio 하위 프로세스로 직접 띄우고 `USE_STUB=true`**(mock JSON 응답)로 연결합니다.
그래서 처음부터 실제 MCP 도구 이름·스키마로 개발되고, 나중에 `USE_FAKE_TOOLS=false`로 바꾸면 compose의 HTTP 서버로 넘어갑니다.
MCP 코드는 `mcp/`에 있습니다. 도구 목록은 처음 필요한 시점에 불러옵니다(lazy).
단위 테스트는 외부 서비스 없이 실행하지만 병원 CLI 대화에는 LLM 키와 MCP 실행 환경이 필요합니다.

## 폴더 구조

```
agent/
├─ app/
│  ├─ config.py            「공통 계약서」 9장 env
│  ├─ graph/state.py       「AI Agent 설계」 2장 + 9-5 State
│  ├─ graph/routing.py     조건부 엣지 (state 값 기반, 실제 동작)
│  ├─ graph/builder.py     메인 그래프 v2 + 병원 서브그래프 조립
│  ├─ nodes/               노드 1개 = 파일 1개 (상단에 입력→출력·LLM/도구·프롬프트·근거 문서)
│  ├─ mcp_client/          MultiServerMCPClient(D-31) + 도구 이름 상수(화이트리스트·변경 도구)
│  ├─ harness/             「Harness 명세」 8요소 (loop 한도는 구현, 나머지는 TODO)
│  ├─ workers/             「공통 계약서」 7장 큐 메시지 모델, SSE 이벤트 enum, aio-pika consumer/publisher 틀
│  ├─ api/main.py          FastAPI /health (8000)
│  └─ cli.py               CLI 러너
├─ prompts/*.md            「AI Agent 설계」 8장 프롬프트 8종 (version 메타 + 작성할 내용 주석)
├─ tests/                  그래프 분기·interrupt, 메시지 camelCase, Harness
└─ Dockerfile              build context = 저장소 루트
```

## 그래프 (`draw_mermaid` 출력, 골격 기준)

메인 그래프 (「AI Agent 설계」 9-1 v2)

```mermaid
graph TD;
	__start__([<p>__start__</p>]):::first
	load_memory(load_memory)
	guard_input(guard_input)
	guard_reply(guard_reply)
	open_hospital_conversation(open_hospital_conversation)
	extract_conditions(extract_conditions)
	ask_clarify(ask_clarify)
	planner_agent(planner_agent)
	tools(tools)
	verify(verify)
	memory_propose(memory_propose)
	respond(respond)
	hospital_subgraph(hospital_subgraph)
	__end__([<p>__end__</p>]):::last
	__start__ --> load_memory;
	ask_clarify --> respond;
	extract_conditions -.-> ask_clarify;
	extract_conditions -.-> planner_agent;
	guard_input -. &nbsp;end&nbsp; .-> __end__;
	guard_input -.-> extract_conditions;
	guard_input -.-> guard_reply;
	guard_input -.-> hospital_subgraph;
	guard_input -.-> open_hospital_conversation;
	guard_reply --> respond;
	hospital_subgraph --> respond;
	load_memory --> guard_input;
	memory_propose --> respond;
	open_hospital_conversation --> respond;
	planner_agent -.-> tools;
	planner_agent -.-> verify;
	tools --> planner_agent;
	verify -.-> memory_propose;
	verify -.-> planner_agent;
	respond --> __end__;
```

병원 서브그래프 (「AI Agent 설계」 4장)

```mermaid
graph TD;
	__start__([<p>__start__</p>]):::first
	load_hospital_context(load_hospital_context)
	hospital_agent(hospital_agent)
	hospital_tools(hospital_tools)
	approval(approval)
	execute_action(execute_action)
	__end__([<p>__end__</p>]):::last
	__start__ --> load_hospital_context;
	approval -.-> execute_action;
	approval -.-> hospital_agent;
	execute_action --> hospital_agent;
	hospital_agent -. &nbsp;end&nbsp; .-> __end__;
	hospital_agent -.-> approval;
	hospital_agent -.-> hospital_tools;
	hospital_tools --> hospital_agent;
	load_hospital_context --> hospital_agent;
```

## 담당자가 채울 순서 (「파트별 착수 가이드」 Agent 착수 순서 기준)

1. `guard_input`·`extract_conditions`에 LLM structured output 붙이기 (`prompts/` 작성)
2. `planner_agent` tool-calling + `harness/tools.py` 래퍼 (절단·ToolError·tool_ledger)
3. `verify`(Critic)·`memory_propose`·`load_memory` (「AI Agent 설계」 9-3·9-4)
4. 병원 서브그래프 `hospital_agent` LLM 교체, `execute_action` 실제 도구 호출
5. `workers/consumer.py` 큐 연결 + `workers/events.py` SSE 변환기, `api/main.py` lifespan
6. Harness 나머지(context·recovery·observability) + `tests/eval/cases.yaml`
