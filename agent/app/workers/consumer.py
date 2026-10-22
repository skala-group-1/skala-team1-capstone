"""One serialized AI consumer for MAIN/HOSPITAL tasks and approval resumes."""

import asyncio
import json
import logging
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import aio_pika
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import ValidationError

from app.config import get_settings
from app.mcp_client.client import mcp_request_context
from app.workers.events import SseEvent, TERMINAL_EVENTS, camel, state_events
from app.workers.messages import AiTaskEvent, AiTaskRequested, AiTaskResume, Queue
from coordinator.nodes.coordinator_tools import summarizer_handoff_summary

logger = logging.getLogger(__name__)
handoff_logger = logging.getLogger("uvicorn.error.handoff")
# Keep the existing namespace so deployed task receipts survive this upgrade.
TASK_NAMESPACE = ("hospital_worker", "tasks")
TASK_TIMEOUT_SECONDS = 120
UNAVAILABLE = {
    "ko": "현재 요청을 처리할 수 없습니다. 잠시 후 다시 시도해 주세요.",
    "en": "This request could not be completed. Please try again shortly.",
    "zh": "暂时无法处理此请求，请稍后重试。",
    "ja": "現在このリクエストを処理できません。しばらくしてから再試行してください。",
}
TOOL_LABEL = {"ko": "정보 확인 중…", "en": "Checking information…", "zh": "正在查询信息…", "ja": "情報を確認中…"}


class EventDeliveryError(Exception):
    """Retry the receipt/event publication, never re-run a completed mutation."""


