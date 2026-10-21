"""요약 카드: 두 purpose 같은 스키마, 5개 필수 필드 존재, 지어내기 금지(null), conditions 우선,
customerLocale = 요청 locale, purpose 별 text 언어 지시."""

from app.summarize import CardDraft

# contract.ts SummaryCard 의 키 (camelCase) — 응답에 전부 존재해야 한다
CARD_KEYS = {"procedure", "preferredDates", "stayDays", "budget", "questions", "customerLocale"}

DRAFT = CardDraft(
    procedure="埋线双眼皮 (DOUBLE_EYELID_NONINCISION)",
    preferred_dates="10/21 – 10/23",
    stay_days=7,
    budget="200万韩元以下",
    questions=["可以用英语咨询吗"],
    text="顾客拒绝了切开法。",
)

MESSAGES = [
    {"role": "user", "content": "我想做埋线双眼皮，10月21日到23日之间，预算200万韩元以内。"},
    {"role": "assistant", "content": "好的，我来整理您的条件。"},
]


def post(client, **overrides):
    body = {"purpose": "NEEDS_CARD", "messages": MESSAGES, "locale": "zh"}
    body.update(overrides)
    res = client.post("/summarize", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_both_purposes_return_same_schema(client, fake_llm):
    fake_llm(DRAFT)
    for purpose in ("HANDOFF_TO_SUB", "NEEDS_CARD"):
        out = post(client, purpose=purpose)
        assert set(out) == {"summaryCard", "text"}
        assert set(out["summaryCard"]) == CARD_KEYS


def test_all_five_fields_filled_from_conversation(client, fake_llm):
    fake_llm(DRAFT)
    card = post(client)["summaryCard"]
    assert card["procedure"].endswith("(DOUBLE_EYELID_NONINCISION)")
    assert card["preferredDates"] == "10/21 – 10/23"
    assert card["stayDays"] == 7
    assert card["budget"] == "200万韩元以下"
    assert card["questions"] == ["可以用英语咨询吗"]


def test_unknown_budget_stays_null(client, fake_llm):
    fake_llm(CardDraft(procedure=None, preferred_dates=None, stay_days=None,
                       budget=None, questions=[], text=""))
    card = post(client)["summaryCard"]
    assert card["budget"] is None and card["stayDays"] is None and card["preferredDates"] is None


def test_conditions_override_llm_draft(client, fake_llm):
    fake_llm(CardDraft(procedure="别的手术", preferred_dates=None, stay_days=3,
                       budget="300万韩元以下", questions=[], text=""))
    card = post(client, conditions={
        "procedureCode": "DOUBLE_EYELID_NONINCISION",
        "areas": [], "dateFrom": "2026-10-20", "dateTo": "2026-10-26",
        "budgetMaxKrw": 2_000_000, "consultLanguage": "zh", "sortBy": "REVIEW_COUNT",
    })["summaryCard"]
    assert card["procedure"] == "埋线双眼皮 (DOUBLE_EYELID_NONINCISION)"   # glossary 표시명 + 코드
    assert card["stayDays"] == 7                                           # 10/20–10/26 · 7일
    assert card["budget"] == "200万韩元以下"


def test_customer_locale_is_request_locale(client, fake_llm):
    fake_llm(DRAFT)
    assert post(client, locale="ja")["summaryCard"]["customerLocale"] == "ja"


def test_korean_locale_is_supported(client, fake_llm):
    llm = fake_llm(CardDraft(procedure=None, preferred_dates="12월 초", stay_days=None, budget=None,
                             questions=["회복 기간이 얼마나 걸리나요?", "통역 지원이 되나요?"], text=""))
    card = post(client, locale="ko", messages=[
        {"role": "user", "content": "12월 초에 쌍꺼풀 받고 싶은데 회복 기간이랑 통역 지원이 궁금해요."},
    ])["summaryCard"]
    assert card["customerLocale"] == "ko"
    assert card["preferredDates"] == "12월 초"
    assert card["questions"] == ["회복 기간이 얼마나 걸리나요?", "통역 지원이 되나요?"]
    assert card["budget"] is None and card["stayDays"] is None          # 언급 없는 항목은 빈 값 유지
    assert "Write card field values in Korean" in llm.calls[0]


def test_korean_conditions_use_korean_display(client, fake_llm):
    fake_llm(CardDraft(procedure=None, preferred_dates=None, stay_days=None,
                       budget=None, questions=[], text=""))
    card = post(client, locale="ko", conditions={
        "procedureCode": "DOUBLE_EYELID_NONINCISION",
        "areas": [], "dateFrom": "2026-10-20", "dateTo": "2026-10-26",
        "budgetMaxKrw": 2_000_000, "consultLanguage": "ko", "sortBy": "REVIEW_COUNT",
    })["summaryCard"]
    assert card["procedure"] == "매몰법 (DOUBLE_EYELID_NONINCISION)"     # glossary term_ko + 코드
    assert card["stayDays"] == 7
    assert card["budget"] == "200만원 이하"


def test_text_language_instruction_per_purpose(client, fake_llm):
    llm = fake_llm(DRAFT)
    post(client, purpose="HANDOFF_TO_SUB", locale="zh")
    assert "Write `text` in English" in llm.calls[0]                 # 서브 에이전트 주입용
    post(client, purpose="NEEDS_CARD", locale="zh")
    assert "Write `text` in Simplified Chinese" in llm.calls[1]      # 사용자 locale
