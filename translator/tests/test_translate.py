"""번역 로직: 숫자 검증(코드), 의료질문 플래그, 용어집 선별 주입, from==to 패스스루, 요약 카드 번역."""

import pytest

from app.messages import ChatTranslate, SummaryTranslate
from app.translate import ChatTranslation, SummaryTranslation, translate_chat, translate_summary


def chat_msg(text, from_="zh", to="ko"):
    return ChatTranslate(message_id=1, consultation_id=1, text=text, from_=from_, to=to)


async def test_number_mismatch_flagged_but_still_published(fake_llm):
    fake_llm(ChatTranslation(translated_text="가격은 130만 원입니다", is_medical_question=False))
    out = await translate_chat(chat_msg("价格是120万韩元"))
    assert out.ok and out.translated_text == "가격은 130만 원입니다"
    assert "NUMBER_MISMATCH" in out.flags


async def test_matching_numbers_not_flagged(fake_llm):
    fake_llm(ChatTranslation(translated_text="가격은 120만 원입니다", is_medical_question=False))
    out = await translate_chat(chat_msg("价格是120万韩元"))
    assert out.flags == []


async def test_medical_question_flag(fake_llm):
    fake_llm(ChatTranslation(translated_text="이 시술이 제 피부에 안전한가요?", is_medical_question=True))
    out = await translate_chat(chat_msg("这个手术对我的皮肤安全吗?"))
    assert "MEDICAL_QUESTION" in out.flags


async def test_glossary_only_matching_terms_injected(fake_llm):
    llm = fake_llm(ChatTranslation(translated_text="사각턱 보톡스 가격이 궁금해요", is_medical_question=False))
    await translate_chat(chat_msg("我想了解瘦脸针的价格"))
    prompt = llm.calls[0]
    assert "사각턱 보톡스" in prompt          # 원문에 등장한 용어는 주입
    assert "이마 보톡스" not in prompt        # 등장하지 않은 용어는 주입 금지


async def test_same_language_skips_llm(fake_llm):
    llm = fake_llm(RuntimeError("must not be called"))
    out = await translate_chat(chat_msg("안녕하세요", from_="ko", to="ko"))
    assert out.ok and out.translated_text == "안녕하세요" and out.flags == []
    assert llm.calls == []


CARD = {
    "procedure": "埋线双眼皮 (DOUBLE_EYELID_NONINCISION)",
    "preferredDates": "10/21 – 10/23",
    "stayDays": 7,
    "budget": "200万韩元以下",
    "questions": ["可以用英语咨询吗"],
    "customerLocale": "zh",
}


async def test_summary_card_translates_text_fields_only(fake_llm):
    fake_llm(SummaryTranslation(translations=[
        "매몰법 쌍꺼풀 (DOUBLE_EYELID_NONINCISION)", "10/21 – 10/23", "200만 원 이하", "영어로 상담 가능한가요"]))
    msg = SummaryTranslate(consultation_id=5, summary_card=CARD, from_="zh", to="ko")
    out = await translate_summary(msg)
    assert out.ok
    card = out.summary_card_ko
    assert card["procedure"].startswith("매몰법 쌍꺼풀")
    assert card["budget"] == "200만 원 이하"
    assert card["questions"] == ["영어로 상담 가능한가요"]
    assert card["stayDays"] == 7 and card["customerLocale"] == "zh"   # 비텍스트 필드는 그대로


async def test_summary_same_language_skips_llm(fake_llm):
    llm = fake_llm(RuntimeError("must not be called"))
    msg = SummaryTranslate(consultation_id=5, summary_card=CARD, from_="zh", to="zh")
    out = await translate_summary(msg)
    assert out.summary_card_ko == CARD and llm.calls == []


async def test_summary_count_mismatch_raises_for_retry(fake_llm):
    fake_llm(SummaryTranslation(translations=["하나뿐"]))
    msg = SummaryTranslate(consultation_id=5, summary_card=CARD, from_="zh", to="ko")
    with pytest.raises(ValueError):
        await translate_summary(msg)


async def test_summary_localizes_month_names_without_changing_card_facts(fake_llm):
    card = {**CARD, "procedure": "Non-incisional double eyelid surgery",
            "preferredDates": "October 22 to October 28, 2026", "budget": "KRW 2,000,000",
            "questions": [], "customerLocale": "en"}
    llm = fake_llm(SummaryTranslation(translations=[
        "비절개 쌍꺼풀 수술", "2026년 10월 22일부터 10월 28일까지", "KRW 2,000,000"]))
    out = await translate_summary(SummaryTranslate(
        consultation_id=5, summary_card=card, from_="en", to="ko"))
    assert out.summary_card_ko["preferredDates"] == "2026년 10월 22일부터 10월 28일까지"
    assert out.summary_card_ko["budget"] == card["budget"]
    assert out.summary_card_ko["stayDays"] == 7
    assert out.summary_card_ko["customerLocale"] == "en"
    assert card["preferredDates"] == "October 22 to October 28, 2026"
    assert "Localize month names" in llm.calls[0]
    assert "preserving year, month and day" in llm.calls[0]
    assert "Keep every number, date and amount exactly as written" not in llm.calls[0]
