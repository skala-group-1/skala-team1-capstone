# skala-team1-capstone

외국인이 모국어(영·중·일)로 피부·성형 시술 정보를 이해하고, 조건에 맞는 병원을 사실 기반으로 비교한 뒤,
AI 요약을 넘겨받은 실제 상담사와 통역 채팅하고 예약을 요청하는 B2B2C 서비스 (SKALA 1조 캡스톤).

> 기획·설계 문서(팀 기준 문서): Notion **기획 v1** 허브 — 개발 시작 전 `13 파트별 착수 가이드` → `12 공통 계약서` 순으로 읽기

## 구조 (모노레포)

| 경로 | 내용 | 스택 |
| --- | --- | --- |
| `frontend/` | 고객·상담사·병원관리자 웹 (앱 사이즈) | Vue 3 + Vite + Pinia |
| `backend/` | 인증·인가, 업무 API, `/internal/**`, SSE·STOMP, 큐 | Spring Boot 3 |
| `agent/` | LangGraph 에이전트, Harness, 번역 워커, `prompts/*.md` | FastAPI + LangGraph |
| `mcp/business_mcp/` | 업무 조회·변경 도구 → backend `/internal` 호출 | FastMCP |
| `mcp/rag_mcp/` | 문서 검색 도구 + `doc://` Resource | FastMCP + pgvector |
| `data/mock/` | 가상 mock 데이터, RAG 문서, 생성기·검증기 | Python (표준 라이브러리) |
| `infra/` | compose 보조 설정 (RabbitMQ 정의 등) | |
| `tests/eval/` | 에이전트 평가셋 | |
| `scripts/` | 장애 시연·stub 스크립트 | |
| `docs/` | 평가 증빙(평가 결과, 스크린샷, harness.md) | |

## 빠른 시작 (현재: 인프라 + backend)

```bash
cp .env.example .env            # OPENAI_API_KEY 등 입력
docker compose up -d --build    # postgres(pgvector) + rabbitmq + backend
docker compose exec postgres psql -U capstone -d capstone -c "select count(*) from app.hospitals;"   # 50
```

- **DB 스키마·mock 데이터는 Flyway가 적재**합니다 (V1 schema → V2.. → V100 seed). `postgres`만 띄우면 DB가 비어 있습니다.
  - backend를 같이 띄우면 자동 적재: `docker compose up -d postgres rabbitmq backend`
  - **backend 없이 DB만 채우기** (agent·MCP·RAG 담당): `docker compose up -d postgres rabbitmq && docker compose run --rm db-seed`
    - 데모 계정 비밀번호는 backend 기동 시에만 채워지므로, 로그인이 필요하면 backend를 띄우세요 (`/internal` 호출은 로그인 불필요)
- Swagger: http://localhost:8080/swagger-ui (로그인 응답의 `accessToken`을 Authorize에 입력)
- RabbitMQ 관리 콘솔: http://localhost:15672 (guest/guest)
- DB 재적재 / mock 재생성 후: `docker compose down -v && docker compose up -d --build` (seed 파일이 바뀌면 Flyway 체크섬이 달라져 기존 볼륨으로는 기동 실패)
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
