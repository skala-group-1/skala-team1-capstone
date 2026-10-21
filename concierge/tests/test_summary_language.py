"""Customer language is visible before consenting to share a summary."""

from unittest.mock import AsyncMock

import pytest

from concierge.nodes import actions

CARD = {"procedure": "Botox", "preferred_dates": None, "stay_days": None,
        "budget": None, "questions": [], "customer_locale": "ja"}


@pytest.mark.parametrize("locale,expected", [
    ("en", "English"), ("ko", "한국어"), ("zh", "中文"), ("ja", "日本語"),
])
async def test_consent_display_includes_customer_language(monkeypatch, locale, expected):
    from concierge.nodes.action_display import label
    card = {**CARD, "customer_locale": locale}
    monkeypatch.setattr(actions, "summarize", AsyncMock(return_value=card))
    s = {"selected_hospital_id": 7, "mode": "HOSPITAL",
         "user": {"user_id": 1, "locale": locale},
         "conversation_id": "ac55e772-a184-494d-8ca7-703ad4850360", "task_id": "task-1"}
    s["conditions"] = {"consult_language": "ja" if locale != "ja" else "en"}
    pending = await actions.prepare_action(s, {"id": "call-1", "name": actions.HANDOFF, "args": {}})
    assert {"label": label("customer_locale", locale), "value": expected} in pending["display"]["rows"]
    assert pending["args"]["summary_card"] == card
    assert pending["args"]["consent"] is False


def test_multiple_questions_become_numbered_lines():
    from concierge.nodes.action_display import question_lines, summary_rows
    qs = ["전문 의사가 있나요?", "상담원 연결이 되나요?"]
    assert question_lines(qs) == "1. 전문 의사가 있나요?\n2. 상담원 연결이 되나요?"
    assert question_lines(["하나뿐인 질문"]) == "하나뿐인 질문"      # 1개면 번호 없이
    assert question_lines([]) == ""
    rows = summary_rows({**CARD, "questions": qs}, "ko")
    assert {"label": "질문", "value": "1. 전문 의사가 있나요?\n2. 상담원 연결이 되나요?"} in rows


def test_missing_summary_language_is_not_invented():
    from concierge.nodes.action_display import label, summary_rows
    for value in (None, "unknown"):
        assert {"label": "Customer language", "value": label("unknown", "en")} in summary_rows(
            {**CARD, "customer_locale": value}, "en")
