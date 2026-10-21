"""Prepare immutable, hospital-scoped proposals before the approval checkpoint."""

import json
from uuid import NAMESPACE_URL, uuid5

import httpx
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from pydantic.alias_generators import to_camel

from app.config import get_settings
from app.mcp_client.client import get_tools
from app.mcp_client.tools import PENDING_ACTION_BY_TOOL
from concierge.nodes.load_hospital_context import selected_hospital, tool_data
from concierge.nodes.action_display import label, price_rows, procedure_name, row, summary_rows

BOOK = "business_create_reservation_request"
CANCEL = "business_cancel_reservation"
HANDOFF = "business_request_consultation"
EDITABLE = {BOOK: ["note"], CANCEL: ["reason"], HANDOFF: []}
ARGUMENTS = {
    BOOK: {"hospital_id", "slot_id", "procedure_code", "price_option_id", "note", "idempotency_key"},
    CANCEL: {"reservation_id", "reason"},
    HANDOFF: {"hospital_id", "conversation_id", "summary_card", "consent", "idempotency_key"},
}


class SummaryCard(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")
    procedure: StrictStr | None = None
    preferred_dates: StrictStr | None = None
    stay_days: StrictInt | None = Field(default=None, ge=1)
    budget: StrictStr | None = None
    questions: list[StrictStr] = Field(default_factory=list)
    customer_locale: StrictStr


async def lookup(name, args):
    tools = {tool.name: tool for tool in await get_tools((name,))}
    if name not in tools:
        raise ValueError(f"Required MCP tool unavailable: {name}")
    data = tool_data(await tools[name].ainvoke(args))
    if not isinstance(data, dict) or data.get("error") or data.get("isError"):
        raise ValueError("MCP lookup did not return a successful result")
    return data


async def summarize(state):
    locale = (state.get("user") or {}).get("locale", "en")
    if locale not in ("en", "zh", "ja"):
        raise ValueError("Summary service supports en, zh and ja only")
    # Only customer statements are evidence of needs; AI prose can contain mistakes.
    messages = [{"role": "user", "content": m.content} for m in state.get("messages", [])
                if isinstance(m, HumanMessage) and isinstance(m.content, str)]
    conditions = {to_camel(k): v for k, v in (state.get("conditions") or {}).items()}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(get_settings().summarizer_url.rstrip("/") + "/summarize", json={
            "purpose": "NEEDS_CARD", "messages": messages, "locale": locale, "conditions": conditions,
        })
        response.raise_for_status()
        card = SummaryCard.model_validate(response.json()["summaryCard"])
    if card.customer_locale != locale or not card.procedure:
        raise ValueError("Confirm the procedure and summary language before requesting consultation")
    return card.model_dump()


def validate_args(tool, args, hospital_id):
    if tool not in ARGUMENTS or set(args) - ARGUMENTS[tool]:
        raise ValueError("Unsupported action arguments")
    if tool != CANCEL and args.get("hospital_id") != hospital_id:
        raise ValueError("Action cannot change the selected hospital")
    for key in ("hospital_id", "slot_id", "price_option_id", "reservation_id"):
        if key in args and args[key] is not None and (type(args[key]) is not int or args[key] <= 0):
            raise ValueError(f"Invalid {key}")
    for key in EDITABLE[tool]:
        if args.get(key) is not None and not isinstance(args[key], str):
            raise ValueError(f"Invalid {key}")
    if tool == BOOK and (not args.get("slot_id") or not isinstance(args.get("procedure_code"), str)
                         or not args["procedure_code"]):
        raise ValueError("Reservation requires a slot and procedure")
    if tool == CANCEL and not args.get("reservation_id"):
        raise ValueError("Cancellation requires a reservation")
    if tool in (BOOK, HANDOFF) and not args.get("idempotency_key"):
        raise ValueError("An application-generated idempotency key is required")
    if tool == HANDOFF:
        if not args.get("conversation_id"):
            raise ValueError("Consultation requires the current conversation")
        SummaryCard.model_validate(args.get("summary_card"))


async def prepare_action(state, call):
    tool = call["name"]
    hospital_id = selected_hospital(state)
    args = dict(call["args"])
    if tool not in ARGUMENTS or set(args) - ARGUMENTS[tool]:
        raise ValueError("Unsupported action arguments")
    if tool != CANCEL:
        args["hospital_id"] = hospital_id
        # Stable even when a checkpointed proposal is replayed after a process crash.
        identity = [state.get("conversation_id"), (state.get("user") or {}).get("user_id"),
                    state.get("task_id"), call["id"], hospital_id, tool]
        args["idempotency_key"] = str(uuid5(NAMESPACE_URL, json.dumps(identity)))
    detail = (state.get("hospital_context") or {}).get("detail") or {}
    locale = (state.get("user") or {}).get("locale", "en")
    rows = [row("hospital", detail.get("name"), locale)]
    notice = ""
    if tool == BOOK:
        validate_args(tool, args, hospital_id)
        query = {"hospital_id": hospital_id, "procedure_code": args["procedure_code"]}
        doctors = (await lookup("business_list_doctors", query))["doctors"]
        prices = (await lookup("business_get_price_options", query))["options"]
        booking = state.get("hospital_booking") or {}
        slots = await lookup("business_get_available_slots", {
            **query, "date_from": booking["date"], "date_to": booking["date"],
        })
        from concierge.nodes.hospital_agent import _validate_booking
        from langchain_core.messages import ToolMessage
        evidence = [AIMessage(content="", tool_calls=[{"name": "business_get_available_slots",
                     "args": query, "id": "approval-slots"}]),
                    ToolMessage(content=json.dumps(slots), tool_call_id="approval-slots")]
        _validate_booking(args, booking, evidence, hospital_id)
        slot = next(s for s in slots["slots"] if s["id"] == args["slot_id"])
        doctor = next((d for d in doctors if d["id"] == slot.get("doctor_id")), None)
        if doctor is None:
            raise ValueError("The slot doctor could not be verified for this procedure")
        price = next((p for p in prices if p["id"] == args.get("price_option_id")), None)
        if args.get("price_option_id") is not None and price is None:
            raise ValueError("The selected price option could not be verified")
        rows += [row("procedure", procedure_name(args["procedure_code"], locale), locale),
                 row("doctor", doctor["name"], locale), row("time", slot["start_at"], locale),
                 *price_rows(price, locale), row("note", args.get("note"), locale)]
        notice = label("booking_notice", locale)
    elif tool == CANCEL:
        validate_args(tool, args, hospital_id)
        reservations = (await lookup("business_get_my_reservations", {}))["reservations"]
        reservation = next((r for r in reservations if r["id"] == args["reservation_id"]
                            and (r.get("hospital") or {}).get("id") == hospital_id), None)
        if reservation is None:
            raise ValueError("Choose your own reservation at the selected hospital")
        slot = reservation.get("slot") or {}
        rows += [row("procedure", procedure_name(reservation.get("procedure_code"), locale), locale),
                 row("doctor", slot.get("doctor_name"), locale), row("time", slot.get("start_at"), locale),
                 row("reason", args.get("reason"), locale)]
        notice = label("cancel_notice", locale)
    else:
        args["conversation_id"] = state.get("conversation_id")
        if not args["conversation_id"]:
            raise ValueError("A trusted conversation ID is required")
        args["summary_card"] = await summarize(state)
        args["consent"] = False
        rows += summary_rows(args["summary_card"], locale)
        notice = label("consent_notice", locale)
    validate_args(tool, args, hospital_id)
    return {"action": PENDING_ACTION_BY_TOOL[tool], "tool": tool, "tool_call_id": call["id"],
            "hospital_id": hospital_id, "args": args, "approved": False,
            "editable": EDITABLE[tool],
            "display": {"title": label({BOOK: "book", CANCEL: "cancel", HANDOFF: "handoff"}[tool], locale),
                        "rows": rows, "notice": notice}}