class HospitalWorker:
    def __init__(self, graph, store, publish):
        self.graph = graph
        self.store = store
        self.publish = publish
        # shortcut: one worker process, add distributed thread locks before scaling replicas.
        self.lock = asyncio.Lock()

    def _log_handoff(self, msg, conversation_id, saved, outcome):
        if not get_settings().handoff_debug_log:
            return
        # JSON escapes user-supplied newlines/control characters. Log only the
        # context actually saved, never credentials or the full graph state.
        handoff_logger.info("MAIN_TO_HOSPITAL %s", json.dumps({
            "outcome": outcome, "taskId": msg.task_id,
            "sourceConversationId": msg.conversation_id,
            "hospitalConversationId": conversation_id,
            "hospitalId": saved.get("selected_hospital_id"),
            "mode": saved.get("mode"),
            "conditions": saved.get("conditions") or {},
            "summary": saved.get("summary"),
        }, ensure_ascii=False))

    async def _emit(self, msg, record, event, data, trace_id):
        record["seq"] += 1
        payload = AiTaskEvent(
            task_id=msg.task_id, seq=record["seq"], event=event, data=data,
            at=datetime.now(ZoneInfo("Asia/Seoul")),
        )
        record["lastEvent"] = payload.model_dump(mode="json", by_alias=True)
        record["status"] = event if event in TERMINAL_EVENTS else SseEvent.STATUS
        try:
            # Save first: a lost publisher confirmation replays the same seq.
            await self.store.aput(TASK_NAMESPACE, msg.task_id, record)
            await self.publish(payload, trace_id)
        except Exception as exc:
            raise EventDeliveryError from exc

    async def _failed(self, msg, record, trace_id):
        await self._emit(msg, record, SseEvent.FAILED, {
            "code": "AI_UNAVAILABLE", "message": UNAVAILABLE[msg.user.locale],
            "traceId": trace_id or msg.task_id,
        }, trace_id)

    async def _initialize_child(self, msg, opened, state):
        conversation_id = opened["conversation_id"]
        hospital_id = opened["hospital_id"]
        if (not isinstance(conversation_id, str) or str(UUID(conversation_id)) != conversation_id
                or conversation_id == msg.conversation_id):
            raise ValueError("Invalid child conversation")
        if (type(hospital_id) is not int or hospital_id <= 0
                or hospital_id != state.get("selected_hospital_id")
                or opened["mode"] not in ("HOSPITAL", "HUMAN")):
            raise ValueError("Invalid child hospital/mode")
        action = getattr(msg, "action", None) or {}
        if action.get("type") == "SELECT_HOSPITAL" and hospital_id != action.get("hospitalId"):
            raise ValueError("Child selection mismatch")
        if opened.get("user_id", msg.user.id) != msg.user.id:
            raise ValueError("Child owner mismatch")
        config = {"configurable": {"thread_id": conversation_id}}
        snapshot = await self.graph.aget_state(config)
        if snapshot.config["configurable"].get("checkpoint_id"):
            existing = snapshot.values
            if ((existing.get("user") or {}).get("user_id") != msg.user.id
                    or existing.get("selected_hospital_id") != hospital_id
                    or existing.get("conversation_id", conversation_id) != conversation_id
                    or existing.get("mode") not in ("HOSPITAL", "HUMAN")):
                raise ValueError("Child checkpoint identity mismatch")
            # Refresh the handoff without touching hospital history or an active approval.
            outcome = "preserved"
            if (not snapshot.next and existing.get("mode") == opened["mode"] == "HOSPITAL"
                    and state.get("summary") and existing.get("summary") != state["summary"]):
                await self.graph.aupdate_state(config, {"summary": state["summary"]}, as_node="respond")
                existing = {**existing, "summary": state["summary"]}
                outcome = "summary_refreshed"
            self._log_handoff(msg, conversation_id, existing, outcome)
            return
        conditions = opened["conditions"]
        if conditions is not None and not isinstance(conditions, dict):
            raise ValueError("Invalid child conditions")
        if not conditions and opened["parent_conversation_id"] == msg.conversation_id:
            conditions = state.get("conditions")
        # The terminal node seeds state without scheduling a turn or running a model.
        await self.graph.aupdate_state(config, {
            "conversation_id": conversation_id,
            "user": {"user_id": msg.user.id, "role": msg.user.role, "locale": msg.user.locale},
            "mode": opened["mode"], "selected_hospital_id": hospital_id,
            "parent_conversation_id": opened["parent_conversation_id"],
            "consultation_id": opened["consultation_id"],
            "conditions": conditions or {}, "summary": state.get("summary"),
        }, as_node="respond")
        saved = await self.graph.aget_state(config)
        self._log_handoff(msg, conversation_id, saved.values, "initialized")

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
            if previous and previous != SseEvent.APPROVAL_REQUIRED:
                # An interrupted delivery may have made a remote mutation already.
                await self._failed(msg, record, trace_id)
                return
            config = {"configurable": {"thread_id": msg.conversation_id}}
            snapshot = await self.graph.aget_state(config)
            try:
                if msg.user.role != "CUSTOMER":
                    raise ValueError("Only customer tasks are supported")
                owner = (snapshot.values.get("user") or {}).get("user_id")
                if owner is not None and owner != msg.user.id:
                    raise ValueError("Conversation owner mismatch")
                if resume:
                    if previous != SseEvent.APPROVAL_REQUIRED or not snapshot.next:
                        raise ValueError("No pending approval")
                    allowed = record["lastEvent"]["data"].get("editable") or []
                    if set(msg.edited_args or {}) - set(allowed):
                        raise ValueError("Non-editable approval argument")
                    payload = Command(resume={
                        "approved": msg.approved, "editedArgs": msg.edited_args or {}, "reason": msg.reason,
                    })
                else:
                    conv = msg.conversation
                    if not conv or conv.mode not in ("MAIN", "HOSPITAL", "AFTERCARE"):
                        raise ValueError("Expected an AI conversation")
                    if conv.mode in ("HOSPITAL", "AFTERCARE") and not conv.hospital_id:
                        raise ValueError("Missing hospital")
                    if not msg.action and not (msg.message or "").strip():
                        raise ValueError("Expected message or action")
                    if conv.mode == "HOSPITAL" and msg.action:
                        raise ValueError("Unsupported hospital action")
                    if conv.mode == "AFTERCARE" and msg.action and msg.action.get("type") != "AFTERCARE_INTRO":
                        raise ValueError("Unsupported aftercare action")
                    if snapshot.next:
                        raise ValueError("Conversation is waiting for an earlier task")
                    selected = snapshot.values.get("selected_hospital_id")
                    # Backend rejects HUMAN tasks; older queued HOSPITAL tasks must stay rejected.
                    returning = (snapshot.values.get("mode") == "HUMAN" and conv.mode in ("HOSPITAL", "AFTERCARE")
                                 and owner == msg.user.id and selected == conv.hospital_id
                                 and snapshot.created_at is not None
                                 and msg.requested_at > datetime.fromisoformat(snapshot.created_at))
                    if snapshot.values.get("mode", conv.mode) != conv.mode and not returning:
                        raise ValueError("Conversation mode mismatch")
                    if conv.mode in ("HOSPITAL", "AFTERCARE") and selected is not None and selected != conv.hospital_id:
                        raise ValueError("Conversation hospital mismatch")
                    payload = {
                        "task_id": msg.task_id, "conversation_id": msg.conversation_id,
                        "action": msg.action,
                        "user": {"user_id": msg.user.id, "role": msg.user.role, "locale": msg.user.locale},
                        "mode": conv.mode, "selected_hospital_id": conv.hospital_id,
                        "parent_conversation_id": conv.parent_conversation_id,
                        "messages": [HumanMessage(content=msg.message, id=msg.task_id)] if msg.message else [],
                        "draft": None, "citations": [], "pending_action": None,
                        "opened_conversation": None, "memory_proposal": None,
                        "verify_passed": None, "verify_attempts": 0,
                    }
                    # Hospital-detail entry creates the backend session without SELECT_HOSPITAL.
                    if conv.mode == "HOSPITAL" and conv.parent_conversation_id and not snapshot.values:
                        parent = await self.graph.aget_state({"configurable": {
                            "thread_id": conv.parent_conversation_id}})
                        if parent.values:
                            if ((parent.values.get("user") or {}).get("user_id") != msg.user.id
                                    or parent.values.get("mode") != "MAIN"):
                                raise ValueError("Parent conversation identity mismatch")
                            conditions = parent.values.get("conditions") or {}
                            prepared = await summarizer_handoff_summary(parent.values, conv.hospital_id,
                                [{"id": conv.hospital_id}], conditions)
                            payload.update({"conditions": conditions, "summary": prepared["summary"]})
            except (ValueError, TypeError, KeyError) as exc:
                logger.warning("Rejected task %s (%s)", msg.task_id, type(exc).__name__)
                await self._failed(msg, record, trace_id)
                return

            await self._emit(msg, record, SseEvent.STATUS, {"status": "RUNNING"}, trace_id)
            try:
                with mcp_request_context(msg.user.id, msg.user.locale, trace_id or msg.task_id):
                    async with asyncio.timeout(TASK_TIMEOUT_SECONDS):
                        await self._stream(msg, record, payload, config, snapshot.values, trace_id)
            except EventDeliveryError:
                raise
            except Exception as exc:
                # Provider exception text can contain prompts, tool results or secrets.
                logger.warning("Task %s failed (%s)", msg.task_id, type(exc).__name__)
                await self._failed(msg, record, trace_id)

    async def _stream(self, msg, record, payload, config, initial, trace_id):
        state = dict(initial)
        seen = set()
        calls = {call["id"]: call["name"]
                 for message in initial.get("messages") or [] if isinstance(message, AIMessage)
                 for call in message.tool_calls}
        streamed = ""
        pending = None
        async for namespace, mode, chunk in self.graph.astream(
            payload, config, stream_mode=["messages", "updates"], subgraphs=True,
        ):
            if mode == "messages":
                message, metadata = chunk
                # Internal drafts may fail verification or contain tool-call reasoning.
                if (metadata.get("langgraph_node") == "respond" and isinstance(message, AIMessage)
                        and not message.tool_calls and isinstance(message.content, str) and message.content):
                    streamed += message.content
                    await self._emit(msg, record, SseEvent.TOKEN, {"text": message.content}, trace_id)
                continue
            for node, update in chunk.items():
                if node == "__interrupt__":
                    if update:
                        pending = update[0].value
                    continue
                if not isinstance(update, dict):
                    continue
                state.update(update)
                if update.get("opened_conversation"):
                    await self._initialize_child(msg, update["opened_conversation"], state)
                outgoing = [(event, data, None) for event, data in state_events(update, state)]
                for message in update.get("messages") or []:
                    if isinstance(message, AIMessage):
                        for call in message.tool_calls:
                            calls[call["id"]] = call["name"]
                            outgoing.append((SseEvent.TOOL_START, {
                                "tool": call["name"], "label": TOOL_LABEL[msg.user.locale],
                            }, call["id"]))
                    elif isinstance(message, ToolMessage) and message.tool_call_id in calls:
                        outgoing.append((SseEvent.TOOL_END, {
                            "tool": calls[message.tool_call_id], "ok": message.status != "error",
                        }, message.tool_call_id))
                for event, data, call_id in outgoing:
                    # Nested subgraphs also surface their merged update at the parent.
                    key = (event, call_id, json.dumps(data, sort_keys=True, ensure_ascii=False))
                    if key not in seen:
                        seen.add(key)
                        await self._emit(msg, record, event, data, trace_id)
        if pending is not None:
            await self._emit(msg, record, SseEvent.APPROVAL_REQUIRED, pending, trace_id)
            return
        snapshot = await self.graph.aget_state(config)
        result = snapshot.values
        last = (result.get("messages") or [None])[-1]
        if (not isinstance(last, AIMessage) or last.tool_calls
                or not isinstance(last.content, str) or not last.content.strip()):
            raise ValueError("Graph did not produce a final answer")
        previous = (initial.get("messages") or [None])[-1]
        if previous is not None and last.id == previous.id:
            raise ValueError("Graph returned a stale answer")
        if not streamed:
            await self._emit(msg, record, SseEvent.TOKEN, {"text": last.content}, trace_id)
        await self._emit(msg, record, SseEvent.DONE, {
            "answer": last.content, "sources": camel(result.get("citations") or []),
        }, trace_id)


