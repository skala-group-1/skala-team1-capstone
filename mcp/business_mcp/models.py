"""도구 출력 모델 (snake_case). 필드는 12 계약서 5장 DTO 를 snake_case 로 옮긴 것.

- Pydantic 반환 → FastMCP 가 structuredContent + outputSchema 로 노출 (04 문서 1장)
- null 허용 필드는 생략하지 않고 None (12 계약서 1장: FE 는 null 이면 '확인 필요')
- backend 가 필드를 더 주더라도 무시하도록 extra="ignore"
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

AreaCode = Literal["GANGNAM", "SINSA", "APGUJEONG", "CHEONGDAM", "MYEONGDONG", "HONGDAE", "JAMSIL"]
SortBy = Literal["REVIEW_COUNT", "RATING", "PRICE", "DISTANCE"]
Locale = Literal["en", "zh", "ja", "ko"]
ReservationStatus = Literal["PENDING", "CONFIRMED", "REJECTED", "EXPIRED", "CANCELLED"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")


# --- 탐색·병원 -------------------------------------------------------------

class ProcedureCandidate(_Model):
    code: str
    name: str
    score: float


class NormalizeResult(_Model):
    candidates: list[ProcedureCandidate]


class Procedure(_Model):
    code: str
    category: str
    name: str
    duration_min: int | None = None
    downtime_days: int | None = None


class HospitalCard(_Model):
    id: int
    name: str
    area_code: str
    category: str
    min_price_krw: int | None = None
    price_verified: bool | None = None
    review_count: int = 0
    rating: float | None = None
    languages: list[str] = []
    has_interpreter: bool = False
    earliest_slot_at: str | None = None
    distance_km: float | None = None


class SearchHospitalsResult(_Model):
    hospitals: list[HospitalCard]
    total: int


class Doctor(_Model):
    id: int
    name: str
    title: str | None = None
    specialties: list[str] = []
    languages: list[str] = []
    career_years: int | None = None


class DoctorList(_Model):
    doctors: list[Doctor]


class PriceOption(_Model):
    id: int
    procedure_code: str
    product: str | None = None
    dose: str | None = None
    price_krw: int
    vat_included: bool
    conditions: str | None = None
    verified_at: str | None = None


class PriceOptionList(_Model):
    options: list[PriceOption]


class Slot(_Model):
    id: int
    start_at: str
    end_at: str | None = None
    doctor_id: int | None = None
    doctor_name: str | None = None
    status: str = "AVAILABLE"


class SlotList(_Model):
    slots: list[Slot]


class HospitalDetail(_Model):
    id: int
    name: str
    name_ko: str | None = None
    category: str
    area_code: str
    address: str | None = None
    phone: str | None = None
    description: str | None = None
    open_hours: dict[str, Any] = {}
    languages: list[str] = []
    has_interpreter: bool = False
    verified_at: str | None = None
    # TODO(mcp): lite=false 일 때 doctors·procedures·review_stats 도 노출할지 결정.
    #            토큰 절약을 위해 기본은 lite(기본정보만)로 두고, 의사·가격은 전용 도구를 쓰게 한다.


class CompareColumn(_Model):
    hospital: HospitalCard
    options: list[PriceOption]
    earliest_slot_at: str | None = None
    verified_at: str | None = None


class CompareResult(_Model):
    procedure_code: str
    columns: list[CompareColumn]


# --- 일정 적합성 (D-23) ----------------------------------------------------

class TripPlan(_Model):
    hospital_id: int
    hospital_name: str | None = None
    slot: Slot | None = None
    procedure_code: str
    downtime_days: int | None = None
    recovery_end_date: str | None = None
    buffer_days: int | None = None
    feasible: bool
    reason: Literal["OK", "RECOVERY_AFTER_DEPARTURE", "NO_SLOT_BEFORE_DEPARTURE"]


class TripPlanResult(_Model):
    plans: list[TripPlan]


# --- 예약·상담 -------------------------------------------------------------

class HospitalRef(_Model):
    id: int
    name: str


class Reservation(_Model):
    id: int
    status: ReservationStatus
    source: str | None = None
    hospital: HospitalRef | None = None
    slot: Slot | None = None
    procedure_code: str | None = None
    hold_expires_at: str | None = None
    reject_reason: str | None = None
    created_at: str | None = None
    # TODO(mcp): 12 계약서 Reservation 의 procedure·price_option·alternatives 를 그대로 넘길지,
    #            LLM 에 필요한 필드만 남길지 agent 담당과 합의


class ReservationList(_Model):
    reservations: list[Reservation]


class SummaryCard(_Model):
    """상담 요청 시 넘기는 니즈 요약 카드 (12 계약서 SummaryCard)."""

    procedure: str
    preferred_dates: str | None = None
    stay_days: int | None = None
    budget: str | None = None
    questions: list[str] = []
    customer_locale: Literal["en", "zh", "ja"]


class Consultation(_Model):
    id: int
    status: Literal["WAITING", "ACTIVE", "CLOSED"]
    hospital: HospitalRef | None = None
    conversation_id: str | None = None
    created_at: str | None = None
