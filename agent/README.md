# agent — 공통 LangGraph 실행 기반

병원 선택 전 탐색은 [`coordinator/`](../coordinator/README.md), 선택 병원 상담은
[`concierge/`](../concierge/README.md)에서 노드·프롬프트·역할별 테스트를 관리합니다.
이 폴더는 두 역할의 공통 State·Harness·MCP 연결·그래프 조립·API·큐 워커·CLI와 의존성을 관리합니다.
요약·번역은 기존 `summarizer/`, `translator/` 서비스가 담당합니다.

역할별 코드를 분리했으며 실행 프로세스는 기존과 같습니다. 로컬 실행은 `PYTHONPATH=..`로
저장소 루트의 역할 패키지를 읽습니다. 별도 가상환경이나 큐 소비자를 역할마다 만들지 않습니다.
그래프 노드 이름·State·큐/SSE 계약·승인 흐름도 유지합니다.

- 설계 기준: Notion 「AI Agent 설계」(그래프·State), 「Harness 명세」, 「공통 계약서」(큐 메시지·SSE), 「MCP 설계」(도구 이름)
- 남은 일 찾기: `rg -n "TODO\\(agent\\)" app prompts ../coordinator ../concierge`

## 병원 상세 → concierge 웹 채팅

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
uv sync --frozen                          # Python 3.12 가상환경 + 의존성
uv run --frozen pytest                    # 단위·그래프 테스트 (MCP·DB·큐 없이 실행)
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

## CLI 대화·승인 복원

`DATABASE_URL`을 설정하면 checkpointer와 store 모두 연결의 `search_path`를 `agent`로
고정하고 해당 스키마·테이블을 준비합니다. 기존 `agent` 스키마 사용·테이블 생성 권한이
필요하며 스키마가 없다면 DB의 스키마 생성 권한도 필요합니다. 연결·권한·마이그레이션
오류는 그대로 실패하며 메모리 저장으로 자동 전환하지 않습니다. 기존 `public` 스키마에
잘못 저장된 체크포인트는 자동 이동하지 않습니다.

```bash
cd agent
# DATABASE_URL은 환경변수 또는 루트 .env에 설정 (접속 문자열/비밀번호를 커밋하지 않음)
PYTHONPATH=.. uv run --frozen python -m app.cli --thread h1 --user 3 --locale zh --mode HOSPITAL --hospital-id 1
# APPROVAL_REQUIRED에서 Ctrl-D 또는 프로세스 종료 후, 같은 thread/user로 재실행
PYTHONPATH=.. uv run --frozen python -m app.cli --thread h1 --user 3
```

재실행하면 저장된 메시지·사용자·언어·모드·병원·조건을 복원하고, 새 메시지를 받기 전에
대기 중인 승인 카드를 표시합니다. `y`는 승인, `n`은 거절이며 다른 입력은 재질문합니다.
승인 프롬프트에서 Ctrl-D/Ctrl-C는 결정 없이 종료합니다. `--user-id`도 같은 옵션입니다.
기존 대화에 다른 사용자 또는 다른 초기 설정을 지정하면 읽은 대화 내용을 출력하거나
변경하지 않고 종료합니다. 설정 변경은 새 `--thread`로 시작합니다. 승인 대기가 아닌
미완료 실행은 새 입력으로 덮어쓰지 않고 오류를 알립니다.

CLI의 사용자 번호 검사는 로컬 실수 방지용이며 인증을 대신하지 않습니다. 웹 요청의
사용자·대화 권한은 backend가 담당합니다. `DATABASE_URL`이 비어 있으면 개발용 메모리
저장소를 사용하므로 프로세스 종료 후 복원되지 않습니다. 같은 thread를 여러 CLI에서
동시에 조작하지 않습니다. 저장·복원은 새로운 업무 변경 권한을 부여하지 않으며,
예약·취소·상담 실행은 그래프의 interrupt 승인과 MCP 경계를 그대로 따릅니다.
실제 MCP 호출에는 지정 사용자·복원된 언어·요청 추적 UUID를 전달합니다. 실제 backend에
연결할 때 `--thread`는 그 사용자의 기존 대화 UUID를 사용합니다(`h1`은 로컬 예시).
새 메시지마다 `task_id` UUID와 `conversation_id=thread_id`를 state에 전달하고,
승인 재개는 저장된 작업을 그대로 이어갑니다(공통 State에 해당 필드 등록 필요).

