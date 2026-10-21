# skala-team1-capstone

외국인이 모국어(영·중·일)로 피부·성형 시술 정보를 이해하고, 조건에 맞는 병원을 사실 기반으로 비교한 뒤,
AI 요약을 넘겨받은 실제 상담사와 통역 채팅하고 예약을 요청하는 B2B2C 서비스 (SKALA 1조 캡스톤).

> 기획·설계 문서(팀 기준 문서): Notion **기획 v1** 허브 — 개발 시작 전 `13 파트별 착수 가이드` → `12 공통 계약서` 순으로 읽기

## 구조 (모노레포)

| 경로 | 내용 | 스택 |
| --- | --- | --- |
| `frontend/` | 고객·상담사·병원관리자 웹 (앱 사이즈) | Vue 3 + Vite + Pinia |
| `backend/` | 인증·인가, 업무 API, `/internal/**`, SSE·STOMP, 큐 | Spring Boot 3 |
| `coordinator/` | 병원 선택 전 시술 정보·병원 탐색 조율, 역할별 프롬프트·테스트 | LangGraph (agent 런타임 공유) |
| `concierge/` | 선택 병원 상담·FAQ·예약 승인, 역할별 프롬프트·테스트 | LangGraph (agent 런타임 공유) |
| `agent/` | 공통 State·Harness·MCP·그래프 조립, API·AI 큐 워커·CLI | FastAPI + LangGraph |
| `summarizer/` | 인계용 대화 요약 카드 | FastAPI |
| `translator/` | 통역 채팅·요약 카드 번역 워커 | FastAPI + RabbitMQ |
| `mcp/business_mcp/` | 업무 조회·변경 도구 → backend `/internal` 호출 | FastMCP |
| `mcp/rag_mcp/` | 문서 검색 도구 + `doc://` Resource | FastMCP + pgvector |
| `data/mock/` | 가상 mock 데이터, RAG 문서, 생성기·검증기 | Python (표준 라이브러리) |
| `infra/` | compose 보조 설정 (RabbitMQ 정의 등) | |
| `tests/eval/` | 에이전트 평가셋 | |
| `scripts/` | 장애 시연·stub 스크립트 | |
| `docs/` | 평가 증빙(평가 결과, 스크린샷, harness.md) | |

## 빠른 시작 (전체 서비스)

```bash
cp .env.example .env            # 기존 .env가 있으면 덮어쓰지 말고 새 항목만 추가
# OPENAI_API_KEY, 서비스 토큰과 DB 연결 URL의 비밀번호 설정
docker compose up -d            # 처음에는 이미지 빌드, DB 권한 준비와 문서 색인도 실행
docker compose ps -a
docker compose exec postgres psql -U capstone -d capstone -c "select count(*) from app.hospitals;"   # 50
```

- 상시 서비스 9개: frontend·backend·agent·business-mcp·rag-mcp·translator·summarizer·postgres·rabbitmq.
  `db-access`와 `rag-index`는 일회성 작업이므로 `Exited (0)`이 정상입니다. 나머지는 `healthy`를 확인합니다.
- 접속: http://localhost (frontend), http://localhost:8080/swagger-ui (backend).
- 첫 색인과 실제 AI 질의에는 OpenAI API가 사용됩니다. 변경 없는 문서는 재색인 시 임베딩 호출을 생략합니다.
- `.env`의 `DATABASE_URL`은 `agent`, `RAG_DATABASE_URL`은 `rag_ro`, `RAG_INDEX_DATABASE_URL`은
  `rag_indexer` 계정을 사용합니다. Docker 호스트명은 `postgres`, DB명은 `POSTGRES_DB`와 맞춥니다.
  비밀번호의 URL 특수문자는 인코딩합니다. `db-access`는 기존 계정 비밀번호를 변경하지 않으며,
  기존 DB를 재사용한다면 해당 계정의 실제 비밀번호를 설정해야 합니다.
- 소스를 수정한 뒤에는 `docker compose up -d --build`로 이미지를 갱신합니다.
- 기동 성공과 기능 완성은 별도입니다. 현재 agent 웹 워커는 HOSPITAL 대화만 처리하며 MAIN 탐색,
  승인 후 실제 예약 저장과 상담사 인계 연결은 후속 작업입니다.
- **DB 스키마·mock 데이터는 Flyway가 적재**합니다 (V1 schema → V2.. → V100 seed). `postgres`만 띄우면 DB가 비어 있습니다.
  - backend를 같이 띄우면 자동 적재: `docker compose up -d postgres rabbitmq backend`
  - **backend 없이 DB만 채우기** (agent·MCP·RAG 담당): `docker compose up -d postgres rabbitmq && docker compose run --rm db-seed`
    - 데모 계정 비밀번호는 backend 기동 시에만 채워지므로, 로그인이 필요하면 backend를 띄우세요 (`/internal` 호출은 로그인 불필요)
- 내부 포트를 로컬 개발에 사용할 때만 `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`.
  DB 5432, RabbitMQ 5672·15672, agent 8000, MCP 9101·9102, translator 8001, summarizer 8002가
  `127.0.0.1`에 열립니다. RabbitMQ 관리 콘솔은 http://localhost:15672 입니다.
- 일반 재기동에는 볼륨을 유지합니다. mock 재생성으로 Flyway 체크섬이 바뀌었다면 데이터를 보존할지
  먼저 결정합니다. `docker compose down -v`는 기존 DB 전체를 삭제하므로 초기화할 때만 사용합니다.
- mock 데이터 설명: [`data/mock/README.md`](data/mock/README.md), backend 개발: [`backend/README.md`](backend/README.md)

## 데모 계정

비밀번호 공통 `Passw0rd!` (로컬 데모 전용). backend 기동 시 PasswordSeeder가 BCrypt 해시를 채웁니다.

| 역할 | 계정 |
| --- | --- |
| 고객 | `customer.en1` `customer.en2` `customer.zh1` `customer.zh2` `customer.ja1` `customer.ja2` `customer.ko1`(한국어) @demo.local |
| 상담사 (병원 1~3) | `counselor.h1` `counselor.h2` `counselor.h3` @demo.local |
| 병원관리자 (병원 1~3) | `admin.h1` `admin.h2` `admin.h3` @demo.local |
| 운영자 | `operator@demo.local` |

## 협업 규칙

- `main` 직접 push 금지 → `feat/{part}-{요약}` 브랜치 + PR
- 커밋: `feat|fix|docs|chore(scope): 요약` (scope: fe, be, agent, mcp, rag, infra, data)
- `.env`는 커밋 금지
- mock 데이터는 JSON/SQL을 직접 고치지 말고 `data/mock/generate.py` 수정 → 재생성 → `validate.py` 통과 후 커밋
- API·DTO·enum을 바꾸면 Notion `12 공통 계약서`를 먼저 수정하고 팀에 공지
