# MVP RAG

PostgreSQL + pgvector의 기존 `rag.documents` / `rag.chunks`를 사용합니다.
122개 문서(병원 FAQ 100개, 공통 22개)를 800자 이하로 분할하여 실제
`text-embedding-3-small` 임베딩을 저장합니다. 긴 섹션은 잘라 버리지 않고 여러 청크로 나눕니다.
원본 front matter와 가상 정책 출처도 DB에 보존합니다.

## 설치 및 적재

저장소 루트에서:

```bash
docker compose -f docker-compose.yml -f mcp/compose.rag.yml up -d postgres
docker compose -f docker-compose.yml -f mcp/compose.rag.yml run --rm db-seed
uv sync --project mcp
# DB 관리자의 연결 문자열을 환경변수에 설정합니다. 비밀번호를 저장소에 커밋하지 마세요.
# RAG_ADMIN_DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:15434/capstone
PYTHONPATH=mcp uv run --project mcp python -m rag_mcp.bootstrap
PYTHONPATH=mcp uv run --project mcp python -m rag_mcp.indexer
```

로컬 DB 포트는 15434입니다(`RAG_POSTGRES_PORT`로 변경 가능).
Compose override의 `!override`를 지원하는 Docker Compose 2.24.4 이상이 필요합니다.
모듈 실행 시 `PYTHONPATH=mcp`를 설정하거나 `cd mcp` 후 `uv run python -m ...`를 사용하세요.
루트 `.env`의 `OPENAI_API_KEY`, `EMBEDDING_MODEL`을 읽습니다.
bootstrap은 권한을 분리한 `rag_ro`, `rag_indexer`를 만들고,
Git에서 제외되는 `mcp/.env.rag`에 연결 설정을 기록합니다(권한 0600).
이미 해당 파일이나 계정이 있으면 덮어쓰지 않습니다.
기존 DB를 사용한다면 bootstrap 대신 해당 권한의 DSN을 직접 설정할 수 있습니다.

| 설정 | 용도 |
|---|---|
| `RAG_DATABASE_URL` | 검색 전용, `rag` 스키마 SELECT 권한 |
| `RAG_INDEX_DATABASE_URL` | 적재 전용, `rag` 테이블 변경 및 시퀀스 사용 권한 |
| `USE_STUB=false` | 실제 벡터 검색 선택 |
| `EMBEDDING_MODEL` | 적재·질의에 동일 모델 사용, 차원 1536 |

전체 스키마 생성은 기존 Flyway가 담당합니다. indexer는 업무 데이터를 변경하지 않습니다.
문서와 청크가 같으면 API 호출 없이 건너뛰며 변경된 문서만 트랜잭션으로 교체합니다.
원본에서 삭제한 문서는 자동 삭제하지 않습니다. 문서 폐기 시 별도 관리가 필요합니다.

## 검색 서버

```bash
cd mcp
MCP_HOST=127.0.0.1 uv run python -m rag_mcp.server
```

`http://127.0.0.1:9102/mcp`에서 기존 검색 도구를 제공합니다.
병원 검색은 SQL에서 `(hospital_id = 상담방병원 OR hospital_id IS NULL)`을
적용한 뒤 코사인 유사도를 계산하여 상위 결과를 반환합니다.
병원 미지정은 공통 문서만 검색합니다. 병원명은 원문/제목에 보존하며 식별은 ID를 씁니다.
이 규모에서는 정확 검색을 사용합니다(근사 벡터 인덱스 없음).

2026-10-20 로컬 검증 시 기존 9102 서버와의 충돌을 피하려고 새 벡터 서버는
`MCP_PORT=19102 MCP_HOST=127.0.0.1`로 실행했습니다.
실제 DB는 `127.0.0.1:15434/capstone`, 검색 주소는 `http://127.0.0.1:19102/mcp`입니다.
앱을 연결할 때는 agent의 실제 MCP 모드와 `RAG_MCP_URL`을 이 주소에 맞춰야 합니다.

병원 ID는 agent의 신뢰할 수 있는 상담방 state에서 주입해야 합니다.
MCP 자체는 외부 공개용 인증 서버가 아닙니다. `doc://` 원문 조회는 문서 ID를 받는
기존 내부 API이므로 사용자별 원문 접근 권한은 호출 계층에서 별도로 검증해야 합니다.
`USE_FAKE_TOOLS=true`인 agent는 자체 stub 프로세스를 사용하므로 이 서버로 자동 전환되지 않습니다.

## 검증

```bash
cd mcp
uv run pytest
RAG_INTEGRATION=1 uv run pytest tests/test_vector_rag.py
```

통합 테스트는 실제 DB에서 50개 병원 필터, 공통 검색, 원문·청크 대응,
재적재 중복 방지 및 읽기 전용 권한을 확인합니다.
테스트의 기존 벡터 재사용은 필터 검증용이며 다국어 검색 품질 평가를 대신하지 않습니다.
초기 적재 결과는 122문서 / 1,370청크이며 전체 테스트 26개가 통과했습니다.
실제 임베딩 질의로 1·2번 병원의 통역 질문을 한국어·영어·중국어·일본어로 호출해
각 병원의 신규 통역 FAQ가 상위 3개에 포함되는 것과 공통 준비 문서·원문 조회를 확인했습니다.
이는 샘플 확인 결과이며 전체 질문에 대한 검색 품질 보장은 아닙니다.
가격·시간은 업무 조회가 우선이며 교육용 문서를 의료 판단 근거로 사용하지 않습니다.

API 참고: [OpenAI embeddings](https://developers.openai.com/api/reference/resources/embeddings/methods/create),
[pgvector](https://github.com/pgvector/pgvector).
