"""Harness — Recovery (「Harness 명세」).

TODO(agent): LLM 호출 래퍼 — 429·503 은 2회 재시도(1s, 3s 지수 백오프) → LLM_FALLBACK_MODEL → 실패 시 FAILED + trace 링크
TODO(agent): 테스트 — 모킹된 429 → 대체 모델 전환 확인
큐 작업 재시도(2회 → DLQ)는 workers/ 와 RabbitMQ 정의(INFRA-02)가 담당.
"""

RETRY_BACKOFF_SECONDS = (1, 3)
