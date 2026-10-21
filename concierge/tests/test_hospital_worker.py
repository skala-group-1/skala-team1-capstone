"""Backend queue contract, graph state isolation and terminal SSE delivery."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langgraph.types import interrupt

from app.api.main import compile_hospital_chat
from app.graph.state import AgentState
from app.workers.consumer import EventDeliveryError, HospitalWorker
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


PARENT = "3ad36082-8034-4d36-bca0-7e3ce800978d"
CHILD = "c6d49de7-d0ab-4c99-a0d7-ec0880ac4995"
CHILD_CONFIG = {"configurable": {"thread_id": CHILD}}
CONDITIONS = {"procedure_code": "JAW_BOTOX", "date_from": "2026-10-22"}


def selection_request(task="select"):
    return request(task=task, thread=PARENT, message=None,
                   conversation={"mode": "MAIN"},
                   action={"type": "SELECT_HOSPITAL", "hospitalId": 1})


def opening_worker(*, opened_changes=None, pending=False):
    opened = {
        "conversation_id": CHILD, "hospital_id": 1, "mode": "HOSPITAL",
        "parent_conversation_id": PARENT, "consultation_id": None, "conditions": {},
        **(opened_changes or {}),
    }

    def prepare(state):
        if state["mode"] == "MAIN":
            return {"opened_conversation": opened, "selected_hospital_id": 1,
                    "conditions": CONDITIONS, "summary": "Selected from search results"}
        if pending:
            return {"pending_action": {"tool": "business_create_reservation", "args": {"slot_id": 9}}}
        return {}

    def respond(state):
        if pending and state["mode"] == "HOSPITAL":
            interrupt({"action": "CREATE_RESERVATION", "editable": [], "display": {}, "args": {}})
        return {"messages": [AIMessage(content=f"{state.get('conditions')} / {state.get('summary')}")]}

    builder = StateGraph(AgentState)
    builder.add_node("prepare", prepare)
    builder.add_node("respond", respond)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "respond")
    builder.add_edge("respond", END)
    store = InMemoryStore()
    publisher = AsyncMock()
    return HospitalWorker(builder.compile(checkpointer=MemorySaver(), store=store), store, publisher), publisher


@pytest.mark.parametrize("backend_conditions,parent,expected", [
    ({}, PARENT, CONDITIONS),
    (None, PARENT, CONDITIONS),
    ({"procedure_code": "SAVED"}, PARENT, {"procedure_code": "SAVED"}),
    ({}, None, {}),
    ({}, "ad4e13ce-968b-44dc-8f6c-c82ee792b6df", {}),
])
async def test_child_is_ready_before_open_event_and_first_message_inherits_context(monkeypatch, backend_conditions, parent, expected):
    worker, publisher = opening_worker(opened_changes={"conditions": backend_conditions, "parent_conversation_id": parent})

    async def publish(event, trace):
        if event.event == "CONVERSATION_OPENED":
            saved = await worker.graph.aget_state(CHILD_CONFIG)
            assert saved.values["conditions"] == expected
            assert saved.values["user"] == {"user_id": 3, "role": "CUSTOMER", "locale": "ko"}
            assert saved.values["mode"] == "HOSPITAL"
            assert saved.values["selected_hospital_id"] == 1
            assert saved.values["parent_conversation_id"] == parent
            assert not saved.values.get("messages") and not saved.next
            assert event.data == {"conversationId": CHILD, "hospitalId": 1}

    publisher.side_effect = publish
    await worker.handle(selection_request())
    assert events(publisher)[-1].event == "DONE"
    parent_snapshot = await worker.graph.aget_state({"configurable": {"thread_id": PARENT}})
    assert parent_snapshot.values["mode"] == "MAIN"
    # Enter the production graph with the saved child; only external work is stubbed.
    from app.graph import builder

    def hospital_reply(state):
        assert state["mode"] == "HOSPITAL" and state["selected_hospital_id"] == 1
        return {"draft": f"{state['conditions']} / {state['summary']}"}

    monkeypatch.setattr(builder, "load_hospital_context", lambda state: {})
    monkeypatch.setattr(builder, "hospital_agent", hospital_reply)
    worker.graph = builder.compile_graph(worker.graph.checkpointer, worker.store)
    await worker.handle(request(task="first-child", thread=CHILD,
                                conversation={"mode": "HOSPITAL", "hospitalId": 1, "parentConversationId": parent}))
    assert events(publisher)[-1].data["answer"] == f"{expected} / Selected from search results"
    saved = await worker.graph.aget_state(CHILD_CONFIG)
    assert [m.content for m in saved.values["messages"] if isinstance(m, HumanMessage)] == ["이 병원에 대해 알려줘"]


async def test_new_checkpoint_keeps_returned_human_mode_and_consultation():
    worker, publisher = opening_worker(opened_changes={"mode": "HUMAN", "consultation_id": 701})
    await worker.handle(selection_request())
    saved = await worker.graph.aget_state(CHILD_CONFIG)
    assert saved.values["mode"] == "HUMAN" and saved.values["consultation_id"] == 701
    assert events(publisher)[-1].event == "DONE"
    await worker.handle(request(task="stale-hospital-message", thread=CHILD))
    assert events(publisher)[-1].event == "FAILED"
    assert await worker.graph.aget_state(CHILD_CONFIG) == saved


@pytest.mark.parametrize("pending", [False, True])
async def test_reopening_child_preserves_entire_checkpoint_and_interrupt(pending):
    worker, publisher = opening_worker(pending=pending)
    await worker.graph.aupdate_state(CHILD_CONFIG, {
        "conditions": {"procedure_code": "SAVED"}, "summary": "Saved summary",
        "messages": [AIMessage(content="Saved message")],
    }, as_node="respond")
    await worker.handle(request(thread=CHILD))
    saved = await worker.graph.aget_state(CHILD_CONFIG)
    assert bool(saved.next) == pending
    if pending:
        assert saved.values["pending_action"] and saved.tasks[0].interrupts
    await worker.handle(selection_request())
    await worker.handle(selection_request(task="select-again"))
    assert await worker.graph.aget_state(CHILD_CONFIG) == saved
    assert len([e for e in events(publisher) if e.event == "CONVERSATION_OPENED"]) == 2


@pytest.mark.parametrize("changes", [
    {"user": {"user_id": 4}}, {"selected_hospital_id": 2},
    {"conversation_id": PARENT}, {"mode": "MAIN"},
])
async def test_child_checkpoint_identity_mismatch_fails_without_opening_or_overwrite(changes):
    worker, publisher = opening_worker()
    await worker.graph.aupdate_state(CHILD_CONFIG, {
        "user": {"user_id": 3}, "selected_hospital_id": 1,
        "conversation_id": CHILD, "mode": "HOSPITAL", **changes,
    }, as_node="respond")
    saved = await worker.graph.aget_state(CHILD_CONFIG)
    await worker.handle(selection_request())
    assert events(publisher)[-1].event == "FAILED"
    assert not any(e.event == "CONVERSATION_OPENED" for e in events(publisher))
    assert await worker.graph.aget_state(CHILD_CONFIG) == saved


@pytest.mark.parametrize("changes", [
    {"conversation_id": PARENT}, {"conversation_id": "not-a-uuid"},
    {"hospital_id": 2}, {"hospital_id": True}, {"mode": "MAIN"},
    {"user_id": 4}, {"conditions": "invalid"},
])
async def test_invalid_open_result_never_emits_opened(changes):
    worker, publisher = opening_worker(opened_changes=changes)
    await worker.handle(selection_request())
    assert events(publisher)[-1].event == "FAILED"
    assert not any(e.event == "CONVERSATION_OPENED" for e in events(publisher))
    assert not (await worker.graph.aget_state(CHILD_CONFIG)).values


async def test_child_checkpoint_save_failure_never_emits_opened(monkeypatch):
    worker, publisher = opening_worker()
    monkeypatch.setattr(worker.graph, "aupdate_state", AsyncMock(side_effect=ConnectionError()))
    await worker.handle(selection_request())
    assert events(publisher)[-1].event == "FAILED"
    assert not any(e.event == "CONVERSATION_OPENED" for e in events(publisher))


async def test_open_publish_failure_retry_does_not_reinitialize_child():
    worker, publisher = opening_worker()

    async def publish(event, trace):
        if event.event == "CONVERSATION_OPENED":
            raise ConnectionError()

    publisher.side_effect = publish
    with pytest.raises(EventDeliveryError):
        await worker.handle(selection_request())
    saved = await worker.graph.aget_state(CHILD_CONFIG)
    assert saved.values["conditions"] == CONDITIONS
    publisher.side_effect = None
    await worker.handle(selection_request())
    assert events(publisher)[-1].event == "FAILED"
    assert await worker.graph.aget_state(CHILD_CONFIG) == saved
