"""POST /summarize 입출력 모델. JSON 은 camelCase (「공통 계약서」 1장).

SummaryCard 필드명은 frontend/src/types/contract.ts 의 SummaryCard 와 1:1
(procedure, preferredDates, stayDays, budget, questions, customerLocale).
대화·conditions 에서 확인 안 되는 값은 null (지어내기 금지).
"""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ChatTurn(CamelModel):
    role: Literal["user", "assistant"]
    content: str


class Conditions(CamelModel):
    """에이전트 state 의 Conditions (contract.ts). dateFrom = 입국일, dateTo = 출국일."""
    procedure_code: str | None = None
    areas: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    budget_max_krw: int | None = None
    consult_language: str | None = None
    sort_by: str | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class SummarizeRequest(CamelModel):
    purpose: Literal["HANDOFF_TO_SUB", "NEEDS_CARD"]
    messages: list[ChatTurn]
    locale: Literal["en", "zh", "ja"]
    conditions: Conditions | None = None


class SummaryCard(CamelModel):
    procedure: str | None = None
    preferred_dates: str | None = None
    stay_days: int | None = None
    budget: str | None = None
    questions: list[str] = Field(default_factory=list)
    customer_locale: str


class SummarizeResponse(CamelModel):
    summary_card: SummaryCard
    text: str
