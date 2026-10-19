"""Harness — Observability (「Harness 명세」).

TODO(agent): trace_id = ai_task_id. 큐 헤더 x-trace-id → 그래프 config metadata → MCP 헤더까지 전파
TODO(agent): 구조화 JSON 로그 (INFRA-06 공통 포맷 확정 후 맞추기)
TODO(agent): LangSmith 메타데이터 — verify 통과율, planner 평균 도구 호출 수, trip-plan feasible 비율
"""
