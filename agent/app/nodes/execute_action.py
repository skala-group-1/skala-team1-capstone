"""execute_action — 승인된 변경 도구 실행 (예약 요청 / 예약 취소 / 상담 요청)

- 입력 → 출력: pending_action(approved) → ToolMessage, (상담 요청 성공 시) mode=HUMAN
- LLM/도구: business_create_reservation_request / business_cancel_reservation / business_request_consultation
- 근거: 03 문서 4장, 04 문서 2장 변경 도구, D-09·D-10
"""

from langchain_core.messages import ToolMessage

from app.graph.state import AgentState


def execute_action(state: AgentState) -> dict:
    action = state["pending_action"]
    # TODO(agent): mcp_client 로 action["tool"] 을 action["args"] 로 실제 호출 (idempotency_key 유지)
    # TODO(agent): SLOT_UNAVAILABLE 등 ToolError 는 대안 슬롯과 함께 hospital_agent 로 돌려주기
    # TODO(agent): request_consultation 성공 시 mode=HUMAN + SSE MODE_CHANGED {mode, consultationId}
    content = f"[execute_action 골격] {action['tool']} 실행됨"
    return {"messages": [ToolMessage(content=content, tool_call_id=action["tool_call_id"])], "pending_action": None}
