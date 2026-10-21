"""Only an explicit interrupt decision can authorize a prepared mutation."""

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt
from pydantic.alias_generators import to_camel

from app.graph.state import AgentState
from concierge.nodes.actions import EDITABLE, HANDOFF, SummaryCard, validate_args
from concierge.nodes.load_hospital_context import selected_hospital


REJECTION_REPLY = {
    "en": "You declined this action. No changes were made.",
    "ko": "요청을 거절했습니다. 변경된 사항은 없습니다.",
    "zh": "您已拒绝此操作，未进行任何更改。",
    "ja": "この操作を承認しませんでした。変更は行われていません。",
}


def approval(state: AgentState) -> dict:
    pending = state.get("pending_action") or {}
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or len(last.tool_calls) != 1:
        raise ValueError("Expected one prepared action")
    call = last.tool_calls[0]
    if pending.get("tool") != call["name"] or pending.get("tool_call_id") != call["id"]:
        raise ValueError("Action has not been prepared")
    hospital_id = selected_hospital(state)
    if pending["hospital_id"] != hospital_id:
        raise ValueError("Selected hospital changed during approval")
    validate_args(pending["tool"], pending["args"], hospital_id)
    display_payload = {k: pending[k] for k in ("action", "display", "args", "editable")}
    if pending["tool"] == HANDOFF:
        # UI DTO is camelCase; keep the approved MCP arguments in snake_case.
        display_payload["args"] = {to_camel(k): v for k, v in pending["args"].items()}
        display_payload["args"]["summaryCard"] = SummaryCard.model_validate(
            pending["args"]["summary_card"]).model_dump(by_alias=True)
    decision = interrupt(display_payload)
    error = None
    args = dict(pending["args"])
    approved = isinstance(decision, dict) and decision.get("approved") is True
    if approved:
        edits = decision.get("editedArgs")
        edits = {} if edits is None else edits
        if not isinstance(edits, dict) or set(edits) - set(EDITABLE[pending["tool"]]):
            error = "Approval edits contain fields that are not editable; request a new approval."
        else:
            args.update(edits)
            try:
                validate_args(pending["tool"], args, hospital_id)
            except ValueError as exc:
                error = str(exc)
        approved = error is None
    if approved and pending["tool"] == HANDOFF:
        args["consent"] = True
    if not approved:
        locale = (state.get("user") or {}).get("locale", "en")
        return {"pending_action": None, "draft": None if error else REJECTION_REPLY.get(locale, REJECTION_REPLY["en"]),
                "messages": [ToolMessage(
            content=error or "User rejected this action. Do not retry without a new user request.",
            tool_call_id=call["id"], status="error" if error else "success",
            additional_kwargs={"approval_completed": True})]}
    return {"pending_action": {**pending, "args": args, "approved": True}}
