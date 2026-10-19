"""큐 메시지가 12 문서 7장대로 camelCase JSON 으로 오가는지."""

import json

from app.workers.messages import AiTaskEvent, AiTaskRequested, ChatTranslate, ChatTranslated


def test_task_requested_parses_camel_case():
    body = {"taskId": "t-1", "conversationId": "c-1", "user": {"id": 1, "role": "CUSTOMER", "locale": "zh"},
            "message": "双眼皮", "action": None, "requestedAt": "2026-10-19T21:00:00+09:00"}
    msg = AiTaskRequested.model_validate_json(json.dumps(body))
    assert msg.task_id == "t-1" and msg.user.locale == "zh"


def test_event_serializes_camel_case():
    out = json.loads(AiTaskEvent(task_id="t-1", seq=1, event="TOKEN", data={"text": "hi"},
                                 at="2026-10-19T21:00:00+09:00").to_json())
    assert set(out) == {"taskId", "seq", "event", "data", "at"}


def test_chat_translate_from_alias():
    msg = ChatTranslate.model_validate_json('{"messageId":1,"consultationId":2,"text":"t","from":"zh","to":"ko"}')
    assert msg.from_ == "zh"
    assert json.loads(msg.to_json())["from"] == "zh"
    assert json.loads(ChatTranslated(message_id=1, ok=True, translated_text="x").to_json())["translatedText"] == "x"
