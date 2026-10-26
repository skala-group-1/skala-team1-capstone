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
- 기동 성공과 기능 완성은 별도입니다. agent 워커는 MAIN·HOSPITAL·AFTERCARE 대화와 승인 재개를 처리합니다.
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

## 평가 결과

Phase1 AI 코드 → 현재 AI 코드를 같은 입력·업무 서버·MCP·DB에서 비교했습니다. 숫자는 검증 결과서와 같습니다.

| 항목 | Phase1 → 현재 | 기준 |
| --- | --- | --- |
| AI 품질 · 문항 충족 | 15/20 → 20/20 (75% → 100%) | 목표 85% 이상. 문항별 3회 중 2회 이상 필수조건 충족 |
| AI 품질 · 응답 충족 | 46/60 → 58/60 (76.7% → 96.7%) | 120응답 개별 판정 |
| 영어 피부 고민 첫 질문 · 완료 p95 | 24.665 → 0.068초 (중앙값 12.485 → 0.016초) | 목표 p95 20% 이상 단축. 각 10회, 동시성 1 |
| 중국어 시술 방식 확인 · 완료 p95 | 23.568 → 5.141초 (중앙값 14.679 → 4.381초) | 같음 |
| 기능 회귀 | 에이전트 451 · 업무 API 67 · MCP 56 · 번역 23 통과, 화면 검사 6건 통과 | 모델·외부 도구 응답 고정 |
| 사후관리 위험 표현 분기 | 14/14 고정 안내, 일반 문의·부정 표현 8/8 일반 경로 | 고정 입력셋 |

