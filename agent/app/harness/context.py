"""Harness — Context (「Harness 명세」 Context).

TODO(agent): pre-model 훅 — 입력 토큰 예산 8k 초과 시 최근 6개 메시지만 남기고 나머지는 state.summary 로 요약
TODO(agent): conditions·선택 병원은 항상 system 메시지에 주입
TODO(agent): RAG chunk 는 상위 5개만
"""

INPUT_TOKEN_BUDGET = 8000
KEEP_RECENT_MESSAGES = 6
MAX_RAG_CHUNKS = 5
