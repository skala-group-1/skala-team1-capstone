# AGENTS.md — AI 코딩 도구용 프로젝트 안내

AI 코딩 도구(Claude Code, Cursor, Codex 등)는 작업 전에 이 파일을 읽는다. 사람도 읽어도 된다.
기준 문서는 Notion "기획 v1" 허브이고, 이 파일은 그 요약이다. 내용이 다르면 Notion이 우선이다.

## 1. 프로젝트 한 줄 요약

외국인(영·중·일)이 모국어로 피부·성형 시술 정보를 얻고, 조건에 맞는 병원을 사실 기반으로 비교하고,
병원 상담사와 통역 채팅을 하고, 예약을 요청하는 웹 서비스. 로컬 실행 + Git 제출 과제.

## 2. 구조와 담당 폴더

| 폴더 | 역할 | 스택 |
| --- | --- | --- |
| `frontend/` | 화면 (최대폭 390px 앱 사이즈 웹) | Vue 3 + TypeScript + Vite + Pinia + vue-i18n |
| `backend/` | 인증·인가, 업무 규칙, DB 쓰기, `/api/**`, `/internal/**`, SSE, STOMP, 큐 | Spring Boot 3, Java 21 |
| `agent/` | LangGraph 에이전트, Harness, 번역 워커, `prompts/*.md` | Python, FastAPI, LangGraph 1.x |
| `mcp/business_mcp/` | 업무 조회·변경 도구 (backend `/internal` 호출) | Python, FastMCP |
| `mcp/rag_mcp/` | 문서 검색 도구 + `doc://` Resource | Python, FastMCP, pgvector |
| `data/mock/` | 가상 mock 데이터, RAG 문서, 생성기·검증기 | Python 표준 라이브러리 |
| `infra/`, `docker-compose.yml` | 실행 환경, RabbitMQ 정의 | Docker |

**작업 중인 파트의 폴더만 수정한다.** 다른 폴더를 고쳐야 하면 멈추고 사람에게 알린다.

## 3. 절대 규칙 (계층별 금지 사항, 평가 항목)

- frontend: 권한 판단 금지(표시용 라우트 가드만), agent 직접 호출 금지 → 항상 backend `/api/**`
- backend: LLM 호출 금지 (번역·AI는 RabbitMQ로 agent에 위임)
- agent: 업무 DB 직접 쓰기 금지 (변경은 MCP 도구 → backend). checkpointer·store용 `agent` 스키마만 사용
- business-mcp: 업무 규칙 복제 금지 (상태 전이·검증은 backend가 함)
- rag-mcp: 업무 데이터 변경 금지 (읽기 전용 계정)
- 변경 도구(예약 요청·취소·상담 요청)는 반드시 사람 승인(interrupt) 후 실행
- AI는 병원을 "추천"하거나 순위를 매기지 않는다. 조건에 맞는 병원을 사용자가 고른 기준으로 정렬만 한다
- 의료 판단·효과 보장 표현 금지. 가격·시간 같은 사실은 도구 결과에서만 인용

## 4. 계약 (필드명·API·enum)

- API·DTO·enum·오류 코드·큐 메시지·SSE 이벤트는 Notion **"공통 계약서"** 가 유일한 기준이다. 필드명을 바꾸거나 새로 지어내지 않는다.
- JSON은 camelCase. DB와 `data/mock/out/*.json`은 snake_case. Python MCP 도구 입출력은 snake_case.
- 일시는 ISO-8601 + `+09:00`, 금액은 정수 KRW(`priceKrw`), 업무 ID는 number, `conversationId`·`taskId`는 UUID 문자열.
- 오류 응답: `{ "code": "SLOT_UNAVAILABLE", "message": "...", "traceId": "...", "details": {} }`
- 모르는 값이 필요하면 추측하지 말고 질문한다.

## 5. 포트와 환경변수

| 서비스 | 포트 | 비고 |
| --- | --- | --- |
| frontend | 80 (개발 5173) | 공개 |
| backend | 8080 | 공개 |
| agent | 8000 | 내부 |
| business-mcp | 9101 (`/mcp`) | 내부 |
| rag-mcp | 9102 (`/mcp`) | 내부 |
| postgres (pgvector/pgvector:pg16) | 5432 | 스키마 app / agent / rag |
| rabbitmq | 5672, 관리 15672 | |

설정값은 전부 환경변수(`.env`, 예시는 `.env.example`). 키·비밀번호를 코드에 쓰지 않는다. `.env`는 커밋하지 않는다.
LLM은 `LLM_PRIMARY_MODEL`(현재 gpt-5-nano), 임베딩은 `EMBEDDING_MODEL`(text-embedding-3-small).

## 6. 데이터

- mock 데이터: `data/mock/out/*.json`, `schema.sql`, `V100__seed.sql` (기준일 2026-10-22 목요일 = 데모 시작일, seed 42)
- 데이터를 고칠 때는 JSON/SQL을 직접 수정하지 말고 `data/mock/generate.py`를 수정 → 재생성 → `python3 data/mock/validate.py` 통과
- 데모 계정 비밀번호 `Passw0rd!` (`password_hash`는 자리표시자, backend PasswordSeeder가 BCrypt로 교체)
- 다른 파트가 아직 없으면 `data/mock/out/*.json`을 읽는 stub/fake로 먼저 개발한다

## 7. 실행

```bash
cp .env.example .env
docker compose up -d postgres rabbitmq
docker compose run --rm db-seed          # Flyway로 스키마 + mock 데이터 적재 (backend 없이)
docker compose up -d --build backend     # 로그인이 필요하면 (PasswordSeeder가 데모 비밀번호를 채움)
python3 data/mock/validate.py
```

- DB 적재는 backend Flyway가 담당한다 (`schema.sql` → V1, backend 변경 → V2~V99, `V100__seed.sql` → V100).
- mock 데이터를 다시 생성했거나 예전 볼륨이 있으면 `docker compose down -v` 후 다시 적재한다 (Flyway 체크섬).
- RabbitMQ 큐는 backend가 기동 시 선언한다. 같은 큐를 다른 곳에서 선언하려면 인자를 완전히 같게 한다.

## 8. 작업 방식

1. Notion "작업 보드"의 카드 하나 = 작업 하나. 카드의 상세·완료 기준을 그대로 따른다.
2. 브랜치: `feat|fix|docs|chore|test/{파트}-{요약}` (카드에 적힌 이름 사용). main 직접 커밋 금지.
3. 먼저 변경할 파일 목록과 계획을 보여주고 확인을 받은 뒤 코드를 쓴다. 한 번에 파일 3~5개 이내.
4. 코드를 쓴 뒤 실행·테스트 방법을 알려주고, 가능하면 직접 실행해서 확인한다.
5. 커밋 메시지: `feat(be): 로그인 API 추가` 형식. AI 도구가 자동으로 붙이는 "Generated with…", "Co-Authored-By: (AI)" 줄은 넣지 않는다.
6. 끝나면 무엇을 바꿨는지 3줄 요약 (Notion 진행 보고에 붙여넣을 용도).

## 9. 버전 기준

Spring Boot 3.x / Java 21, Python 3.11+, LangGraph 1.x, LangChain 1.x, FastMCP, Vue 3, Node 20+.
라이브러리 API가 확실하지 않으면 지어내지 말고 공식 문서 확인을 요청한다.
