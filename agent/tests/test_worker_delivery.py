"""AMQP ack/retry/shutdown boundaries without consuming shared queues."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.workers.consumer import Consumers, deliver
from app.workers.messages import AiTaskRequested, Queue


def message(attempt=0):
    return SimpleNamespace(
        body=b'{"taskId":"t","conversationId":"c","user":{"id":1,"role":"CUSTOMER","locale":"en"},"message":"hello","requestedAt":"2026-10-21T10:00:00+09:00","conversation":{"mode":"MAIN"}}',
        headers={"x-attempt": attempt, "x-trace-id": "trace"}, ack=AsyncMock(), nack=AsyncMock(),
    )


@pytest.mark.parametrize("attempt,target", [
    (0, "ai.task.requested.retry.5s"), (1, "ai.task.requested.retry.15s"), (2, "ai.task.dlq"),
])
async def test_retry_confirm_before_ack(attempt, target):
    incoming = message(attempt)
    worker = SimpleNamespace(handle=AsyncMock(side_effect=ConnectionError()))

    async def publish(msg, routing_key):
        incoming.ack.assert_not_awaited()
        assert routing_key == target
        assert msg.headers == {"x-attempt": attempt + 1, "x-trace-id": "trace"}
        assert msg.body == incoming.body

    exchange = SimpleNamespace(publish=AsyncMock(side_effect=publish))
    await deliver(incoming, AiTaskRequested, worker, exchange, Queue.AI_TASK_REQUESTED)
    incoming.ack.assert_awaited_once()
    incoming.nack.assert_not_awaited()


async def test_retry_publish_failure_nacks_original():
    incoming = message()
    worker = SimpleNamespace(handle=AsyncMock(side_effect=ConnectionError()))
    exchange = SimpleNamespace(publish=AsyncMock(side_effect=ConnectionError()))
    await deliver(incoming, AiTaskRequested, worker, exchange, Queue.AI_TASK_REQUESTED)
    incoming.nack.assert_awaited_once_with(requeue=True)
    incoming.ack.assert_not_awaited()


async def test_malformed_body_goes_directly_to_dlq_without_execution():
    incoming = message()
    incoming.body = b'{"taskId":"t"}'
    worker = SimpleNamespace(handle=AsyncMock())
    exchange = SimpleNamespace(publish=AsyncMock())
    await deliver(incoming, AiTaskRequested, worker, exchange, Queue.AI_TASK_RESUME)
    assert exchange.publish.call_args.kwargs["routing_key"] == "ai.task.dlq"
    worker.handle.assert_not_awaited()
    incoming.ack.assert_awaited_once()


async def test_cancellation_requeues_without_ack():
    incoming = message()
    worker = SimpleNamespace(handle=AsyncMock(side_effect=asyncio.CancelledError()))
    with pytest.raises(asyncio.CancelledError):
        await deliver(incoming, AiTaskRequested, worker, SimpleNamespace(publish=AsyncMock()), Queue.AI_TASK_RESUME)
    incoming.nack.assert_awaited_once_with(requeue=True)
    incoming.ack.assert_not_awaited()


async def test_shutdown_cancels_consumers_then_drains_active_delivery():
    connection = SimpleNamespace(close=AsyncMock())
    consumers = Consumers(connection)
    queue = SimpleNamespace(cancel=AsyncMock())
    consumers.subscriptions.append((queue, "tag"))
    finish = asyncio.Event()
    task = asyncio.create_task(finish.wait())
    consumers.active.add(task)
    closing = asyncio.create_task(consumers.close())
    await asyncio.sleep(0)
    queue.cancel.assert_awaited_once_with("tag")
    connection.close.assert_not_awaited()
    finish.set()
    await closing
    connection.close.assert_awaited_once()
