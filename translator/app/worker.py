"""큐 소비·발행 (aio-pika). exchange capstone.direct, routing key = 큐 이름.

큐·exchange 는 여기서 **선언하지 않는다** — backend 가 기동 시 전부 선언한다 (재시도·DLQ 포함).
처리 실패 시 backend RetryRepublisher 와 같은 규약: x-attempt 0 → {큐}.retry.5s, 1 → {큐}.retry.15s,
그 이상 → {큐}.dlq. 재발행 시 x-attempt 를 +1 한다 (TTL 후 원래 큐 복귀는 토폴로지가 처리).
"""

import logging

import aio_pika

from app.config import get_settings
from app.messages import (
    EXCHANGE,
    HEADER_ATTEMPT,
    HEADER_TRACE_ID,
    CamelModel,
    ChatTranslate,
    Queue,
    SummaryTranslate,
)
from app.translate import translate_chat, translate_summary

log = logging.getLogger(__name__)

PREFETCH_COUNT = 2


async def handle_chat_translate(msg: ChatTranslate, trace_id: str,
                                channel: aio_pika.abc.AbstractChannel) -> None:
    await publish(channel, Queue.CHAT_TRANSLATED, await translate_chat(msg), trace_id)


async def handle_summary_translate(msg: SummaryTranslate, trace_id: str,
                                   channel: aio_pika.abc.AbstractChannel) -> None:
    await publish(channel, Queue.SUMMARY_TRANSLATED, await translate_summary(msg), trace_id)


HANDLERS = {
    Queue.CHAT_TRANSLATE: (ChatTranslate, handle_chat_translate),
    Queue.SUMMARY_TRANSLATE: (SummaryTranslate, handle_summary_translate),
}


async def publish(channel: aio_pika.abc.AbstractChannel, routing_key: str, body: CamelModel,
                  trace_id: str, attempt: int = 0) -> None:
    exchange = await channel.get_exchange(EXCHANGE)
    message = aio_pika.Message(
        body=body.to_json(),
        content_type="application/json",
        headers={HEADER_TRACE_ID: trace_id, HEADER_ATTEMPT: attempt},
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await exchange.publish(message, routing_key=routing_key)


def retry_target(queue_name: str, attempt: int) -> str:
    if attempt == 0:
        return f"{queue_name}.retry.5s"
    if attempt == 1:
        return f"{queue_name}.retry.15s"
    return f"{queue_name}.dlq"


async def retry_or_dead_letter(channel: aio_pika.abc.AbstractChannel, queue_name: str,
                               message: aio_pika.abc.AbstractIncomingMessage, cause: Exception) -> None:
    headers = dict(message.headers or {})
    raw = headers.get(HEADER_ATTEMPT, 0)
    attempt = int(raw) if isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.isdigit()) else 0
    target = retry_target(queue_name, attempt)
    headers[HEADER_ATTEMPT] = attempt + 1
    log.warning("message on %s failed (attempt %s), moving to %s: %r", queue_name, attempt, target, cause)
    exchange = await channel.get_exchange(EXCHANGE)
    await exchange.publish(
        aio_pika.Message(body=message.body, content_type="application/json", headers=headers,
                         delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=target,
    )


async def start_consumers() -> aio_pika.abc.AbstractRobustConnection:
    """큐마다 consumer 를 붙이고 연결을 돌려준다 (종료 시 close)."""
    connection = await aio_pika.connect_robust(get_settings().rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=PREFETCH_COUNT)
    for queue_name, (model, handler) in HANDLERS.items():
        queue = await channel.get_queue(queue_name)

        async def on_message(message: aio_pika.abc.AbstractIncomingMessage,
                             queue_name=queue_name, model=model, handler=handler):
            async with message.process(requeue=False):
                trace_id = (message.headers or {}).get(HEADER_TRACE_ID, "")
                try:
                    await handler(model.model_validate_json(message.body), trace_id, channel)
                except Exception as e:  # noqa: BLE001 — 재시도 규약으로 넘긴다
                    await retry_or_dead_letter(channel, queue_name, message, e)

        await queue.consume(on_message)
    return connection
