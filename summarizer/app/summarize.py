"""상담 요청 요약 카드 생성 — "리포트가 아니라 그냥 요약" (사실 나열만, 해석·추천·의료 판단 금지).

- LLM 1회 호출 (structured output, "unknown 이면 null") 로 카드 초안 + text 를 받는다.
- conditions 로 확인되는 값(시술 코드·체류일·예산)은 LLM 결과보다 **코드로 덮어쓴다** (conditions 우선).
- customerLocale 은 항상 요청의 locale (대화에서 추측 금지).
- text: HANDOFF_TO_SUB 는 영어(서브 에이전트 system 프롬프트 주입용), NEEDS_CARD 는 사용자 locale.
"""

import json

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.schemas import Conditions, SummarizeRequest, SummarizeResponse, SummaryCard

LANG_NAME = {"ko": "Korean", "en": "English", "zh": "Simplified Chinese", "ja": "Japanese"}
GLOSSARY_LANG_KEY = {"ko": "term_ko", "en": "term_en", "zh": "term_zh", "ja": "term_ja"}


class CardDraft(BaseModel):
    """LLM structured output. 대화에서 확인되지 않는 필드는 반드시 null."""
    procedure: str | None = Field(description="Procedure the customer wants, with its standard code if mentioned; null if unknown")
    preferred_dates: str | None = Field(description="Desired procedure date or date range as stated; null if unknown")
    stay_days: int | None = Field(description="Length of stay in Korea in days (arrival to departure, inclusive); null if unknown")
    budget: str | None = Field(description="Budget upper limit in KRW as stated; null if unknown")
    questions: list[str] = Field(default_factory=list, description="Questions the customer wants the hospital to answer; empty if none")
    text: str = Field(description="At most 3 plain sentences of extra context not in the card fields (declined options, special requests). Facts only")


_llm = None
_procedure_names: dict[str, dict[str, str]] | None = None


def _structured_llm():
    global _llm
    if _llm is None:
        s = get_settings()
        _llm = ChatOpenAI(model=s.llm_fast_model, api_key=s.openai_api_key).with_structured_output(CardDraft)
    return _llm


def procedure_names() -> dict[str, dict[str, str]]:
    """glossary.json 의 note("procedure: CODE") 로 시술 코드 → 언어별 표시명 매핑을 만든다."""
    global _procedure_names
    if _procedure_names is None:
        terms = json.loads(get_settings().glossary_path.read_text(encoding="utf-8"))
        mapping: dict[str, dict[str, str]] = {}
        for term in terms:
            note = term.get("note") or ""
            if note.startswith("procedure: "):
                code = note.removeprefix("procedure: ").split(";")[0].strip()
                mapping[code] = term
        _procedure_names = mapping
    return _procedure_names


def procedure_display(code: str, locale: str) -> str:
    """표준 시술 코드 + 표시명. 예: 埋线双眼皮 (DOUBLE_EYELID_NONINCISION)"""
    term = procedure_names().get(code)
    name = term.get(GLOSSARY_LANG_KEY.get(locale, "term_en")) if term else None
    return f"{name} ({code})" if name else code


def format_budget(krw: int, locale: str) -> str:
    """예산 상한(KRW) 표시 문자열. 예: 200万韩元以下 / Up to 2,000,000 KRW"""
    if locale in ("zh", "ja") and krw % 10_000 == 0:
        man = krw // 10_000
        return f"{man}万韩元以下" if locale == "zh" else f"{man}万ウォン以下"
    return f"Up to {krw:,} KRW"


def _prompt(req: SummarizeRequest) -> str:
    transcript = "\n".join(f"{m.role}: {m.content}" for m in req.messages)
    text_lang = "English" if req.purpose == "HANDOFF_TO_SUB" else LANG_NAME[req.locale]
    conditions = ""
    if req.conditions is not None:
        conditions = ("\nConfirmed conditions (authoritative — prefer these over the conversation):\n"
                      f"{req.conditions.model_dump_json(by_alias=True)}\n")
    return (
        "Summarize the consultation request below into a card. This is a summary, not a report: "
        "state only facts from the conversation — no interpretation, no recommendation, no evaluation, "
        "no medical judgment.\n"
        "Rules:\n"
        "- Fill every card field that the conversation (or conditions) confirms; set a field to null "
        "ONLY if it is unknown. Never invent a value.\n"
        f"- Write card field values in {LANG_NAME[req.locale]}.\n"
        f"- Write `text` in {text_lang}, at most 3 plain sentences, covering only context that is not "
        "already in the card fields (e.g. options the customer declined, special requests).\n"
        f"{conditions}\n"
        f"Conversation:\n{transcript}"
    )


def _apply_conditions(card: SummaryCard, cond: Conditions | None, locale: str) -> SummaryCard:
    """conditions 에 있는 값은 대화 요약보다 우선한다."""
    if cond is None:
        return card
    if cond.procedure_code:
        card.procedure = procedure_display(cond.procedure_code, locale)
    if cond.date_from and cond.date_to:
        card.stay_days = (cond.date_to - cond.date_from).days + 1
    if cond.budget_max_krw:
        card.budget = format_budget(cond.budget_max_krw, locale)
    return card


async def summarize(req: SummarizeRequest) -> SummarizeResponse:
    draft: CardDraft = await _structured_llm().ainvoke(_prompt(req))
    card = SummaryCard(
        procedure=draft.procedure,
        preferred_dates=draft.preferred_dates,
        stay_days=draft.stay_days,
        budget=draft.budget,
        questions=draft.questions,
        customer_locale=req.locale,          # 항상 요청 locale (프로필 언어), 대화에서 추측 금지
    )
    card = _apply_conditions(card, req.conditions, req.locale)
    return SummarizeResponse(summary_card=card, text=draft.text)
