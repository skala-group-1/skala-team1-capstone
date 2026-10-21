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


RESERVATION_REPLY = {
    "PENDING": ("Your reservation request was submitted and is awaiting hospital approval.",
                "예약 요청이 접수되었으며 병원 승인을 기다리고 있습니다.",
                "预约申请已提交，正在等待医院批准。", "予約リクエストを送信しました。病院の承認をお待ちください。"),
    "CONFIRMED": ("Your reservation is confirmed.", "예약이 확정되었습니다.",
                  "预约已确认。", "予約が確定しました。"),
    "REJECTED": ("The hospital declined your reservation request.", "병원이 예약 요청을 거절했습니다.",
                 "医院已拒绝您的预约申请。", "病院が予約リクエストをお断りしました。"),
    "EXPIRED": ("Your reservation request has expired.", "예약 요청이 만료되었습니다.",
                "预约申请已过期。", "予約リクエストの有効期限が切れました。"),
    "CANCELLED": ("Your reservation has been cancelled.", "예약이 취소되었습니다.",
                  "预约已取消。", "予約をキャンセルしました。"),
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
        else:
            locale = (state.get("user") or {}).get("locale", "en")
            locales = ("en", "ko", "zh", "ja")
            update["draft"] = RESERVATION_REPLY[data["status"]][locales.index(locale if locale in locales else "en")]
        content, status = json.dumps(data, ensure_ascii=False), "success"
    except Exception as exc:
        # Tool errors contain backend guidance/alternative slots, never fabricate success.
        detail = str(exc) if isinstance(exc, ToolException) else "The action result could not be confirmed."
        content = detail + " Do not claim success or automatically retry. For a slot conflict, look up fresh alternatives and ask the user to choose, then obtain new approval."
        status = "error"
    update["messages"] = [ToolMessage(content=content, tool_call_id=action["tool_call_id"], status=status,
                                      additional_kwargs={"approval_completed": True})]
    return update
