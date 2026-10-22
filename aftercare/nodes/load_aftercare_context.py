"""Load the reservation behind an aftercare conversation and verify it via MCP.

The reservation ID comes from the backend's AFTERCARE_INTRO action once and is
kept in state. Every turn re-reads it from the user's own reservations so a
cancelled or foreign reservation can never be used as context.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.graph.state import AgentState
from app.mcp_client.client import get_tools
from concierge.nodes.load_hospital_context import selected_hospital, tool_data

INTRO = "AFTERCARE_INTRO"
SEOUL = ZoneInfo("Asia/Seoul")


def reservation_id(state: AgentState) -> int:
    action = state.get("action") or {}
    value = (state.get("aftercare_context") or {}).get("reservation_id")
    if value is None and action.get("type") == INTRO:
        value = action.get("reservationId")
    if type(value) is not int or value <= 0:
        raise ValueError("An aftercare reservation is required")
    return value


def days_since(start_at: str, today=None) -> int | None:
    """Days after the procedure (procedure day = 0). None before the procedure."""
    start = datetime.fromisoformat(start_at)
    if start.tzinfo is None:
        raise ValueError("Procedure time must include an offset")
    today = today or datetime.now(SEOUL).date()
    days = (today - start.astimezone(SEOUL).date()).days
    return days if days >= 0 else None


async def _read(name, args):
    tools = {tool.name: tool for tool in await get_tools((name,))}
    if name not in tools:
        raise ValueError(f"Required MCP tool unavailable: {name}")
    return tool_data(await tools[name].ainvoke(args))


async def load_aftercare_context(state: AgentState) -> dict:
    hospital_id = selected_hospital(state)
    rid = reservation_id(state)
    reservations = (await _read("business_get_my_reservations", {}))["reservations"]
    reservation = next((r for r in reservations if r.get("id") == rid), None)
    if reservation is None or (reservation.get("hospital") or {}).get("id") != hospital_id:
        raise ValueError("Aftercare reservation does not belong to this conversation")
    if reservation.get("status") != "CONFIRMED":
        raise ValueError("Aftercare is available for confirmed reservations only")
    start_at = (reservation.get("slot") or {}).get("start_at")
    procedure_code = reservation.get("procedure_code")
    if not isinstance(start_at, str) or not isinstance(procedure_code, str):
        raise ValueError("Reservation procedure or time is missing")

    context = dict(state.get("hospital_context") or {})
    if context.get("hospital_id") != hospital_id or "detail" not in context:
        detail = await _read("business_get_hospital_detail", {"hospital_id": hospital_id})
        if detail.get("id") != hospital_id:
            raise ValueError("Hospital context does not match the selected hospital")
        context = {"hospital_id": hospital_id, "detail": detail}
    return {
        "hospital_context": context,
        # The summarizer card for a counselor handoff reads the procedure from conditions.
        "conditions": {**(state.get("conditions") or {}), "procedure_code": procedure_code},
        "aftercare_context": {
            "reservation_id": rid, "procedure_code": procedure_code, "start_at": start_at,
            "days_since_procedure": days_since(start_at),
            "doctor_name": (reservation.get("slot") or {}).get("doctor_name"),
        },
    }
