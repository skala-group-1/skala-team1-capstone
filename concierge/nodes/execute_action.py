"""Execute only an approved proposal through the existing MCP boundary."""

import json

from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException

from app.graph.state import AgentState
from concierge.nodes.actions import BOOK, CANCEL, HANDOFF, lookup, validate_args
from concierge.nodes.load_hospital_context import selected_hospital

EXECUTE_ACTION_READY = True

HANDOFF_REPLY = {
    "en": "Your summary was shared with the hospital and a human consultation was requested.",
    "ko": "요약을 병원에 전달하고 상담사 연결을 요청했습니다.",
    "zh": "摘要已发送给医院，已申请人工咨询。",
    "ja": "要約を病院に共有し、相談員への接続を依頼しました。",
}


async def execute_action(state: AgentState) -> dict:
    action = state.get("pending_action") or {}
    if action.get("approved") is not True:
        raise ValueError("Explicit approval is required before mutation")
    hospital_id = selected_hospital(state)
    tool, args = action["tool"], action["args"]
    if action.get("hospital_id") != hospital_id:
        raise ValueError("Selected hospital changed after approval")
    validate_args(tool, args, hospital_id)
    if tool == HANDOFF and (args.get("consent") is not True
                            or args["conversation_id"] != state.get("conversation_id")):
        raise ValueError("Summary consent and the current conversation are required")
    update = {"pending_action": None}
    try:
        data = await lookup(tool, args)
        expected = {BOOK: {"PENDING", "CONFIRMED", "REJECTED", "EXPIRED", "CANCELLED"},
                    CANCEL: {"CANCELLED"}, HANDOFF: {"WAITING", "ACTIVE", "CLOSED"}}
        if type(data.get("id")) is not int or data["id"] <= 0 or data.get("status") not in expected[tool]:
            raise ValueError("Mutation result could not be verified")
        if tool == CANCEL and data["id"] != args["reservation_id"]:
            raise ValueError("Cancellation returned a different reservation")
        if data.get("hospital") and data["hospital"].get("id") != hospital_id:
            raise ValueError("Mutation returned a different hospital")
        if tool == HANDOFF:
            if data.get("status") == "CLOSED":
                raise ValueError("Consultation is already closed")
            update.update(mode="HUMAN", consultation_id=data["id"],
                          draft=HANDOFF_REPLY.get((state.get("user") or {}).get("locale"), HANDOFF_REPLY["en"]))
        content, status = json.dumps(data, ensure_ascii=False), "success"
    except Exception as exc:
        # Tool errors contain backend guidance/alternative slots, never fabricate success.
        detail = str(exc) if isinstance(exc, ToolException) else "The action result could not be confirmed."
        content = detail + " Do not claim success or automatically retry. For a slot conflict, look up fresh alternatives and ask the user to choose, then obtain new approval."
        status = "error"
    update["messages"] = [ToolMessage(content=content, tool_call_id=action["tool_call_id"], status=status)]
    return update
