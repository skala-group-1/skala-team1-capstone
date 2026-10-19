"""Harness — Tools 래퍼 (05 문서 Tools).

TODO(agent): MCP 도구 결과가 4,000자를 넘으면 자르고 "(truncated)" 표시
TODO(agent): ToolError 는 예외로 터뜨리지 말고 ToolMessage(status="error") 로 모델에 돌려주기
TODO(agent): 병원 서브그래프에서는 hospital_id 를 state.selected_hospital_id 로 강제 주입 (03 문서 4장)
TODO(agent): 모든 도구 결과를 state.tool_ledger 에 정규화 저장 (03 문서 9-3 Critic 대조용)
TODO(agent): 호출마다 x-acting-user-id, x-trace-id 헤더 전달 (04 문서 1장, LLM 인자에는 노출 금지)
"""

MAX_TOOL_RESULT_CHARS = 4000
