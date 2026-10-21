"""Opt-in isolated RabbitMQ transport + real graph, with fake model/mutation.

WORKER_TEST_RABBITMQ_URL must target a disposable broker: this test declares its
own backend-compatible topology. Never point it at the shared application broker.
"""

import asyncio
import os
from uuid import uuid4

import aio_pika
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langgraph.types import interrupt

from app.config import get_settings
from app.graph.state import AgentState
from app.workers.consumer import HospitalWorker, start_consumers
from app.workers.messages import AiTaskEvent, AiTaskRequested, AiTaskResume, Queue

URL = os.getenv("WORKER_TEST_RABBITMQ_URL")
pytestmark = pytest.mark.skipif(not URL, reason="isolated RabbitMQ URL not supplied")


async def test_real_broker_stream_resume_duplicate_restart_and_retry(monkeypatch):
    monkeypatch.setattr(get_settings(), "rabbitmq_url", URL)
    connection = await aio_pika.connect_robust(URL)
    consumers = None
    executions = []
    try:
        channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        exchange = await channel.declare_exchange("capstone.direct", aio_pika.ExchangeType.DIRECT, durable=True)
        for name in (Queue.AI_TASK_REQUESTED, Queue.AI_TASK_RESUME):
            queue = await channel.declare_queue(name, durable=True, arguments={
                "x-dead-letter-exchange": "capstone.direct", "x-dead-letter-routing-key": "ai.task.dlq",
            })
            await queue.bind(exchange, name)
            for suffix, ttl in (("5s", 5000), ("15s", 15000)):
                name_retry = f"{name}.retry.{suffix}"
                retry = await channel.declare_queue(name_retry, durable=True, arguments={
                    "x-message-ttl": ttl, "x-dead-letter-exchange": "capstone.direct", "x-dead-letter-routing-key": name,
                })
                await retry.bind(exchange, name_retry)
        output = await channel.declare_queue(Queue.AI_TASK_EVENT, durable=True)
        await output.bind(exchange, Queue.AI_TASK_EVENT)
        dead = await channel.declare_queue("ai.task.dlq", durable=True)
        await dead.bind(exchange, "ai.task.dlq")

        async def respond(state):
            if state["messages"][-1].content == "approval":
                decision = interrupt({"action": "CREATE_RESERVATION", "args": {}, "display": {}, "editable": ["note"]})
                executions.append(decision)
                return {"messages": [AIMessage(content="Approved test action")]}
            model = FakeListChatModel(responses=["hello"])
            return {"messages": [await model.ainvoke(state["messages"])]}

        builder = StateGraph(AgentState)
        builder.add_node("respond", respond)
        builder.add_edge(START, "respond")
        builder.add_edge("respond", END)
        store = InMemoryStore()
        graph = builder.compile(checkpointer=MemorySaver(), store=store)
        consumers = await start_consumers(graph, store)

        async def publish(model, queue):
            await exchange.publish(aio_pika.Message(body=model.to_json(), headers={"x-attempt": 0, "x-trace-id": model.task_id}), routing_key=queue)

        async def receive_terminal():
            received = []
            async with asyncio.timeout(15):
                async with output.iterator() as iterator:
                    async for incoming in iterator:
                        event = AiTaskEvent.model_validate_json(incoming.body)
                        await incoming.ack()
                        received.append(event)
                        if event.event in {"DONE", "FAILED", "APPROVAL_REQUIRED"}:
                            return received

        def request(message="hello", mode="MAIN"):
            return AiTaskRequested.model_validate({
                "taskId": str(uuid4()), "conversationId": str(uuid4()),
                "user": {"id": 1, "role": "CUSTOMER", "locale": "en"},
                "message": message, "requestedAt": "2026-10-21T10:00:00+09:00",
                "conversation": {"mode": mode, "hospitalId": 1 if mode == "HOSPITAL" else None},
            })

        for mode in ("MAIN", "HOSPITAL"):
            req = request(mode=mode)
            await publish(req, Queue.AI_TASK_REQUESTED)
            received = await receive_terminal()
            assert [e.seq for e in received] == list(range(1, 8))
            assert [e.data["text"] for e in received if e.event == "TOKEN"] == list("hello")
            assert received[-1].event == "DONE"
        await consumers.close()
        consumers = await start_consumers(graph, store)
        await publish(req, Queue.AI_TASK_REQUESTED)
        duplicate = await receive_terminal()
        assert len(duplicate) == 1 and duplicate[0].seq == 7

        req = request("approval", "HOSPITAL")
        await publish(req, Queue.AI_TASK_REQUESTED)
        paused = await receive_terminal()
        assert paused[-1].event == "APPROVAL_REQUIRED" and not executions
        await consumers.close()
        consumers = await start_consumers(graph, store)
        approval = AiTaskResume(task_id=req.task_id, conversation_id=req.conversation_id, user=req.user,
                                approved=True, edited_args={"note": "test"})
        await publish(approval, Queue.AI_TASK_RESUME)
        resumed = await receive_terminal()
        assert resumed[0].seq == paused[-1].seq + 1
        assert resumed[-1].event == "DONE" and len(executions) == 1
        await publish(approval, Queue.AI_TASK_RESUME)
        assert len(await receive_terminal()) == 1 and len(executions) == 1

        original = HospitalWorker.handle
        attempts = []

        async def transient(self, msg, trace_id=""):
            attempts.append(msg.task_id)
            if len(attempts) == 1:
                raise ConnectionError("test transient failure")
            await original(self, msg, trace_id)

        monkeypatch.setattr(HospitalWorker, "handle", transient)
        await publish(request(), Queue.AI_TASK_REQUESTED)
        assert (await receive_terminal())[-1].event == "DONE"
        assert len(attempts) == 2
        await exchange.publish(aio_pika.Message(body=b"invalid json"), routing_key=Queue.AI_TASK_REQUESTED)
        async with asyncio.timeout(5):
            async with dead.iterator() as iterator:
                async for incoming in iterator:
                    assert incoming.body == b"invalid json"
                    await incoming.ack()
                    break
    finally:
        if consumers:
            await consumers.close()
        await connection.close()
