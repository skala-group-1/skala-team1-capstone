"""Backend queue contract, graph state isolation and terminal SSE delivery."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langgraph.types import interrupt

from app.api.main import compile_hospital_chat
from app.graph.state import AgentState
from app.workers.consumer import HospitalWorker
from app.workers.messages import AiTaskRequested, AiTaskResume


def request(task="t1", thread="c1", hospital=1, **overrides):
    body = {
        "taskId": task, "conversationId": thread,
        "user": {"id": 3, "role": "CUSTOMER", "locale": "ko"},
        "message": "이 병원에 대해 알려줘", "action": None,
        "requestedAt": "2026-10-20T10:00:00+09:00",
        "conversation": {"mode": "HOSPITAL", "hospitalId": hospital, "parentConversationId": None},
    }
    return AiTaskRequested.model_validate({**body, **overrides})


def resume(approved=False):
    return AiTaskResume.model_validate({
        "taskId": "t1", "conversationId": "c1",
        "user": {"id": 3, "role": "CUSTOMER", "locale": "ko"},
        "approved": approved, "editedArgs": None, "reason": "취소",
    })


def setup_worker(node):
    builder = StateGraph(AgentState)
    builder.add_node("answer", node)
    builder.add_edge(START, "answer")
    builder.add_edge("answer", END)
    store = InMemoryStore()
    graph = builder.compile(checkpointer=MemorySaver(), store=store)
    publisher = AsyncMock()
    return HospitalWorker(graph, store, publisher), publisher


def events(publisher):
    return [call.args[0] for call in publisher.await_args_list]


async def test_backend_metadata_and_followup_stay_in_same_hospital():
    def answer(state):
        count = sum(m.type == "human" for m in state["messages"])
        return {"messages": [AIMessage(content=f"{state['selected_hospital_id']}:{count}")]}

    worker, publisher = setup_worker(answer)
    await worker.handle(request(), "trace")
    await worker.handle(request(task="t2"), "trace")
    await worker.handle(request(task="t3", thread="c2", hospital=2), "trace")
    replies = [e for e in events(publisher) if e.event == "DONE"]
    assert [e.data["answer"] for e in replies] == ["1:1", "1:2", "2:1"]
    assert [e.seq for e in events(publisher)] == [1, 2, 3, 1, 2, 3, 1, 2, 3]
    state = await worker.graph.aget_state({"configurable": {"thread_id": "c1"}})
    assert state.values["user"] == {"user_id": 3, "role": "CUSTOMER", "locale": "ko"}
    assert events(publisher)[0].at.utcoffset().total_seconds() == 9 * 3600


@pytest.mark.parametrize("changes", [
    {"conversation": None},
    {"conversation": {"mode": "HUMAN", "hospitalId": 1}},
    {"conversation": {"mode": "HOSPITAL"}},
    {"message": None},
    {"action": {"type": "SELECT_HOSPITAL", "hospitalId": 2}},
])
async def test_invalid_or_nonhospital_requests_fail_without_model(changes):
    node = AsyncMock()
    worker, publisher = setup_worker(node)
    await worker.handle(request(**changes))
    node.assert_not_awaited()
    assert [e.event for e in events(publisher)] == ["FAILED"]


async def test_same_thread_cannot_change_hospital_or_user():
    worker, publisher = setup_worker(lambda state: {"messages": [AIMessage(content="안녕하세요")]})
    await worker.handle(request())
    await worker.handle(request(task="t2", hospital=2))
    await worker.handle(request(task="t3", user={"id": 4, "role": "CUSTOMER", "locale": "ko"}))
    assert [e.event for e in events(publisher)] == ["STATUS", "TOKEN", "DONE", "FAILED", "FAILED"]


async def test_duplicate_task_replays_done_without_running_graph_again():
    node = AsyncMock(return_value={"messages": [AIMessage(content="답변")]})
    worker, publisher = setup_worker(node)
    await worker.handle(request())
    await worker.handle(request())
    assert node.await_count == 1
    assert [e.seq for e in events(publisher)] == [1, 2, 3, 3]


@pytest.mark.parametrize("approved", [False, True])
async def test_interrupt_resume_preserves_seq_and_decision(approved):
    decisions = []

    def node(state):
        decision = interrupt({"action": "CREATE_RESERVATION", "args": {}, "display": {}, "editable": ["note"]})
        decisions.append(decision)
        return {"messages": [AIMessage(content="접수하지 않았습니다.")]}

    worker, publisher = setup_worker(node)
    await worker.handle(request())
    # Recreate worker as on restart, keeping checkpointer/store.
    worker = HospitalWorker(worker.graph, worker.store, publisher)
    await worker.handle(resume(approved))
    emitted = events(publisher)
    assert [e.seq for e in emitted] == [1, 2, 3, 4, 5]
    assert emitted[1].event == "APPROVAL_REQUIRED"
    assert decisions[0]["approved"] is approved
    assert emitted[-1].event == "DONE"
    state = await worker.graph.aget_state({"configurable": {"thread_id": "c1"}})
    assert not state.next


async def test_timeout_and_provider_exception_are_sanitized(monkeypatch):
    async def slow(state):
        await asyncio.sleep(1)

    worker, publisher = setup_worker(slow)
    monkeypatch.setattr("app.workers.consumer.TASK_TIMEOUT_SECONDS", 0.01)
    await worker.handle(request(), "trace-id")
    assert events(publisher)[-1].event == "FAILED"
    assert events(publisher)[-1].data["traceId"] == "trace-id"
    node = AsyncMock(side_effect=RuntimeError("SECRET_PROVIDER_RESPONSE"))
    worker, publisher = setup_worker(node)
    await worker.handle(request())
    assert "SECRET" not in events(publisher)[-1].to_json().decode()


async def test_standalone_graph_returns_draft_without_main_agent(monkeypatch):
    async def hospital(state):
        return {"draft": f"병원 {state['selected_hospital_id']} 안내"}

    subgraph = StateGraph(AgentState)
    subgraph.add_node("hospital_answer", hospital)
    subgraph.add_edge(START, "hospital_answer")
    subgraph.add_edge("hospital_answer", END)
    monkeypatch.setattr("app.api.main.build_hospital_subgraph", lambda: subgraph)
    store = InMemoryStore()
    graph = compile_hospital_chat(MemorySaver(), store)
    publisher = AsyncMock()
    await HospitalWorker(graph, store, publisher).handle(request())
    assert events(publisher)[-1].data == {"answer": "병원 1 안내", "sources": []}


async def test_lifespan_starts_and_closes_worker(monkeypatch):
    from app.api.main import app, lifespan
    connection = SimpleNamespace(close=AsyncMock())
    start = AsyncMock(return_value=connection)
    monkeypatch.setattr("app.api.main.start_consumers", start)
    monkeypatch.setattr("app.harness.memory.get_settings", lambda: SimpleNamespace(database_url=""))
    async with lifespan(app):
        start.assert_awaited_once()
        assert app.state.graph is not None
    connection.close.assert_awaited_once()
