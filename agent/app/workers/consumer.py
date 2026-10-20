"""Hospital chat adapter: backend queue → graph → backend SSE events.

This development worker owns the two AI task queues, not the translation queues.
Do not run a separate MAIN consumer on the same queue: RabbitMQ load-balances
messages, rather than routing by conversation.mode.
"""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aio_pika
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from app.config import get_settings
from app.mcp_client.client import mcp_request_context
from app.workers.events import SseEvent
from app.workers.messages import AiTaskEvent, AiTaskRequested, AiTaskResume, Queue

logger = logging.getLogger(__name__)
TASK_NAMESPACE = ("hospital_worker", "tasks")
TASK_TIMEOUT_SECONDS = 120
UNAVAILABLE = {
    "ko": "현재 요청을 처리할 수 없습니다. 잠시 후 다시 시도해 주세요.",
    "en": "This request could not be completed. Please try again shortly.",
    "zh": "暂时无法处理此请求，请稍后重试。",
    "ja": "現在このリクエストを処理できません。しばらくしてから再試行してください。",
}
BOOKING_UNAVAILABLE = {
    "ko": "예약 저장 기능은 아직 연결되지 않았습니다. 예약은 접수되지 않았어요.",
    "en": "Reservation submission is not connected yet. No reservation was submitted.",
    "zh": "预约提交功能尚未连接，未提交任何预约。",
    "ja": "予約送信機能はまだ接続されていません。予約は送信されていません。",
}


