# mcp/ — business-mcp · rag-mcp

FastMCP 서버 2개 (04 MCP 설계 문서). agent 는 두 서버를 한 Client 에 붙여 도구명 접두어 `business_`, `rag_` 로 쓴다.

> **지금 상태: 골격.** 도구 이름·시그니처·description·힌트·오류 규칙은 확정본(04 문서) 기준으로 작성했고,
> 실제 로직은 `# TODO(mcp):` / `# TODO(rag):` 주석이 달린 곳을 채우면 된다.
> stub 모드는 `data/mock` 데이터를 실제로 돌려주므로 agent 담당은 지금 바로 붙여서 개발할 수 있다.

## 실행

```bash
cd mcp
uv sync                                   # Python 3.12 (.python-version)
uv run python -m business_mcp.server      # http://localhost:9101/mcp  (Streamable HTTP)
uv run python -m rag_mcp.server           # http://localhost:9102/mcp
uv run pytest                             # list_tools 스냅샷 + stub 도구 테스트
npx @modelcontextprotocol/inspector       # Inspector 에서 위 URL 로 접속해 도구 호출 (발표 증빙 캡처)
```

## 환경변수

| 이름 | 기본값 | 서버 | 설명 |
| --- | --- | --- | --- |
| `MCP_TRANSPORT` | `http` | 공통 | `http`(Streamable HTTP) / `stdio` |
| `MCP_PORT` | 9101 / 9102 | 공통 | http 포트 |
| `USE_STUB` | `true` | 공통 | business: mock JSON 으로 backend 흉내 / rag: mock Markdown 키워드 검색. **compose 최종본은 `false`** |
| `MOCK_DATA_DIR`, `RAG_DOCS_DIR` | 저장소의 `data/mock/...` 자동 탐색 | 공통 | 컨테이너에서 mock 경로 지정 |
| `BACKEND_INTERNAL_URL` | `http://localhost:8080/internal` | business | compose: `http://backend:8080/internal` |
| `SERVICE_TOKEN` | `.env` 값 | business | `X-Service-Token` 헤더 |
| `DEFAULT_ACTING_USER_ID` | `3` (customer.zh1) | business | stdio 처럼 헤더가 없을 때 쓸 사용자 |
| `DATABASE_URL` | `postgresql://rag_ro:...` | rag | 읽기 전용 계정, schema `rag` |
| `OPENAI_API_KEY`, `EMBEDDING_MODEL` | — / `text-embedding-3-small` | rag | 질의 임베딩 |
| `RAG_SCORE_THRESHOLD` | `0.2` | rag | 이 점수 미만 chunk 는 버림 → 0건이면 "No grounded document found" |

`.env` 는 저장소 루트의 것을 읽는다 (`mcp/` 에서 실행 기준 `../.env`).

## agent 연결 계약 (D-29)

- **fake 모드** (`USE_FAKE_TOOLS=true`): agent 가 두 서버를 **stdio 서브프로세스**로 띄운다.
  `MCP_TRANSPORT=stdio USE_STUB=true uv run --project mcp python -m business_mcp.server` (rag 도 동일).
  가짜 데이터는 여기 stub 한 곳에만 있으므로 agent 에 별도 `fake_tools.py` 를 두지 않는다.
- **실제 모드**: `BUSINESS_MCP_URL=http://business-mcp:9101/mcp`, `RAG_MCP_URL=http://rag-mcp:9102/mcp`.
- 호출자 정보는 LLM 인자가 아니라 MCP 요청 헤더로: `X-Acting-User-Id`, `X-Trace-Id`, (선택) `X-Locale`.
  business-mcp 가 그대로 backend `/internal/**` 헤더로 넘긴다. (헤더를 사용자별로 싣는 방식은 TODO — agent 담당과 합의)

## 도구 (12 + 2)

