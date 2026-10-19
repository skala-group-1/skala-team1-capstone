# agent — FastAPI + LangGraph

AI 상담 에이전트(메인 그래프 + 병원 서브그래프), Harness, 큐 워커(AI 작업·번역)가 들어가는 서비스입니다.
**지금은 골격 단계**입니다. 노드는 더미 응답만 하고, 해야 할 일은 코드 안에 `# TODO(agent):` 주석으로 적어 두었습니다.

- 설계 기준: Notion 「AI Agent 설계」(그래프·State), 「Harness 명세」, 「공통 계약서」(큐 메시지·SSE), 「MCP 설계」(도구 이름)
- 남은 일 찾기: `grep -rn "TODO(agent)" app prompts`

## 실행

```bash
cd agent
uv sync                                   # Python 3.12 가상환경 + 의존성
uv run pytest                             # 골격 테스트 (MCP·DB·큐 없이 통과)
uv run python -m app.cli --thread t1      # CLI 대화 (MAIN 모드)
uv run python -m app.cli --thread h1 --mode HOSPITAL --hospital-id 1   # "예약" 입력 → 승인 y/n (interrupt/resume)
uv run python -m app.cli --conditions '{"procedure_code":"JAW_BOTOX","date_from":"2026-10-20"}'  # planner 경로
uv run uvicorn app.api.main:app --reload --port 8000   # GET /health
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
MCP 코드는 `chore/mcp-skeleton` 브랜치(`mcp/`)에 있고, 도구는 **실제로 도구를 호출하는 시점에만** 불러오므로(lazy) 지금의 골격 테스트·CLI는 MCP 없이 동작합니다.

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