class HospitalWorker:
    def __init__(self, graph, store, publish):
        self.graph = graph
        self.store = store
        self.publish = publish
        # Serialize requested/resume consumers sharing a thread. Run one instance
        # until distributed task locking is implemented.
        self.lock = asyncio.Lock()

    async def _emit(self, msg, record, event, data, trace_id):
        record["seq"] += 1
        payload = AiTaskEvent(
            task_id=msg.task_id, seq=record["seq"], event=event, data=data,
            at=datetime.now(ZoneInfo("Asia/Seoul")),
        )
        record["lastEvent"] = payload.model_dump(mode="json", by_alias=True)
        record["status"] = event
        # Persist before publishing so redelivery can replay a terminal event.
        await self.store.aput(TASK_NAMESPACE, msg.task_id, record)
        await self.publish(payload, trace_id)

    async def _failed(self, msg, record, trace_id, message=None):
        await self._emit(msg, record, SseEvent.FAILED, {
            "code": "AI_UNAVAILABLE",
            "message": message or UNAVAILABLE[msg.user.locale],
            "traceId": trace_id or msg.task_id,
        }, trace_id)

    async def handle(self, msg, trace_id=""):
        async with self.lock:
            item = await self.store.aget(TASK_NAMESPACE, msg.task_id)
            record = dict(item.value) if item else {
                "seq": 0, "userId": msg.user.id, "conversationId": msg.conversation_id,
            }
            if (record["userId"], record["conversationId"]) != (msg.user.id, msg.conversation_id):
                raise ValueError("Task owner/conversation mismatch")
            previous = record.get("status")
            resume = isinstance(msg, AiTaskResume)
            if previous in (SseEvent.DONE, SseEvent.FAILED) or (
                previous == SseEvent.APPROVAL_REQUIRED and not resume
            ):
                await self.publish(AiTaskEvent.model_validate(record["lastEvent"]), trace_id)
                return
            # Never automatically execute a partially completed delivery twice.
            if previous == SseEvent.STATUS:
                await self._failed(msg, record, trace_id)
                return
            config = {"configurable": {"thread_id": msg.conversation_id}}
            blocked_approval = False
            try:
                snapshot = await self.graph.aget_state(config)
                owner = (snapshot.values.get("user") or {}).get("user_id")
                if owner is not None and owner != msg.user.id:
                    raise ValueError("Conversation owner mismatch")
                if resume:
                    if previous != SseEvent.APPROVAL_REQUIRED or not snapshot.next:
                        raise ValueError("No pending approval")
                    # execute_action is a placeholder. Never run its fake success
                    # path from the web; settle the interrupt as rejected instead.
                    blocked_approval = msg.approved
                    payload = Command(resume={
                        "approved": False, "editedArgs": {},
                        "reason": BOOKING_UNAVAILABLE[msg.user.locale] if msg.approved else msg.reason,
                    })
                else:
                    conv = msg.conversation
                    if not conv or conv.mode != "HOSPITAL" or not conv.hospital_id:
                        raise ValueError("This worker handles hospital conversations only")
                    if msg.action or not msg.message or not msg.message.strip():
                        raise ValueError("Expected hospital chat text")
                    if snapshot.next:
                        raise ValueError("Conversation is waiting for an earlier task")
                    selected = snapshot.values.get("selected_hospital_id")
                    if selected is not None and selected != conv.hospital_id:
                        raise ValueError("Conversation hospital mismatch")
                    payload = {
                        "user": {"user_id": msg.user.id, "role": msg.user.role, "locale": msg.user.locale},
                        "mode": "HOSPITAL", "selected_hospital_id": conv.hospital_id,
                        "parent_conversation_id": conv.parent_conversation_id,
                        "messages": [HumanMessage(content=msg.message, id=msg.task_id)],
                        "draft": None, "citations": [],
                    }
            except Exception as exc:
                logger.warning("Rejected task %s (%s)", msg.task_id, type(exc).__name__)
                await self._failed(msg, record, trace_id)
                return

            await self._emit(msg, record, SseEvent.STATUS, {"status": "RUNNING"}, trace_id)
            try:
                with mcp_request_context(msg.user.id, msg.user.locale, trace_id or msg.task_id):
                    result = await asyncio.wait_for(
                        self.graph.ainvoke(payload, config), timeout=TASK_TIMEOUT_SECONDS,
                    )
                if blocked_approval:
                    terminal = (SseEvent.FAILED, {
                        "code": "AI_UNAVAILABLE", "message": BOOKING_UNAVAILABLE[msg.user.locale],
                        "traceId": trace_id or msg.task_id,
                    })
                elif result.get("__interrupt__"):
                    terminal = (SseEvent.APPROVAL_REQUIRED, result["__interrupt__"][0].value)
                else:
                    last = (result.get("messages") or [None])[-1]
                    if not isinstance(last, AIMessage) or last.tool_calls or not isinstance(last.content, str):
                        raise ValueError("Graph did not produce a final answer")
                    if not last.content.strip():
                        raise ValueError("Graph returned an empty answer")
                    sources = [
                        {"docId": c["doc_id"], "section": c["section"], "title": c["title"],
                         "uri": c["uri"], "snippet": c.get("snippet", "")}
                        for c in result.get("citations") or []
                    ]
                    terminal = (SseEvent.DONE, {"answer": last.content, "sources": sources})
            except Exception as exc:
                # Never log prompts, tool results, secrets or provider exception text.
                logger.warning("Task %s failed (%s)", msg.task_id, type(exc).__name__)
                await self._failed(
                    msg, record, trace_id,
                    BOOKING_UNAVAILABLE[msg.user.locale] if blocked_approval else None,
                )
                return
            await self._emit(msg, record, *terminal, trace_id)


async def start_consumers(graph, store):
    """Attach only AI queues; backend owns queue declarations and DLQ arguments."""
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        exchange = await channel.get_exchange(settings.rabbitmq_exchange)

        async def publish(event, trace_id):
            await exchange.publish(
                aio_pika.Message(
                    body=event.to_json(), content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    headers={"x-trace-id": trace_id, "x-attempt": 0},
                ),
                routing_key=Queue.AI_TASK_EVENT,
            )

        worker = HospitalWorker(graph, store, publish)
        for queue_name, model in (
            (Queue.AI_TASK_REQUESTED, AiTaskRequested),
            (Queue.AI_TASK_RESUME, AiTaskResume),
        ):
            queue = await channel.get_queue(queue_name)

            async def on_message(message, model=model):
                async with message.process(requeue=False):
                    msg = model.model_validate_json(message.body)
                    await worker.handle(msg, (message.headers or {}).get("x-trace-id", ""))

            await queue.consume(on_message)
        return connection
    except BaseException:
        await connection.close()
        raise
