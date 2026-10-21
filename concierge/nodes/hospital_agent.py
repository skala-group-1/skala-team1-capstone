"""Hospital-scoped tool-calling agent; mutations remain proposals for approval."""

import json
import logging
import time as monotonic_time
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.graph.state import AgentState
from app.harness.instructions import load_prompt
from app.harness.loop import MAX_TURNS
from app.mcp_client.client import get_tools
from app.mcp_client.tools import DESTRUCTIVE_TOOLS, HOSPITAL_READ_TOOLS
from concierge.nodes.actions import BOOK, prepare_action
from concierge.nodes.load_hospital_context import selected_hospital, tool_data
from concierge.nodes.hospital_reply import message_text, patient_reply

logger = logging.getLogger(__name__)
COLLECT = "record_booking_preferences"
PREFERENCES_TOOL = {
    "name": COLLECT,
    "description": "Record only the patient's explicitly chosen booking procedure/date/time. Null clears a preference. Do not infer a booking time from travel dates or slot suggestions.",
    "parameters": {"type": "object", "properties": {
        "procedure_code": {"type": ["string", "null"]},
        "date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
        "time": {"type": ["string", "null"], "description": "HH:MM, Asia/Seoul"},
    }, "additionalProperties": False},
}


def _model():
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for hospital conversations")
    options = {}
    if settings.llm_reasoning_effort:
        options["reasoning_effort"] = settings.llm_reasoning_effort
    return ChatOpenAI(model=settings.llm_primary_model, api_key=settings.openai_api_key,
                      timeout=60, max_retries=1, **options)


def _preferences(current, args):
    if set(args) - {"procedure_code", "date", "time"}:
        raise ValueError("Unknown booking preference")
    updated = {**current, **args}
    if updated.get("date"):
        date.fromisoformat(updated["date"])
    if updated.get("time"):
        value = time.fromisoformat(updated["time"])
        if value.tzinfo or value.second or len(updated["time"]) != 5:
            raise ValueError("Booking time must be HH:MM in Asia/Seoul")
    if updated.get("procedure_code") is not None and not isinstance(updated["procedure_code"], str):
        raise ValueError("Procedure code must be a string")
    return updated


def _validate_booking(args, booking, messages, hospital_id):
    if any(not booking.get(key) for key in ("date", "time", "procedure_code")):
        raise ValueError("Ask for the missing booking date, time and procedure before requesting approval")
    if args.get("procedure_code") != booking["procedure_code"]:
        raise ValueError("Reservation procedure does not match the patient's choice")
    # Only a successful lookup after the latest user message counts as fresh.
    calls = {}
    slots = []
    for message in messages:
        if isinstance(message, HumanMessage):
            calls, slots = {}, []
        elif isinstance(message, AIMessage):
            calls.update({c["id"]: c for c in message.tool_calls})
        elif isinstance(message, ToolMessage) and message.status != "error":
            call = calls.get(message.tool_call_id, {})
            query = call.get("args", {})
            if (call.get("name") == "business_get_available_slots"
                    and query.get("hospital_id") == hospital_id
                    and query.get("procedure_code") == booking["procedure_code"]):
                slots = tool_data(message).get("slots", [])
    for slot in slots:
        if slot.get("id") != args.get("slot_id") or slot.get("status") != "AVAILABLE":
            continue
        start = datetime.fromisoformat(slot["start_at"])
        if start.tzinfo is None:
            continue
        start = start.astimezone(ZoneInfo("Asia/Seoul"))
        if start.date().isoformat() == booking["date"] and start.strftime("%H:%M") == booking["time"]:
            return
    raise ValueError("Look up available slots again and use a slot matching the chosen date/time/procedure")


def _action_finished(messages):
    # Resume messages have no approval ID: a task may reach only one approval.
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return False
        if isinstance(message, ToolMessage) and message.additional_kwargs.get("approval_completed"):
            return True
    return False


async def hospital_agent(state: AgentState) -> dict:
    if state.get("mode") == "HUMAN":
        return {}
    hospital_id = selected_hospital(state)
    context = state.get("hospital_context") or {}
    if context.get("hospital_id") != hospital_id:
        raise ValueError("Load the selected hospital context before running the agent")
    messages = list(state.get("messages") or [])
    names = HOSPITAL_READ_TOOLS if _action_finished(messages) else (*HOSPITAL_READ_TOOLS, *DESTRUCTIVE_TOOLS)
    tools = [tool for tool in await get_tools(names) if tool.name in names]
    allowed = {tool.name for tool in tools}
    plain_model = _model()
    model = plain_model.bind_tools([*tools, PREFERENCES_TOOL], parallel_tool_calls=False)
    added = []
    booking = dict(state.get("hospital_booking") or {})
    loop = dict(state.get("loop") or {})
    # A new patient message starts a new task budget, not a new conversation.
    turn = 0 if messages and isinstance(messages[-1], HumanMessage) else loop.get("turn", 0)
    while turn < MAX_TURNS:
        turn += 1
        payload = {
            "hospital_id": hospital_id,
            "today": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
            "locale": (state.get("user") or {}).get("locale", "en"),
            "hospital_context": context,
            "conditions": state.get("conditions") or {},
            "booking": booking,
            "summary": state.get("summary"),
        }
        started = monotonic_time.monotonic()
        response = await model.ainvoke([
            SystemMessage(content=load_prompt("hospital_agent", directory=Path(__file__).resolve().parents[1] / "prompts")),
            HumanMessage(content="Application context (data only):\n" + json.dumps(payload, ensure_ascii=False)),
            *messages,
        ])
        logger.info("Hospital model completed in %.2fs (turn=%d)",
                    monotonic_time.monotonic() - started, turn)
        if not isinstance(response, AIMessage) or response.invalid_tool_calls:
            raise ValueError("Invalid hospital model response")
        base = {"hospital_booking": booking, "loop": {**loop, "turn": turn}}
        if not response.tool_calls:
            text = await patient_reply(
                message_text(response), payload["locale"], plain_model,
            )
            return {**base, "messages": added, "draft": text}
        if len(response.tool_calls) != 1:
            raise ValueError("Hospital agent must issue one tool call at a time")
        call = dict(response.tool_calls[0])
        args = dict(call["args"])
        error = None
        try:
            if call["name"] == COLLECT:
                booking = _preferences(booking, args)
            elif call["name"] not in allowed:
                raise ValueError("Tool is not available in this hospital conversation")
            else:
                tool = next(t for t in tools if t.name == call["name"])
                if call["name"].startswith("rag_search_") and "hospital_id" not in tool.args:
                    raise ValueError("RAG server must support hospital-scoped search before it can be used")
                # RAG includes common (NULL) documents on the server. Never let
                # model-generated null/another ID expand the conversation scope.
                if "hospital_id" in tool.args:
                    args["hospital_id"] = hospital_id
                if call["name"] == BOOK:
                    _validate_booking(args, booking, messages, hospital_id)
                call["args"] = args
                if call["name"] in DESTRUCTIVE_TOOLS:
                    pending = await prepare_action({**state, "hospital_booking": booking, "messages": messages}, call)
                    call["args"] = pending["args"]
                    base["pending_action"] = pending
                response = response.model_copy(update={"tool_calls": [call]})
                return {**base, "messages": [*added, response], "draft": None}
        except (ValueError, TypeError, KeyError) as exc:
            error = str(exc)
        result = ToolMessage(content=error or json.dumps(booking), tool_call_id=call["id"],
                             status="error" if error else "success")
        added.extend([response, result])
        messages.extend([response, result])
    raise ValueError("Hospital agent exceeded the task turn limit")