async def deliver(message, model, worker, exchange, queue_name):
    """Confirm retry publication before acknowledging the original delivery."""
    try:
        msg = model.model_validate_json(message.body)
        await worker.handle(msg, (message.headers or {}).get("x-trace-id", ""))
    except asyncio.CancelledError:
        await message.nack(requeue=True)
        raise
    except Exception as exc:
        headers = dict(message.headers or {})
        raw = headers.get("x-attempt", 0)
        attempt = raw if isinstance(raw, int) and raw >= 0 else 0
        target = (f"{queue_name}.retry.5s" if attempt == 0 else f"{queue_name}.retry.15s")
        if attempt >= 2 or isinstance(exc, (ValidationError, ValueError)):
            target = "ai.task.dlq"
        headers["x-attempt"] = attempt + 1
        logger.warning("Delivery on %s failed (%s), target %s", queue_name, type(exc).__name__, target)
        try:
            await exchange.publish(aio_pika.Message(
                body=message.body, content_type="application/json", headers=headers,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ), routing_key=target)
        except Exception:
            await message.nack(requeue=True)
            return
    await message.ack()


class Consumers:
    def __init__(self, connection):
        self.connection = connection
        self.subscriptions = []
        self.active = set()

    async def close(self):
        try:
            for queue, tag in self.subscriptions:
                await queue.cancel(tag)
            if self.active:
                await asyncio.gather(*self.active, return_exceptions=True)
        finally:
            await self.connection.close()


async def start_consumers(graph, store):
    """Backend owns topology; never declare a competing queue or MAIN consumer."""
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    consumers = Consumers(connection)
    try:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        await channel.set_qos(prefetch_count=1)
        exchange = await channel.get_exchange(settings.rabbitmq_exchange)

        async def publish(event, trace_id):
            await exchange.publish(aio_pika.Message(
                body=event.to_json(), content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={"x-trace-id": trace_id, "x-attempt": 0},
            ), routing_key=Queue.AI_TASK_EVENT)

        worker = HospitalWorker(graph, store, publish)
        for queue_name, model in (
            (Queue.AI_TASK_REQUESTED, AiTaskRequested), (Queue.AI_TASK_RESUME, AiTaskResume),
        ):
            queue = await channel.get_queue(queue_name)

            async def on_message(message, model=model, queue_name=queue_name):
                task = asyncio.current_task()
                consumers.active.add(task)
                try:
                    await deliver(message, model, worker, exchange, queue_name)
                finally:
                    consumers.active.discard(task)

            tag = await queue.consume(on_message)
            consumers.subscriptions.append((queue, tag))
        return consumers
    except BaseException:
        await consumers.close()
        raise
