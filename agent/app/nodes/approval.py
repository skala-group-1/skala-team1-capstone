"""approval — 변경 도구 실행 전 고객 승인 (HITL interrupt)

- 입력 → 출력: 변경 도구 tool_call → interrupt(PendingAction) → resume {approved, editedArgs, reason}
- LLM/도구: 없음
- 근거: 03 문서 4장(승인 카드·재개), 12 문서 PendingAction·ApprovalRequest, SSE APPROVAL_REQUIRED, D-10
"""

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt

from app.graph.state import AgentState
from app.mcp_client.tools import DESTRUCTIVE_TOOLS, PENDING_ACTION_BY_TOOL


def approval(state: AgentState) -> dict:
    last = state["messages"][-1]
    assert isinstance(last, AIMessage)
    call = next(c for c in last.tool_calls if c["name"] in DESTRUCTIVE_TOOLS)

    # TODO(agent): display 는 사람이 읽는 형태로 (병원명·일시·시술·가격 옵션·전달될 정보), 사용자 locale
    # TODO(agent): 상담 요청은 니즈 요약 카드 + 개인정보 제공 동의 문구, editable=["note"] 등
    pending = {
        "action": PENDING_ACTION_BY_TOOL[call["name"]],
        "display": {"title": call["name"], "rows": [{"label": k, "value": str(v)} for k, v in call["args"].items()],
                    "notice": ""},
        "args": call["args"],
        "editable": ["note"],
    }
    decision = interrupt(pending)  # backend 가 ai.task.resume 으로 ApprovalRequest 를 넘겨줌

    approved = bool(decision.get("approved"))
    args = {**call["args"], **(decision.get("editedArgs") or {})}
    result = {"pending_action": {**pending, "tool": call["name"], "tool_call_id": call["id"], "args": args,
                                 "approved": approved}}
    if not approved:
        # 거절·수정 → hospital_agent 로 돌아감. tool_call 에 대응하는 ToolMessage 가 있어야 다음 LLM 호출이 깨지지 않음
        result["messages"] = [ToolMessage(content=f"User rejected: {decision.get('reason')}", tool_call_id=call["id"])]
    return result
