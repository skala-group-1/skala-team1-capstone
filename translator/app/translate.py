"""번역 로직. 메시지 1건당 LLM 호출은 1회 이하 (실시간성).

- 번역 + 의료질문 분류를 structured output 한 번으로 받는다 (별도 분류 호출 금지).
- 숫자·날짜·금액 검증은 LLM 이 아니라 코드(정규식)로 한다 → NUMBER_MISMATCH.
- `from == to` 면 LLM 호출 없이 원문을 그대로 돌려보낸다.
"""

import re

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.glossary import format_glossary, select_terms
from app.messages import ChatTranslate, ChatTranslated, SummaryTranslate, SummaryTranslated

LANG_NAME = {"ko": "Korean", "en": "English", "zh": "Simplified Chinese", "ja": "Japanese"}

# 「공통 계약서」 SummaryCard 의 자유 텍스트 필드만 번역한다 (stayDays·customerLocale 은 그대로)
SUMMARY_TEXT_KEYS = ("procedure", "preferredDates", "budget")


class ChatTranslation(BaseModel):
    """번역 LLM 호출의 structured output (1회 호출로 번역 + 의료질문 분류)."""
    translated_text: str = Field(description="The translated message, nothing else")
    is_medical_question: bool = Field(
        description="True if the source message asks for medical judgment "
                    "(diagnosis, treatment suitability/effect, safety for a personal condition)")


class SummaryTranslation(BaseModel):
    translations: list[str] = Field(description="Translations of the input items, same order and same length")


_llm_cache: dict[str, object] = {}


def _structured_llm(schema: type[BaseModel]):
    key = schema.__name__
    if key not in _llm_cache:
        s = get_settings()
        _llm_cache[key] = ChatOpenAI(model=s.llm_fast_model, api_key=s.openai_api_key)\
            .with_structured_output(schema)
    return _llm_cache[key]


_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")


def extract_numbers(text: str) -> list[str]:
    """숫자·날짜·금액에 들어가는 수 토큰을 정규식으로 추출 (천 단위 구분 쉼표는 제거)."""
    return sorted(token.replace(",", "") for token in _NUM_RE.findall(text))


def numbers_mismatch(source: str, translated: str) -> bool:
    return extract_numbers(source) != extract_numbers(translated)


def _lang(code: str) -> str:
    return LANG_NAME.get(code, code)


def _chat_prompt(text: str, from_: str, to: str, pairs: list[tuple[str, str]]) -> str:
    glossary = f"\nGlossary — use exactly these target terms:\n{format_glossary(pairs)}\n" if pairs else ""
    return (
        "You are a real-time interpreter in a chat between a Korean clinic counselor and a foreign "
        f"customer (skin / plastic-surgery consultation). Translate the message below from "
        f"{_lang(from_)} to {_lang(to)}.\n"
        "Rules:\n"
        f"- Write what a native {_lang(to)} speaker would naturally say — no stilted, literal phrasing.\n"
        "- Keep every number, date and amount exactly as written in the source (same digits).\n"
        "- Translate only. Do not add, omit, answer or explain anything.\n"
        "- Set is_medical_question to true only if the message asks for medical judgment "
        "(diagnosis, whether a procedure suits/is safe for a personal condition, guaranteed results).\n"
        f"{glossary}\n"
        f"Message:\n{text}"
    )


async def translate_chat(msg: ChatTranslate) -> ChatTranslated:
    if msg.from_ == msg.to:
        return ChatTranslated(message_id=msg.message_id, ok=True, translated_text=msg.text)

    pairs = select_terms(msg.text, msg.from_, msg.to)
    result: ChatTranslation = await _structured_llm(ChatTranslation).ainvoke(
        _chat_prompt(msg.text, msg.from_, msg.to, pairs))

    flags = []
    if numbers_mismatch(msg.text, result.translated_text):
        flags.append("NUMBER_MISMATCH")
    if result.is_medical_question:
        flags.append("MEDICAL_QUESTION")
    return ChatTranslated(message_id=msg.message_id, ok=True,
                          translated_text=result.translated_text, flags=flags)


def _summary_prompt(items: list[str], from_: str, to: str, pairs: list[tuple[str, str]]) -> str:
    glossary = f"\nGlossary — use exactly these target terms:\n{format_glossary(pairs)}\n" if pairs else ""
    numbered = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
    return (
        f"Translate each item below from {_lang(from_)} to {_lang(to)}. They are fields of a "
        "consultation summary card for a Korean clinic counselor.\n"
        "Rules:\n"
        f"- Natural {_lang(to)} as a native speaker would write it.\n"
        "- Preserve all numbers, amounts and the exact calendar dates; do not add or omit facts.\n"
        "- Localize month names and date formatting into the target language, preserving year, month and day.\n"
        "  For Korean, October 22 to October 28, 2026 becomes 2026년 10월 22일부터 10월 28일까지.\n"
        "  Do not leave English month names in a Korean date or change currency amounts.\n"
        "- Return exactly one translation per item, same order.\n"
        f"{glossary}\n"
        f"Items:\n{numbered}"
    )


async def translate_summary(msg: SummaryTranslate) -> SummaryTranslated:
    card = dict(msg.summary_card)
    if msg.from_ == msg.to:
        return SummaryTranslated(consultation_id=msg.consultation_id, ok=True, summary_card_ko=card)

    text_keys = [k for k in SUMMARY_TEXT_KEYS if isinstance(card.get(k), str) and card[k]]
    questions = card.get("questions")
    question_items = [q for q in questions if isinstance(q, str)] if isinstance(questions, list) else []
    items = [card[k] for k in text_keys] + question_items
    if not items:
        return SummaryTranslated(consultation_id=msg.consultation_id, ok=True, summary_card_ko=card)

    pairs = select_terms("\n".join(items), msg.from_, msg.to)
    result: SummaryTranslation = await _structured_llm(SummaryTranslation).ainvoke(
        _summary_prompt(items, msg.from_, msg.to, pairs))
    if len(result.translations) != len(items):
        raise ValueError(f"summary translation count mismatch: {len(result.translations)} != {len(items)}")

    for key, translated in zip(text_keys, result.translations):
        card[key] = translated
    if question_items:
        card["questions"] = result.translations[len(text_keys):]
    return SummaryTranslated(consultation_id=msg.consultation_id, ok=True, summary_card_ko=card)
