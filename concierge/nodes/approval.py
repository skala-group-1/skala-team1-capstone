"""Only an explicit interrupt decision can authorize a prepared mutation."""

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt

from app.graph.state import AgentState
from concierge.nodes.actions import EDITABLE, HANDOFF, validate_args
from concierge.nodes.load_hospital_context import selected_hospital


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
    decision = interrupt({k: pending[k] for k in ("action", "display", "args", "editable")})
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
        return {"pending_action": None, "messages": [ToolMessage(
            content=error or "User rejected this action. Do not retry without a new user request.",
            tool_call_id=call["id"], status="error" if error else "success",
            additional_kwargs={"approval_completed": True})]}
    return {"pending_action": {**pending, "args": args, "approved": True}}
