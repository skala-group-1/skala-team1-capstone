"""business-mcp 서버 (port 9101). 도구 13개 = 조회 9 + 승인 변경 3 + 대화 열기 1.

규칙 (「MCP 설계」 1장)
- 함수명 = 도구명. agent 에서는 접두어가 붙어 business_<name> 으로 보인다
- docstring = description (영어, 입력·출력·단위·언제 쓰는지). LLM 이 읽는 문장이므로 신중히 수정
- 조회 도구 readOnlyHint=true / 승인 필요 도구 destructiveHint=true + idempotentHint
- 예약·취소·상담 도구는 승인 interrupt 후 호출한다. 대화 열기는 명시적 병원 선택만 필요하다
- acting_user_id·trace_id 는 인자로 받지 않는다 → context.current_context()

실행: cd mcp && uv run python -m business_mcp.server   (MCP_TRANSPORT=stdio 로 stdio)
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from business_mcp.backend_client import BackendClient, build_client
from business_mcp.context import current_context
from business_mcp.models import (
    AreaCode, CompareResult, Consultation, Conversation, DoctorList, HospitalDetail, Locale, NormalizeResult,
    PriceOptionList, Reservation, ReservationList, ReservationStatus, SearchHospitalsResult, SlotList,
    SortBy, SummaryCard, TripPlanResult,
)
from mcp_common.run import run_server

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
DESTRUCTIVE_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False)

mcp = FastMCP(
    name="business-mcp",
    instructions=(
        "Business data tools for a fictional Korean skin/plastic-surgery clinic marketplace. "
        "All facts (prices, slots, hospitals) must come from these tools. "
        "Never rank or recommend hospitals; only filter and sort by the user's chosen criterion."
    ),
)

# 테스트에서 StubBackendClient 등으로 바꿔 끼울 수 있게 모듈 전역으로 둔다
backend: BackendClient = build_client()


# ============================== 조회 도구 (9) ==============================

@mcp.tool(annotations=READ_ONLY)
async def normalize_procedure(
    text: Annotated[str, Field(description="Free-text procedure name in any language, e.g. 'double eyelid', '瘦脸针'")],
    locale: Annotated[Locale | None, Field(description="Language of the returned names. Defaults to the user's locale")] = None,
) -> NormalizeResult:
    """Map a free-text procedure name to standard procedure codes.

    Use this FIRST whenever the user mentions a procedure, before any tool that needs procedure_code.
    Returns up to 3 candidates (code, localized name, score 0-1). If the top score is low or there are
    several close candidates, ask the user which one they mean instead of guessing.
    """
    ctx = current_context()
    if locale:
        ctx = ctx.__class__(ctx.acting_user_id, ctx.trace_id, locale)
    return NormalizeResult.model_validate(await backend.normalize_procedure(ctx, text))


@mcp.tool(annotations=READ_ONLY)
async def search_hospitals(
    procedure_code: Annotated[str, Field(description="Standard code from normalize_procedure, e.g. DOUBLE_EYELID_NONINCISION")],
    date_from: Annotated[str, Field(description="Arrival date in Korea, YYYY-MM-DD")],
    date_to: Annotated[str | None, Field(description="Departure date, YYYY-MM-DD")] = None,
    areas: Annotated[list[AreaCode] | None, Field(description="Seoul area codes to include; omit for all areas")] = None,
    budget_max_krw: Annotated[int | None, Field(description="Max price in KRW (integer won), compared with the cheapest option")] = None,
    language: Annotated[str | None, Field(description="Consultation language the clinic must support: en, zh, ja")] = None,
    sort_by: Annotated[SortBy, Field(description="Sort order chosen by the user. Not a recommendation")] = "REVIEW_COUNT",
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> SearchHospitalsResult:
    """Find hospitals that offer a procedure and match the user's conditions.

    Output: hospitals (id, name, area_code, min_price_krw, review_count, rating, languages,
    earliest_slot_at ISO-8601 +09:00) and total count. Prices are KRW integers.
    If total is 0, relax ONE condition (date ±1 day, budget, or area), search again and tell the user what was relaxed.
    Results are filtered and sorted only; do not describe any hospital as 'best' or 'recommended'.
    """
    # TODO(mcp): 0건일 때 완화 옵션별 예상 건수(relaxOptions)를 이 도구가 줄지, agent 가 재호출할지 결정 (「AI Agent 설계」 9-1)
    result = await backend.search_hospitals(current_context(), {
        "procedure_code": procedure_code, "areas": areas, "date_from": date_from, "date_to": date_to,
        "budget_max_krw": budget_max_krw, "consult_language": language, "sort_by": sort_by, "limit": limit,
    })
    return SearchHospitalsResult(hospitals=result["items"], total=result["total"])


@mcp.tool(annotations=READ_ONLY)
async def get_hospital_detail(
    hospital_id: Annotated[int, Field(description="Hospital id from search_hospitals results")],
) -> HospitalDetail:
    """Get basic information about one hospital: name, address, phone, opening hours, supported languages,
    interpreter availability and the date the information was last verified (verified_at, YYYY-MM-DD or null).

    Use list_doctors / get_price_options / get_available_slots for doctors, prices and slots.
    """
    return HospitalDetail.model_validate(await backend.get_hospital_detail(current_context(), hospital_id))


@mcp.tool(annotations=READ_ONLY)
async def list_doctors(
    hospital_id: int,
    procedure_code: Annotated[str | None, Field(description="Only doctors whose specialties include this code")] = None,
) -> DoctorList:
    """List doctors of a hospital (id, name, title, specialties as procedure codes, languages, career_years)."""
    return DoctorList(doctors=await backend.list_doctors(current_context(), hospital_id, procedure_code))


@mcp.tool(annotations=READ_ONLY)
async def get_price_options(hospital_id: int, procedure_code: str) -> PriceOptionList:
    """List price options of one procedure at one hospital.

    Each option: product, dose, price_krw (KRW integer), vat_included, conditions, verified_at (null = unverified).
    Quote prices exactly as returned and always mention whether VAT is included.
    """
    return PriceOptionList(options=await backend.get_price_options(current_context(), hospital_id, procedure_code))


@mcp.tool(annotations=READ_ONLY)
async def get_available_slots(
    hospital_id: int,
    procedure_code: str,
    date_from: Annotated[str, Field(description="YYYY-MM-DD, inclusive")],
    date_to: Annotated[str, Field(description="YYYY-MM-DD, inclusive")],
    doctor_id: int | None = None,
) -> SlotList:
    """List bookable slots (status AVAILABLE) at a hospital in a date range, earliest first, at most 20.

    Each slot: id, start_at / end_at (ISO-8601 +09:00, Asia/Seoul), doctor_id, doctor_name.
    Use the slot id with create_reservation_request.
    """
    return SlotList(slots=await backend.get_available_slots(
        current_context(), hospital_id, procedure_code, date_from, date_to, doctor_id))


@mcp.tool(annotations=READ_ONLY)
async def compare_hospitals(
    hospital_ids: Annotated[list[int], Field(min_length=1, max_length=3, description="Up to 3 hospital ids")],
    procedure_code: str,
) -> CompareResult:
    """Build a side-by-side comparison of up to 3 hospitals for one procedure:
    hospital card, price options, earliest slot and verified_at per column.
    Missing values are null; present them as 'needs confirmation', never guess.
    """
    return CompareResult.model_validate(
        await backend.compare_hospitals(current_context(), hospital_ids, procedure_code))


@mcp.tool(annotations=READ_ONLY)
async def get_my_reservations(
    status: Annotated[ReservationStatus | None, Field(description="Filter by status; omit for all")] = None,
) -> ReservationList:
    """List the current user's reservations (PENDING / CONFIRMED / REJECTED / EXPIRED / CANCELLED).
    Use before cancel_reservation to find the reservation id.
    """
    return ReservationList(reservations=await backend.get_my_reservations(current_context(), status))


@mcp.tool(annotations=READ_ONLY)
async def plan_trip(
    procedure_code: str,
    hospital_ids: Annotated[list[int], Field(min_length=1, max_length=5)],
    arrival_date: Annotated[str, Field(description="YYYY-MM-DD")],
    departure_date: Annotated[str, Field(description="YYYY-MM-DD")],
) -> TripPlanResult:
    """Check, per hospital, whether the procedure fits the user's stay in Korea.

    For each hospital: the earliest slot before departure, recovery_end_date = procedure date + downtime days,
    buffer_days = departure - recovery end, feasible (true if buffer >= 1 day) and reason
    (OK | RECOVERY_AFTER_DEPARTURE | NO_SLOT_BEFORE_DEPARTURE | PROCEDURE_NOT_OFFERED).
    This is a data-based schedule calculation, NOT a medical judgment; tell the user that actual recovery
    time must be confirmed with the clinic's doctor. If nothing is feasible, consider a procedure with
    shorter downtime and explain the difference with rag_search_procedure_docs.
    """
    return TripPlanResult.model_validate(await backend.plan_trip(current_context(), {
        "procedure_code": procedure_code, "hospital_ids": hospital_ids,
        "arrival_date": arrival_date, "departure_date": departure_date,
    }))


# ============================== 대화 열기 (1) ==============================

@mcp.tool(annotations=ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
async def open_hospital_conversation(
    hospital_id: Annotated[int, Field(gt=0, strict=True, description="Hospital id explicitly selected by the user from search results")],
    parent_conversation_id: Annotated[uuid.UUID, Field(description="Current MAIN conversation UUID")],
) -> Conversation:
    """Open a hospital conversation only after the user explicitly selects that hospital.

    Inputs: a positive hospital id and the current MAIN conversation UUID. Returns the backend
    Conversation: id, mode, hospital, parent_conversation_id, consultation_id, conditions,
    created_at (ISO-8601 +09:00), messages. The backend validates ownership and the hospital,
    reuses an existing HOSPITAL/HUMAN conversation, or copies parent conditions into a new one.
    Navigation needs no approval interrupt; reservation, cancellation and consultation still do.
    """
    return Conversation.model_validate(await backend.open_hospital_conversation(
        current_context(), hospital_id, str(parent_conversation_id)))


# ============================== 변경 도구 (3) ==============================
# ⚠️ agent 는 이 도구들을 approval 노드(interrupt) 승인 후에만 호출한다.
#    hospital_id 는 병원 서브그래프 state 에서 강제 주입 (「AI Agent 설계」 4장) — MCP 는 받은 값 그대로 backend 에 넘김.

@mcp.tool(annotations=DESTRUCTIVE_IDEMPOTENT)
async def create_reservation_request(
    hospital_id: int,
    slot_id: Annotated[int, Field(description="Slot id from get_available_slots")],
    procedure_code: str,
    note: Annotated[str | None, Field(description="Optional note to the clinic, in the user's words")] = None,
    price_option_id: Annotated[int | None, Field(description="Chosen price option id, if any")] = None,
    idempotency_key: Annotated[str | None, Field(description="Reuse the same key when retrying the same request")] = None,
) -> Reservation:
    """Request a reservation. Requires the user's explicit approval first.

    Holds the slot for 30 minutes and creates a PENDING reservation that the clinic must approve
    (output: id, status=PENDING, hold_expires_at). Retrying with the same idempotency_key returns the
    same reservation. If the slot is taken, the error lists nearby available slots.
    """
    # TODO(mcp): idempotency_key 를 agent 가 승인 시점에 만들어 넘기도록 합의 (재개·재시도 시 중복 예약 방지).
    #            지금은 없으면 새로 만든다 → 재시도 시 중복 위험
    ctx = current_context()
    body = {"hospital_id": hospital_id, "slot_id": slot_id, "procedure_code": procedure_code,
            "price_option_id": price_option_id, "note": note}
    return Reservation.model_validate(
        await backend.create_reservation(ctx, body, idempotency_key or str(uuid.uuid4())))


@mcp.tool(annotations=DESTRUCTIVE_IDEMPOTENT)
async def cancel_reservation(
    reservation_id: Annotated[int, Field(description="Id from get_my_reservations")],
    reason: str | None = None,
) -> Reservation:
    """Cancel the user's own PENDING or CONFIRMED reservation. Requires the user's explicit approval first."""
    return Reservation.model_validate(await backend.cancel_reservation(current_context(), reservation_id, reason))


@mcp.tool(annotations=DESTRUCTIVE_IDEMPOTENT)
async def request_consultation(
    hospital_id: int,
    summary_card: SummaryCard,
    consent: Annotated[bool, Field(description="Must be true: the user agreed to share this summary with the clinic")],
    conversation_id: Annotated[str | None, Field(description="Current conversation id (uuid)")] = None,
    idempotency_key: str | None = None,
) -> Consultation:
    """Hand the conversation over to a human counselor of the hospital. Requires the user's explicit approval
    of the summary card and consent to share it. Output: consultation id, status=WAITING.
    After success the chat switches to HUMAN mode and AI auto-replies stop.
    """
    # TODO(mcp): conversation_id 는 LLM 인자보다 agent state(thread_id)에서 주입하는 편이 안전 — agent 담당과 합의
    body = {"hospital_id": hospital_id, "conversation_id": conversation_id,
            "summary_card": summary_card.model_dump(), "consent": consent}
    return Consultation.model_validate(
        await backend.request_consultation(current_context(), body, idempotency_key or str(uuid.uuid4())))


if __name__ == "__main__":
    run_server(mcp, default_port=9101)
