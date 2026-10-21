"""SSE 이벤트 타입 (「공통 계약서」 6장). agent 는 ai.task.event 로 발행하고 backend 가 SSE 로 중계한다.

규칙: 한 작업의 마지막 이벤트는 반드시 DONE / FAILED / APPROVAL_REQUIRED 중 하나.
"""

from enum import StrEnum

from pydantic.alias_generators import to_camel


class SseEvent(StrEnum):
    STATUS = "STATUS"
    TOKEN = "TOKEN"
    TOOL_START = "TOOL_START"
    TOOL_END = "TOOL_END"
    CONDITIONS = "CONDITIONS"
    RESULT_CARDS = "RESULT_CARDS"
    CONVERSATION_OPENED = "CONVERSATION_OPENED"
    MODE_CHANGED = "MODE_CHANGED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    TRIP_PLAN = "TRIP_PLAN"
    MEMORY_PROPOSAL = "MEMORY_PROPOSAL"
    VERIFY = "VERIFY"
    DONE = "DONE"
    FAILED = "FAILED"


TERMINAL_EVENTS = frozenset({SseEvent.DONE, SseEvent.FAILED, SseEvent.APPROVAL_REQUIRED})


def camel(value):
    """Translate internal/MCP field names at the SSE boundary."""
    if isinstance(value, dict):
        return {to_camel(k): camel(v) for k, v in value.items()}
    if isinstance(value, list):
        return [camel(v) for v in value]
    return value


def state_events(update, state):
    """Only emit fields a node actually updated; never replay stale turn data."""
    if "conditions" in update or "missing" in update:
        yield SseEvent.CONDITIONS, {
            "conditions": camel(state.get("conditions") or {}),
            "missing": [to_camel(k) for k in state.get("missing") or []],
        }
    if "candidates" in update or "relax_options" in update:
        yield SseEvent.RESULT_CARDS, {
            "cards": camel(state.get("candidates") or []),
            "relaxOptions": camel(state.get("relax_options") or []),
        }
    if update.get("opened_conversation"):
        opened = update["opened_conversation"]
        yield SseEvent.CONVERSATION_OPENED, {
            "conversationId": opened["conversation_id"], "hospitalId": opened["hospital_id"],
        }
    if update.get("mode") == "HUMAN" and state.get("consultation_id"):
        yield SseEvent.MODE_CHANGED, {"mode": "HUMAN", "consultationId": state["consultation_id"]}
    if "trip_plans" in update:
        conditions = state.get("conditions") or {}
        yield SseEvent.TRIP_PLAN, {
            "arrivalDate": conditions.get("date_from"), "departureDate": conditions.get("date_to"),
            "plans": camel(update["trip_plans"]), "summary": state.get("trip_summary") or "",
        }
    if update.get("memory_proposal"):
        yield SseEvent.MEMORY_PROPOSAL, camel(update["memory_proposal"])
    if update.get("verify_passed") is not None:
        yield SseEvent.VERIFY, {
            "passed": update["verify_passed"], "attempts": state.get("verify_attempts", 0),
        }