- 평가셋 v2.1: 고정 20문항(답 가능 15 · 답 불가 2 · 실패 유도 3, en 15 · zh 3 · ja 2), 병원 1 FAQ(`HOSPITAL_FAQ_001` v1), seed 42
- 모델·프롬프트: `gpt-5-nano`, `P-PHASE1` → `P-FINAL-0.8` · 실행일 2026-10-23
- 개선 내용: 예약 정책 질문의 병원 FAQ 조회 누락 수정(#91)으로 Q-08·09·10·17 개선, 첫 질문 고정 분기·추론 설정 조정·중복 검수 축소·병렬 도구·스트리밍으로 응답 시간 단축(#65)

## 사용 기술 · 도구

- Frontend Vue 3 + TypeScript + Pinia + vue-i18n / Backend Spring Boot 3 (Java 21) / AI Python · FastAPI · LangGraph · FastMCP
- 저장소 PostgreSQL + pgvector, 큐 RabbitMQ, 실시간 SSE · STOMP, 모니터링 Prometheus · Grafana · Alloy · Loki (`infra/monitoring/`)
- 모델: 메인·병원 대화 `gpt-5-nano`(reasoning low), 사전·사후관리 `gpt-5.4-mini`, 임베딩 `text-embedding-3-small`
- AI 코딩 도구: [`AGENTS.md`](AGENTS.md)의 계층별 금지 규칙과 공통 계약을 따르도록 하고, 생성 코드는 테스트와 PR 리뷰로 확인한 뒤 병합

## 데이터 출처

- 업무 데이터(병원 50 · 시술 18 · 의사 159 · 가격 옵션 678 · 예약 가능 시간 26,928 · 후기 8,444 · 후기 번역 25,332)는
  모두 `data/mock/generate.py`가 만든 **가상 데이터**입니다(seed 42). 실제 병원·개인정보는 없습니다.
- RAG 문서 158개(`data/mock/rag_docs/`): 시술 가이드 18 · 공통 4 · 병원 FAQ 100 · 시술 전 준비 18 · 사후관리 18.
  모두 팀이 작성하거나 생성한 가상 문서이며 본문에 `Fictional educational content. Not medical advice.`를 표시합니다.
- 상세 생성 방법과 검증: [`data/mock/README.md`](data/mock/README.md)

## Team & Contribution

Phase 2(`phase1-end` 태그 이후) 병합 PR 기준입니다. 역할은 주담당이며 독점이 아닙니다.

| 이름 | 역할 | 담당 모듈 · 문서 | 주요 PR |
| --- | --- | --- | --- |
| 마영창 | R4 Backend · R3 Data | 사후관리 에이전트·대화방·09시 안내, 준비·관리 RAG 문서 36개, 후기 작성·번역 워커·시술 필터, 병원관리자 상담사·리뷰·병원 정보 관리 | [#50](https://github.com/skala-group-1/skala-team1-capstone/pull/50) [#54](https://github.com/skala-group-1/skala-team1-capstone/pull/54) [#60](https://github.com/skala-group-1/skala-team1-capstone/pull/60) [#63](https://github.com/skala-group-1/skala-team1-capstone/pull/63) [#66](https://github.com/skala-group-1/skala-team1-capstone/pull/66) [#90](https://github.com/skala-group-1/skala-team1-capstone/pull/90) 외 (20건) |
| 탁연우 | R5 Frontend · 발표자료 | `frontend/` 채팅·예약·상담·인증·직원 화면 UX와 접근성, 선택지 칩 표시, 발표자료 | [#57](https://github.com/skala-group-1/skala-team1-capstone/pull/57) [#64](https://github.com/skala-group-1/skala-team1-capstone/pull/64) [#67](https://github.com/skala-group-1/skala-team1-capstone/pull/67) [#77](https://github.com/skala-group-1/skala-team1-capstone/pull/77) 외 (12건) |
| 고두범 | R1 PM · R6 검증 | `infra/performance/` 성능 측정, `infra/monitoring/`, `docs/performance/`, 예약 정책 FAQ 조회 수정, 데모 영상 | [#81](https://github.com/skala-group-1/skala-team1-capstone/pull/81) [#82](https://github.com/skala-group-1/skala-team1-capstone/pull/82) [#83](https://github.com/skala-group-1/skala-team1-capstone/pull/83) [#91](https://github.com/skala-group-1/skala-team1-capstone/pull/91) 외 (5건) |
| 이준희 | R2 AI(흐름) | 메인 상담 흐름·유사 시술 탐색, 인계 로그·예약 가격·날짜 조회, 서비스 로고 | [#51](https://github.com/skala-group-1/skala-team1-capstone/pull/51) [#70](https://github.com/skala-group-1/skala-team1-capstone/pull/70) [#92](https://github.com/skala-group-1/skala-team1-capstone/pull/92) (3건) |
| 신동주 | R2 AI(흐름) | 메인 에이전트 응답 속도 개선, 선택지(`DONE.suggestions`) 전송, 데모 영상 | [#65](https://github.com/skala-group-1/skala-team1-capstone/pull/65) [#78](https://github.com/skala-group-1/skala-team1-capstone/pull/78) (2건) |
| 서정윤 | R2 AI(흐름) | 병원 진입 시 메인 상담 맥락 전달, 병원 대화 첫 안내 | [#73](https://github.com/skala-group-1/skala-team1-capstone/pull/73) (1건) |

## 알려진 한계

| 한계 | 원인 · 근거 | 다음 단계 |
| --- | --- | --- |
| 답 가능 45응답 중 출처 포함 15응답, 30응답은 `sources` 빈 배열 | 내용 판정과 출처 반환을 따로 집계했고, 출처 필수 검증이 없음 | 답 가능 응답의 출처 필수 검증 |
| Q-17(예약금)·Q-18(효과 보장 요구)은 3회 중 1회 미충족 | 응답마다 안내 문구 생성이 달라짐 | 고정 안내 문구·재검증 |
| 평가 범위가 병원 1곳 FAQ·20문항, 영어 위주 | 평가셋 v2.1 구성 | 다병원·다국어 평가셋 확장 |
| 응답 시간은 대표 2입력·각 10회·동시성 1 | 부하·동시 요청은 측정하지 않음 | 동시 요청 부하 측정 |
| 상담사 답변 초안·상담사 상태 관리·상담 품질 조회(TC-13~16)는 설계까지 | 이번 범위에서 업무 흐름·인수조건만 정의 | 구현 |
| 가상 데이터 기반, 실제 병원 시스템 연동 없음 | 교육용 데모 | 실제 병원 자료 적용 전 검증 |

## 협업 규칙

- `main` 직접 push 금지 → `feat/{part}-{요약}` 브랜치 + PR
- 커밋: `feat|fix|docs|chore(scope): 요약` (scope: fe, be, agent, mcp, rag, infra, data)
- `.env`는 커밋 금지
- mock 데이터는 JSON/SQL을 직접 고치지 말고 `data/mock/generate.py` 수정 → 재생성 → `validate.py` 통과 후 커밋
- API·DTO·enum을 바꾸면 Notion `12 공통 계약서`를 먼저 수정하고 팀에 공지
