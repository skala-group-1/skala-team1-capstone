"""큐 메시지가 「공통 계약서」 7장대로 camelCase JSON 으로 오가는지 (agent/tests/test_messages.py 와 같은 기준)."""

import json

from app.messages import ChatTranslate, ChatTranslated, SummaryTranslate, SummaryTranslated


def test_chat_translate_from_alias_roundtrip():
    msg = ChatTranslate.model_validate_json(
        '{"messageId":1,"consultationId":2,"text":"t","from":"zh","to":"ko"}')
    assert msg.from_ == "zh" and msg.message_id == 1
    assert json.loads(msg.to_json())["from"] == "zh"


def test_chat_translated_serializes_camel_case():
    out = json.loads(ChatTranslated(message_id=1, ok=True, translated_text="x",
                                    flags=["NUMBER_MISMATCH"]).to_json())
    assert set(out) == {"messageId", "ok", "translatedText", "flags", "error"}
    assert out["translatedText"] == "x" and out["flags"] == ["NUMBER_MISMATCH"]


def test_summary_translate_roundtrip():
    body = {"consultationId": 3, "summaryCard": {"procedure": "jaw botox"}, "from": "en", "to": "ko"}
    msg = SummaryTranslate.model_validate_json(json.dumps(body))
    assert msg.from_ == "en" and msg.summary_card["procedure"] == "jaw botox"
    out = json.loads(SummaryTranslated(consultation_id=3, ok=True,
                                       summary_card_ko={"procedure": "사각턱 보톡스"}).to_json())
    assert set(out) == {"consultationId", "ok", "summaryCardKo"}
