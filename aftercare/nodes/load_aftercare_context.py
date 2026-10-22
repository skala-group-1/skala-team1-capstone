"""Load the reservation behind an aftercare conversation and verify it via MCP.

The reservation ID comes from the backend's guide action (AFTERCARE_INTRO on the
first visit, AFTERCARE_DAILY on later days) and is kept in state. Every turn
re-reads it from the user's own reservations so a foreign reservation can never
be used as context. Rejected, cancelled or expired reservations keep the room
but are marked closed so the agent stops guiding.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.graph.state import AgentState
from app.mcp_client.client import get_tools
from concierge.nodes.load_hospital_context import selected_hospital, tool_data

INTRO = "AFTERCARE_INTRO"
DAILY = "AFTERCARE_DAILY"
GUIDES = (INTRO, DAILY)
ACTIVE = ("PENDING", "CONFIRMED")
SEOUL = ZoneInfo("Asia/Seoul")


def reservation_id(state: AgentState) -> int:
    action = state.get("action") or {}
    value = (state.get("aftercare_context") or {}).get("reservation_id")
    if value is None and action.get("type") in GUIDES:
        value = action.get("reservationId")
    if type(value) is not int or value <= 0:
        raise ValueError("An aftercare reservation is required")
    return value


def days_from(start_at: str, now: datetime | None = None) -> tuple[int, bool]:
    """(days from the procedure date, whether the procedure time is still ahead).

    Procedure day = 0, before it negative, after it positive (Asia/Seoul dates).
    """
    start = datetime.fromisoformat(start_at)
    if start.tzinfo is None:
        raise ValueError("Procedure time must include an offset")
    now = now or datetime.now(SEOUL)
    return (now.astimezone(SEOUL).date() - start.astimezone(SEOUL).date()).days, now < start


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
    start_at = (reservation.get("slot") or {}).get("start_at")
    procedure_code = reservation.get("procedure_code")
    if not isinstance(start_at, str) or not isinstance(procedure_code, str):
        raise ValueError("Reservation procedure or time is missing")
    days, before_start = days_from(start_at)

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
            "reservation_id": rid, "reservation_status": reservation.get("status"),
            "closed": reservation.get("status") not in ACTIVE,
            "procedure_code": procedure_code, "start_at": start_at,
            "days_from_procedure": days, "before_start": before_start,
            "doctor_name": (reservation.get("slot") or {}).get("doctor_name"),
        },
    }
