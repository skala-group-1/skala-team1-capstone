# summarizer — 공용 요약 에이전트 (내부 HTTP API)

대화 요약 카드("상담 요청 요약")를 만드는 독립 컨테이너입니다. 메인→서브 인계(HANDOFF_TO_SUB)와
서브→사람 상담사 인계(NEEDS_CARD) 두 경우 모두 **같은 폼**을 씁니다.

- `POST /summarize` (포트 8002, 내부 전용) — 메인·서브 에이전트의 그래프 노드가 동기 호출
  - 요청: `{purpose, messages: [{role, content}], locale, conditions?}`
  - 응답: `{summaryCard: {procedure, preferredDates, stayDays, budget, questions, customerLocale}, text}`
    (필드명은 `frontend/src/types/contract.ts` 의 SummaryCard 와 1:1)
- 대화·conditions 에서 확인되는 값은 빠짐없이 채우고, 확인 안 되는 값만 null (지어내기 금지)
- conditions 가 오면 시술 코드·체류일·예산은 LLM 요약보다 **코드로 우선 적용**
- `customerLocale` 은 항상 요청의 `locale` (사용자 프로필 언어, 대화에서 추측 금지)
- `text` 는 카드 외 맥락 3문장 이내 — HANDOFF_TO_SUB 는 영어, NEEDS_CARD 는 사용자 locale
- 상담사용 한국어 번역은 여기서 하지 않는다 (backend 가 `summary.translate` 큐로 translator 에 위임)

## 실행

```bash
cd summarizer
uv sync && uv run pytest                  # 테스트 (LLM 없이 통과)
uv run uvicorn app.main:app --reload --port 8002

# compose
docker compose up -d --build summarizer
```

환경변수는 저장소 루트 `.env` 를 읽습니다: `OPENAI_API_KEY`, `LLM_FAST_MODEL`(기본 gpt-5-nano),
`GLOSSARY_PATH`(컨테이너에서는 Dockerfile 이 지정).
