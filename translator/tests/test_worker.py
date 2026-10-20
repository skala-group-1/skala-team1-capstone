"""워커: 결과 발행(camelCase, 헤더), 실패 시 재시도 규약 (x-attempt 0→retry.5s, 1→retry.15s, 2+→dlq)."""

import json

from app.messages import HEADER_ATTEMPT, HEADER_TRACE_ID, ChatTranslate
from app.translate import ChatTranslation
from app.worker import handle_chat_translate, retry_or_dead_letter, retry_target


class FakeExchange:
    def __init__(self):
        self.published = []

    async def publish(self, message, routing_key):
        self.published.append((routing_key, message))


class FakeChannel:
    def __init__(self):
        self.exchange = FakeExchange()

    async def get_exchange(self, name):
        return self.exchange


class FakeIncoming:
    def __init__(self, headers, body=b"{}"):
        self.headers = headers
        self.body = body


async def test_handle_chat_translate_publishes_result(fake_llm):
    fake_llm(ChatTranslation(translated_text="번역", is_medical_question=False))
    channel = FakeChannel()
    msg = ChatTranslate(message_id=7, consultation_id=1, text="hello", from_="en", to="ko")
    await handle_chat_translate(msg, "trace-1", channel)

    [(routing_key, message)] = channel.exchange.published
    assert routing_key == "chat.translated"
    assert message.headers[HEADER_TRACE_ID] == "trace-1"
    body = json.loads(message.body)
    assert body["messageId"] == 7 and body["ok"] is True and body["translatedText"] == "번역"


def test_retry_target_follows_backend_convention():
    assert retry_target("chat.translate", 0) == "chat.translate.retry.5s"
    assert retry_target("chat.translate", 1) == "chat.translate.retry.15s"
    assert retry_target("chat.translate", 2) == "chat.translate.dlq"


async def test_retry_republish_increments_attempt():
    channel = FakeChannel()
    incoming = FakeIncoming({HEADER_TRACE_ID: "t", HEADER_ATTEMPT: 0}, body=b'{"messageId":1}')
    await retry_or_dead_letter(channel, "chat.translate", incoming, RuntimeError("boom"))

    [(routing_key, message)] = channel.exchange.published
    assert routing_key == "chat.translate.retry.5s"
    assert message.headers[HEADER_ATTEMPT] == 1
    assert message.body == b'{"messageId":1}'          # 원문 그대로 재발행


async def test_retry_exhausted_goes_to_dlq():
    channel = FakeChannel()
    incoming = FakeIncoming({HEADER_ATTEMPT: 2})
    await retry_or_dead_letter(channel, "summary.translate", incoming, RuntimeError("boom"))
    [(routing_key, message)] = channel.exchange.published
    assert routing_key == "summary.translate.dlq"
    assert message.headers[HEADER_ATTEMPT] == 3