```bash
uv run --frozen pytest -q tests/test_memory.py tests/test_cli.py
# 격리된 빈 PostgreSQL DB만 사용: 모든 사용자 테이블이 agent 스키마인지도 검사
# AGENT_TEST_DATABASE_URL을 설정한 터미널에서 실행 (미설정 시 이 테스트만 skip)
uv run --frozen pytest -q -s tests/test_cli.py::test_postgres_cli_restart_in_separate_processes
```

실제 PostgreSQL 테스트는 결정적 중첩 그래프를 CLI에 연결합니다. 승인 대기 프로세스를
강제 종료한 뒤 별도 프로세스에서 각각 승인·거절하고, 메시지·store 지속과 사용자·대화
분리를 확인합니다. LLM·MCP·RabbitMQ와 업무 DB 쓰기는 실행하지 않으므로 이 테스트는
실제 예약 접수의 검증이 아닙니다. 테스트용 사용자 3의 프로필과 UUID thread가 남으므로
테스트가 끝나면 전용 DB를 폐기합니다.

## 가짜 도구 (D-31)

agent 안에 별도의 가짜 도구를 만들지 않습니다. `USE_FAKE_TOOLS=true`면 `app/mcp_client/client.py`가
**business-mcp·rag-mcp를 stdio 하위 프로세스로 직접 띄우고 `USE_STUB=true`**(mock JSON 응답)로 연결합니다.
그래서 처음부터 실제 MCP 도구 이름·스키마로 개발되고, 나중에 `USE_FAKE_TOOLS=false`로 바꾸면 compose의 HTTP 서버로 넘어갑니다.
MCP 코드는 `mcp/`에 있습니다. 도구 목록은 처음 필요한 시점에 불러옵니다(lazy).
단위 테스트는 외부 서비스 없이 실행하지만 병원 CLI 대화에는 LLM 키와 MCP 실행 환경이 필요합니다.

## 폴더 구조

```text
coordinator/
├─ nodes/                  탐색·조건·가드·기억·검증·인계 노드
├─ prompts/                coordinator, guard_input, extract_conditions, ask_clarify, rag_answer
└─ tests/                  탐색 도구 루프·조건·인계 요약
concierge/
├─ nodes/                  병원 상담·컨텍스트·응답 검증·조회 도구·승인·변경 실행
├─ prompts/                hospital_agent
└─ tests/                  병원 상담·RAG·큐 워커
agent/
├─ app/
│  ├─ config.py            공통 환경변수
│  ├─ graph/               State·분기·두 역할 그래프 조립
│  ├─ nodes/respond.py     공통 응답 마무리
│  ├─ mcp_client/          MCP 연결·도구 이름 상수
│  ├─ harness/             반복 한도·메모리·프롬프트 로더 등
│  ├─ workers/             큐 계약·AI 작업 소비·SSE 이벤트 발행
│  ├─ api/main.py          FastAPI /health (8000)·병원 채팅 진입점
│  └─ cli.py               CLI 러너
├─ prompts/                공통 system_base와 기존 요약·번역 템플릿
├─ tests/                  통합 그래프·계약·Harness·MCP 컨텍스트
├─ pyproject.toml          공통 의존성·세 폴더의 pytest 수집 설정
└─ Dockerfile              저장소 루트 context로 세 폴더를 함께 복사
```

전체 테스트는 `cd agent && uv run --frozen pytest -q`로 실행합니다.
역할만 확인할 때는 `uv run --frozen pytest -c pyproject.toml ../coordinator/tests -q` 또는
`uv run --frozen pytest -c pyproject.toml ../concierge/tests -q`를 사용합니다.

Docker에서도 `/app/{agent,coordinator,concierge}`로 같은 배치를 유지합니다.
저장소 루트에서 `docker build -f agent/Dockerfile -t capstone-agent .`로 빌드합니다.

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

## 남은 구현 위치

- `coordinator/nodes/`: 입력·조건 추출의 LLM 연결, 외부 시술 정보 검색, 검증·프로필 기억, 병원 대화 생성
- `concierge/nodes/`: `execute_action`의 실제 변경 도구 연결, 상담사 인계·취소 연동
- `agent/app/workers/`: MAIN 작업 연동 (현재 소비자는 HOSPITAL만 처리)
- `agent/app/harness/`: 미구현 Harness 항목과 평가셋

남은 기능은 각 파일의 `TODO(agent)`를 기준으로 확인합니다.