| 서버 | 도구 | 힌트 | backend / 데이터 |
| --- | --- | --- | --- |
| business | `normalize_procedure` | readOnly | `GET /internal/procedures/normalize` |
| business | `search_hospitals` | readOnly | `GET /internal/hospitals/search` |
| business | `get_hospital_detail` | readOnly | `GET /internal/hospitals/{id}?lite=true` |
| business | `list_doctors` | readOnly | `GET /internal/hospitals/{id}/doctors` |
| business | `get_price_options` | readOnly | `GET /internal/hospitals/{id}/prices` |
| business | `get_available_slots` | readOnly | `GET /internal/hospitals/{id}/slots` (최대 20) |
| business | `compare_hospitals` | readOnly | `POST /internal/hospitals/compare` (`procedureCode`) |
| business | `get_my_reservations` | readOnly | `GET /internal/reservations/mine` (12 계약서 기준, 04 문서와 다름) |
| business | `plan_trip` | readOnly | `POST /internal/trip-plans` |
| business | `create_reservation_request` | destructive·idempotent | `POST /internal/reservations` + `Idempotency-Key` |
| business | `cancel_reservation` | destructive·idempotent | `POST /internal/reservations/{id}/cancel` |
| business | `request_consultation` | destructive·idempotent | `POST /internal/consultations` |
| rag | `search_procedure_docs` | readOnly | 시술 가이드·공통 문서 |
| rag | `search_hospital_docs` | readOnly | 병원 FAQ |
| rag | Resource `doc://{doc_id}`, `doc://{doc_id}/sections/{section}` | — | 원문 / 섹션 원문 |

변경 도구는 agent 가 **승인 interrupt 후에만** 호출한다 (03 문서 4장). 도구를 추가·삭제하면 `tests/test_list_tools.py` 스냅샷과 agent 담당에게 공유.

## 구조

```
mcp/
├─ mcp_common/        casing(camel↔snake), paths(mock 위치), run(transport 선택)
├─ business_mcp/
│  ├─ server.py       도구 12개 (시그니처·docstring·힌트)
│  ├─ models.py       출력 Pydantic 모델 (12 계약서 DTO 의 snake_case 판)
│  ├─ context.py      acting user·trace id 헤더 읽기
│  ├─ backend_client.py  BackendClient 인터페이스 + HttpBackendClient(3s, 1회 재시도)
│  ├─ stub_backend.py    StubBackendClient (mock JSON 근사치 — backend 규칙 복제 금지)
│  └─ errors.py       ToolError 메시지 규칙
├─ rag_mcp/
│  ├─ server.py       검색 도구 2 + doc:// Resource
│  └─ store.py        DocStore 인터페이스 + StubDocStore + PgVectorStore(TODO)
└─ tests/
```

## 남은 일 (담당자용) — `grep -rn "TODO(" mcp/` 로 전체 확인

**MCP 담당**
- [ ] HttpBackendClient 를 backend 실제 응답으로 검증 (BE-13 이후 예약·상담, BE-14 이후 plan_trip)
- [ ] errors.py: 409 `CONCURRENT_UPDATE`·`INVALID_STATE_TRANSITION`·`CONSENT_REQUIRED` 문구
- [ ] acting user 헤더를 agent 가 어떻게 실을지 합의 (context.py)
- [ ] `idempotency_key` 를 agent 가 승인 시점에 만들어 넘기도록 합의
- [ ] 각 도구 오류 케이스 테스트, HttpBackendClient 테스트(httpx.MockTransport)
- [ ] Inspector 캡처 (발표 증빙)

**RAG 담당**
- [ ] `PgVectorStore` 구현 + `data/rag_docs/indexer.py` (섹션 청킹·임베딩·모델/차원 메타)
- [ ] `RAG_SCORE_THRESHOLD` 실측 후 확정, 다국어 질의 검색 품질 점검 (03 문서 예시 질문 10개)
- [ ] Resource 메타에 임베딩 모델·색인 시각 추가, (선택) Prompt `answer_with_citations`
