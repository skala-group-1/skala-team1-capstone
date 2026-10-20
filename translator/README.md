# translator — 공용 번역 에이전트 (RabbitMQ 워커)

상담사↔고객 통역 채팅 실시간 번역과 상담 요약 카드의 한국어 번역을 맡는 독립 컨테이너입니다.

- 소비: `chat.translate`, `summary.translate` / 발행: `chat.translated`, `summary.translated`
  (exchange `capstone.direct`, routing key = 큐 이름, 헤더 `x-trace-id`·`x-attempt`, body camelCase JSON)
- 번역은 LLM 1회 호출 (`LLM_FAST_MODEL`, structured output 으로 의료질문 분류까지 같이),
  숫자·날짜·금액 검증은 코드(정규식)로 → `NUMBER_MISMATCH` / `MEDICAL_QUESTION` 플래그
- 용어집 `data/mock/out/glossary.json` 을 기동 시 로드, **원문에 등장하는 용어만** 프롬프트에 주입
- 번역 방향은 메시지의 `from`→`to` 를 그대로 따른다 (`to` 는 backend 가 사용자 프로필 언어 또는 ko 로 채움).
  `from == to` 면 LLM 호출 없이 원문 그대로 반환
- 큐·exchange 는 선언하지 않는다 (backend 가 기동 시 선언). 실패 시 `x-attempt` 에 따라
  `{큐}.retry.5s` → `{큐}.retry.15s` → `{큐}.dlq` (backend RetryRepublisher 와 같은 규약)

## 실행

```bash
cd translator
uv sync && uv run pytest                  # 테스트 (LLM·RabbitMQ 없이 통과)
uv run uvicorn app.main:app --reload --port 8001   # GET /health (RabbitMQ 필요)

# compose (backend 가 큐를 선언한 뒤에 떠야 한다 → depends_on 에 반영돼 있음)
docker compose up -d --build translator
```

환경변수는 저장소 루트 `.env` 를 읽습니다: `OPENAI_API_KEY`, `LLM_FAST_MODEL`(기본 gpt-5-nano),
`RABBITMQ_URL`, `GLOSSARY_PATH`(컨테이너에서는 Dockerfile 이 지정).
