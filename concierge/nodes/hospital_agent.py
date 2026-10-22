"""Hospital-scoped tool-calling agent; mutations remain proposals for approval."""

import json
import logging
import re
import time as monotonic_time
from uuid import uuid4
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
from concierge.nodes.actions import BOOK, HANDOFF, prepare_action
from concierge.nodes.load_hospital_context import selected_hospital, tool_data
from concierge.nodes.hospital_reply import message_text, patient_reply
from concierge.nodes.calendar_dates import request_calendar, clarification, validate_slot_dates, availability_only, slot_reply

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
HANDOFF_PROPOSAL_TOOL = {
    "name": HANDOFF,
    "description": "Display the consultation summary review form and connection-confirmation button. Call when the patient asks for a counselor or summary form, BEFORE asking for consent. This call only prepares a local approval card: it does NOT contact the hospital or submit a consultation. The application supplies the summary, hospital and conversation. Only the patient's later approval submits the request. Supports Korean, English, Chinese and Japanese.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
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


def _matching_booking_slots(booking, messages, hospital_id):
    if any(not booking.get(key) for key in ("date", "time", "procedure_code")):
        return []
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
    matching = []
    for slot in slots:
        if slot.get("status") != "AVAILABLE":
            continue
        start = datetime.fromisoformat(slot["start_at"])
        if start.tzinfo is None:
            continue
        start = start.astimezone(ZoneInfo("Asia/Seoul"))
        if start.date().isoformat() == booking["date"] and start.strftime("%H:%M") == booking["time"]:
            matching.append(slot["id"])
    return matching


def _validate_booking(args, booking, messages, hospital_id):
    if any(not booking.get(key) for key in ("date", "time", "procedure_code")):
        raise ValueError("Record explicit booking choices with record_booking_preferences first; ask only for choices the patient has not supplied")
    if args.get("procedure_code") != booking["procedure_code"]:
        raise ValueError("Reservation procedure does not match the patient's choice")
    if args.get("slot_id") not in _matching_booking_slots(booking, messages, hospital_id):
        raise ValueError("Look up available slots again and use a slot matching the chosen date/time/procedure")


def _action_finished(messages):
    # Resume messages have no approval ID: a task may reach only one approval.
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return False
        if isinstance(message, ToolMessage) and message.additional_kwargs.get("approval_completed"):
            return True
    return False


def requests_counselor_form(text: str) -> bool:
    text = text.strip().lower().replace("’", "'")
    if re.search(r"\b(?:don't|do not|not now|cancel|never mind)\b|(?:연결|상담).*(?:싫|취소|않|말아)|(?:보여|띄워|열어)\s*(?:주지|주지는|주진|주실 필요|말)", text):
        return False
    return bool(
        re.search(r"상담[^\n.!?]*(?:폼|카드)[^\n.!?]*(?:보여|띄워|열어)", text)
        or re.search(r"상담(?:사|원)[^\n.!?]*(?:연결해|연결해\s*주|이야기하고 싶|대화하고 싶)", text)
        or re.search(r"\b(?:i (?:want|would like|need) to|i'd like to|can i|could i|let me)\s+(?:talk|speak|chat)\s+(?:to|with)\s+(?:a |the |your |human )*(?:counselor|counsellor|advisor|agent)\b", text)
        or re.search(r"^(?:please )?connect me (?:to|with) (?:a |the |your |human )*(?:counselor|counsellor|advisor|agent)\b", text)
    )


async def hospital_agent(state: AgentState) -> dict:
    if state.get("mode") == "HUMAN":
        return {}
    messages = state.get("messages") or []
    if (messages and isinstance(messages[-1], ToolMessage)
            and messages[-1].status == "success"
            and messages[-1].additional_kwargs.get("approval_completed")
            and state.get("draft")):
        # Verified mutation results already have a localized, factual confirmation.
        return {"draft": state["draft"]}
    hospital_id = selected_hospital(state)
    context = state.get("hospital_context") or {}
    if context.get("hospital_id") != hospital_id:
        raise ValueError("Load the selected hospital context before running the agent")
    messages = list(state.get("messages") or [])
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    latest_user = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    calendar_scope = request_calendar(latest_user.content, today) if latest_user and isinstance(latest_user.content, str) else {}
    names = HOSPITAL_READ_TOOLS if _action_finished(messages) else (*HOSPITAL_READ_TOOLS, *DESTRUCTIVE_TOOLS)
    tools = [tool for tool in await get_tools(names) if tool.name in names]
    allowed = {tool.name for tool in tools}
    # An explicit request to open the review UI is not a mutation. Do not let
    # the model replace the real approval form with a prose imitation.
    latest = messages[-1] if messages else None
    if (HANDOFF in allowed and isinstance(latest, HumanMessage)
            and isinstance(latest.content, str)
            and requests_counselor_form(latest.content)):
        call = {"name": HANDOFF, "args": {}, "id": "handoff-" + str(uuid4())}
        pending = await prepare_action(state, call)
        call["args"] = pending["args"]
        return {"pending_action": pending, "draft": None,
                "messages": [AIMessage(content="", tool_calls=[call])]}
    if calendar_scope.get("clarify") and messages and isinstance(messages[-1], HumanMessage):
        return {"draft": clarification(calendar_scope, (state.get("user") or {}).get("locale", "en"))}
    if (isinstance(latest, ToolMessage) and latest.status == "success" and latest_user
            and isinstance(latest_user.content, str) and availability_only(latest_user.content)):
        calls = [c for m in messages if isinstance(m, AIMessage) for c in m.tool_calls
                 if c["id"] == latest.tool_call_id and c["name"] == "business_get_available_slots"]
        if calls:
            return {"draft": slot_reply(calls[-1]["args"], tool_data(latest),
                                       (state.get("user") or {}).get("locale", "en"))}
    plain_model = _model()
    added = []
    booking = dict(state.get("hospital_booking") or {})
    loop = dict(state.get("loop") or {})
    # A new patient message starts a new task budget, not a new conversation.
    turn = 0 if messages and isinstance(messages[-1], HumanMessage) else loop.get("turn", 0)
    while turn < MAX_TURNS:
        turn += 1
        payload = {
            "hospital_id": hospital_id,
            "mode": state.get("mode"),
            "today": today.isoformat(),
            "calendar_scope": calendar_scope,
            "locale": (state.get("user") or {}).get("locale", "en"),
            "hospital_context": context,
            "conditions": state.get("conditions") or {},
            "booking": booking,
            "summary": state.get("summary"),
        }
        # Do not let the model skip recording choices or the current-turn slot lookup.
        booking_ready = bool(_matching_booking_slots(booking, messages, hospital_id))
        available_tools = [tool for tool in tools if tool.name != BOOK or booking_ready]
        available_tools = [HANDOFF_PROPOSAL_TOOL if tool.name == HANDOFF else tool
                           for tool in available_tools]
        model = plain_model.bind_tools([*available_tools, PREFERENCES_TOOL], parallel_tool_calls=False)
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
                if call["name"] == "business_get_available_slots":
                    validate_slot_dates(args, calendar_scope)
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
