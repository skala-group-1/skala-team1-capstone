"""Real LangGraph streams with deterministic model/tools; no live LLM or DB claims."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langgraph.types import interrupt

from app.graph.state import AgentState
from app.workers.consumer import EventDeliveryError, HospitalWorker, TASK_NAMESPACE
from app.workers.messages import AiTaskRequested, AiTaskResume


def request(task="t", **kwargs):
    return AiTaskRequested.model_validate({
        "taskId": task, "conversationId": "thread",
        "user": {"id": 1, "role": "CUSTOMER", "locale": "en"},
        "message": "Find hospitals", "requestedAt": "2026-10-21T10:00:00+09:00",
        "conversation": {"mode": "MAIN"}, **kwargs,
    })


def resume(**kwargs):
    return AiTaskResume.model_validate({
        "taskId": "t", "conversationId": "thread",
        "user": {"id": 1, "role": "CUSTOMER", "locale": "en"},
        "approved": True, "editedArgs": {"note": "edited"}, **kwargs,
    })


def worker_for(nodes):
    graph = StateGraph(AgentState)
    previous = START
    for name, node in nodes:
        graph.add_node(name, node)
        graph.add_edge(previous, name)
        previous = name
    graph.add_edge(previous, END)
    store = InMemoryStore()
    publisher = AsyncMock()
    worker = HospitalWorker(graph.compile(checkpointer=MemorySaver(), store=store), store, publisher)
    return worker, publisher


def events(publisher):
    return [call.args[0] for call in publisher.await_args_list]


async def test_actual_messages_stream_tokens_are_incremental_and_private_drafts_hidden():
    raw = FakeListChatModel(responses=["PRIVATE DRAFT"])
    final = FakeListChatModel(responses=["hello"])

    async def plan(state):
        await raw.ainvoke(state["messages"])
        return {"draft": "private"}

    async def respond(state):
        return {"messages": [await final.ainvoke(state["messages"])]}

    worker, publisher = worker_for([("planner", plan), ("respond", respond)])
    await worker.handle(request())
    output = events(publisher)
    assert [e.data["text"] for e in output if e.event == "TOKEN"] == list("hello")
    assert [e.seq for e in output] == list(range(1, len(output) + 1))
    assert output[-1].data["answer"] == "hello"
    assert "PRIVATE" not in str([e.data for e in output])


async def test_tagged_model_inside_nested_coordinator_graph_streams_tokens():
    """run_coordinator invokes a request-local graph inside the planner node; its
    user-facing model is tagged so its tokens stream before respond re-emits them."""
    from coordinator.nodes.planner_agent import USER_ANSWER_TAG
    tagged = FakeListChatModel(responses=["hello"], tags=[USER_ANSWER_TAG])

    inner = StateGraph(AgentState)

    async def main(state):
        return {"messages": [await tagged.ainvoke(state["messages"])]}

    inner.add_node("main", main)
    inner.add_edge(START, "main")
    inner.add_edge("main", END)
    coordinator = inner.compile(checkpointer=False)

    async def plan(state):
        output = await asyncio.wait_for(coordinator.ainvoke({"messages": state["messages"]}), 10)
        return {"draft": output["messages"][-1].content}

    worker, publisher = worker_for([
        ("planner", plan), ("respond", lambda s: {"messages": [AIMessage(content=s["draft"])]}),
    ])
    await worker.handle(request())
    output = events(publisher)
    assert [e.data["text"] for e in output if e.event == "TOKEN"] == list("hello")
    assert output[-1].data["answer"] == "hello"


async def test_main_action_and_all_contract_state_events():
    def plan(state):
        assert state["action"] == {"type": "SET_SORT", "sortBy": "RATING"}
        assert state["conversation_id"] == "thread" and state["task_id"] == "t"
        return {
            "conditions": {"procedure_code": "JAW_BOTOX", "date_from": "2026-10-22", "date_to": "2026-10-28"},
            "missing": ["budget_max_krw"],
            "candidates": [{"id": 1, "min_price_krw": 100000}],
            "relax_options": [{"option": "DATE_PLUS_MINUS_1", "label": "Dates", "expected_count": 4}],
            "trip_plans": [{"hospital_id": 1, "buffer_days": 2}], "trip_summary": "Available dates",
            "selected_hospital_id": 1,
            "opened_conversation": {
                "conversation_id": "c6d49de7-d0ab-4c99-a0d7-ec0880ac4995", "hospital_id": 1,
                "mode": "HOSPITAL", "parent_conversation_id": "thread",
                "consultation_id": None, "conditions": {},
            },
            "memory_proposal": {"fields": {"preferred_areas": ["GANGNAM"]}, "message": "Save?"},
            "verify_passed": True, "verify_attempts": 0,
            "citations": [{"doc_id": "faq", "title": "Title", "section": "visit", "uri": "doc://faq/sections/visit", "snippet": "Text"}],
        }

    worker, publisher = worker_for([("plan", plan), ("respond", lambda s: {"messages": [AIMessage(content="Answer")]})])
    await worker.handle(request(message=None, action={"type": "SET_SORT", "sortBy": "RATING"}))
    output = {e.event: e.data for e in events(publisher)}
    assert output["CONDITIONS"]["missing"] == ["budgetMaxKrw"]
    assert output["RESULT_CARDS"]["cards"][0]["minPriceKrw"] == 100000
    assert output["TRIP_PLAN"]["arrivalDate"] == "2026-10-22"
    assert output["TRIP_PLAN"]["plans"][0]["bufferDays"] == 2
    assert output["CONVERSATION_OPENED"] == {
        "conversationId": "c6d49de7-d0ab-4c99-a0d7-ec0880ac4995", "hospitalId": 1, "summary": None,
    }
    assert output["MEMORY_PROPOSAL"]["fields"]["preferredAreas"] == ["GANGNAM"]
    assert output["VERIFY"] == {"passed": True, "attempts": 0}
    assert output["DONE"]["sources"][0]["docId"] == "faq"


async def test_restart_approval_edit_and_duplicate_resume_only_execute_once():
    decisions = []

    def action(state):
        decision = interrupt({"action": "REQUEST_CONSULTATION", "editable": ["note"], "display": {}, "args": {}})
        decisions.append(decision)
        return {"mode": "HUMAN", "consultation_id": 701, "messages": [AIMessage(content="Connected") ]}

    worker, publisher = worker_for([("action", action)])
    await worker.handle(request())
    worker = HospitalWorker(worker.graph, worker.store, publisher)
    await worker.handle(resume())
    await worker.handle(resume())
    assert decisions == [{"approved": True, "editedArgs": {"note": "edited"}, "reason": None}]
    assert [e.data for e in events(publisher) if e.event == "MODE_CHANGED"] == [{"mode": "HUMAN", "consultationId": 701}]
    assert events(publisher)[-1].seq == events(publisher)[-2].seq


async def test_invalid_approval_edit_cannot_execute():
    execute = AsyncMock()

    async def action(state):
        interrupt({"action": "CREATE_RESERVATION", "editable": ["note"], "display": {}, "args": {}})
        await execute()
        return {"messages": [AIMessage(content="unexpected")]}

    worker, publisher = worker_for([("action", action)])
    await worker.handle(request())
    await worker.handle(resume(editedArgs={"slot_id": 9}))
    execute.assert_not_awaited()
    assert events(publisher)[-1].event == "FAILED"


async def test_terminal_publish_failure_replays_saved_seq_without_execution():
    node = AsyncMock(return_value={"messages": [AIMessage(content="done")]})
    worker, publisher = worker_for([("answer", node)])

    async def publish(event, trace):
        if event.event == "DONE":
            raise ConnectionError()

    publisher.side_effect = publish
    with pytest.raises(EventDeliveryError):
        await worker.handle(request())
    saved = await worker.store.aget(TASK_NAMESPACE, "t")
    assert saved.value["status"] == "DONE"
    publisher.side_effect = None
    worker = HospitalWorker(worker.graph, worker.store, publisher)
    await worker.handle(request())
    assert node.await_count == 1
    assert events(publisher)[-1].seq == saved.value["seq"]


async def test_interrupted_delivery_fails_without_reexecuting_partial_graph():
    node = AsyncMock(return_value={"messages": [AIMessage(content="unexpected")]})
    worker, publisher = worker_for([("answer", node)])
    await worker.store.aput(TASK_NAMESPACE, "t", {"seq": 9, "status": "TOKEN", "userId": 1, "conversationId": "thread"})
    await worker.handle(request())
    node.assert_not_awaited()
    assert events(publisher)[-1].seq == 10
    assert events(publisher)[-1].event == "FAILED"


async def test_pending_thread_is_not_overwritten_by_new_task():
    def action(state):
        interrupt({"action": "CREATE_RESERVATION", "editable": [], "display": {}, "args": {}})
    worker, publisher = worker_for([("action", action)])
    await worker.handle(request())
    await worker.handle(request(task="another"))
    assert events(publisher)[-1].event == "FAILED"
    snapshot = await worker.graph.aget_state({"configurable": {"thread_id": "thread"}})
    assert snapshot.values["task_id"] == "t"
    assert snapshot.next


async def test_closed_consultation_returns_to_hospital_and_survives_worker_restart():
    async def answer(state):
        assert state["mode"] == "HOSPITAL"
        assert state["selected_hospital_id"] == 41
        assert state["consultation_id"] == 701
        return {"messages": [AIMessage(content="Clinic information")]}

    node = AsyncMock(side_effect=answer)
    worker, publisher = worker_for([("answer", node)])
    config = {"configurable": {"thread_id": "thread"}}
    await worker.graph.aupdate_state(config, {
        "mode": "HUMAN", "user": {"user_id": 1}, "selected_hospital_id": 41,
        "consultation_id": 701, "messages": [AIMessage(content="Counselor connected", id="history")],
    }, as_node="answer")

    msg = request(conversation={"mode": "HOSPITAL", "hospitalId": 41}, requestedAt=datetime.now(timezone.utc))
    await worker.handle(msg)
    worker = HospitalWorker(worker.graph, worker.store, publisher)
    await worker.handle(msg)
    await worker.handle(request(task="followup", conversation={"mode": "HOSPITAL", "hospitalId": 41}))

    assert node.await_count == 2
    assert [e.event for e in events(publisher)] == ["STATUS", "TOKEN", "DONE", "DONE", "STATUS", "TOKEN", "DONE"]
    snapshot = await worker.graph.aget_state(config)
    assert snapshot.values["mode"] == "HOSPITAL"
    assert snapshot.values["messages"][0].id == "history"


@pytest.mark.parametrize("saved_mode,requested_mode,owner,hospital", [
    ("MAIN", "HOSPITAL", 1, 41),
    ("HOSPITAL", "MAIN", 1, 41),
    ("HUMAN", "MAIN", 1, 41),
    ("HUMAN", "HUMAN", 1, 41),
    ("HUMAN", "HOSPITAL", 2, 41),
    ("HUMAN", "HOSPITAL", None, 41),
    ("HUMAN", "HOSPITAL", 1, 42),
    ("HUMAN", "HOSPITAL", 1, None),
])
async def test_mode_return_rejects_other_transitions_and_unmatched_identity(saved_mode, requested_mode, owner, hospital):
    node = AsyncMock()
    worker, publisher = worker_for([("answer", node)])
    config = {"configurable": {"thread_id": "thread"}}
    await worker.graph.aupdate_state(config, {
        "mode": saved_mode, "user": {"user_id": owner}, "selected_hospital_id": hospital,
    }, as_node="answer")

    await worker.handle(request(conversation={"mode": requested_mode, "hospitalId": 41},
                                requestedAt=datetime.now(timezone.utc)))

    node.assert_not_awaited()
    assert [e.event for e in events(publisher)] == ["FAILED"]
    assert (await worker.graph.aget_state(config)).values["mode"] == saved_mode


@pytest.mark.parametrize("age_seconds", [0, 1])
async def test_hospital_task_queued_before_handoff_cannot_resume_ai(age_seconds):
    node = AsyncMock()
    worker, publisher = worker_for([("answer", node)])
    config = {"configurable": {"thread_id": "thread"}}
    await worker.graph.aupdate_state(config, {
        "mode": "HUMAN", "user": {"user_id": 1}, "selected_hospital_id": 41,
    }, as_node="answer")
    snapshot = await worker.graph.aget_state(config)
    requested_at = datetime.fromisoformat(snapshot.created_at) - timedelta(seconds=age_seconds)

    await worker.handle(request(conversation={"mode": "HOSPITAL", "hospitalId": 41}, requestedAt=requested_at))

    node.assert_not_awaited()
    assert [e.event for e in events(publisher)] == ["FAILED"]
    assert await worker.graph.aget_state(config) == snapshot


@pytest.mark.parametrize("checkpoint_time", [None, "invalid", "2026-10-21T10:00:00"])
async def test_return_fails_closed_when_checkpoint_timestamp_is_unusable(checkpoint_time):
    node = AsyncMock()
    worker, publisher = worker_for([("answer", node)])
    config = {"configurable": {"thread_id": "thread"}}
    await worker.graph.aupdate_state(config, {
        "mode": "HUMAN", "user": {"user_id": 1}, "selected_hospital_id": 41,
    }, as_node="answer")
    snapshot = await worker.graph.aget_state(config)
    worker.graph.aget_state = AsyncMock(return_value=snapshot._replace(created_at=checkpoint_time))

    await worker.handle(request(conversation={"mode": "HOSPITAL", "hospitalId": 41},
                                requestedAt=datetime.now(timezone.utc)))

    node.assert_not_awaited()
    assert [e.event for e in events(publisher)] == ["FAILED"]


async def test_tool_start_end_payloads():
    def plan(state):
        return {"messages": [AIMessage(content="", tool_calls=[{"id": "call", "name": "business_search_hospitals", "args": {}}])]}
    def tool(state):
        return {"messages": [ToolMessage(content="[]", tool_call_id="call", status="success")]}
    worker, publisher = worker_for([("plan", plan), ("tools", tool), ("respond", lambda s: {"messages": [AIMessage(content="No results")]})])
    await worker.handle(request())
    output = {e.event: e.data for e in events(publisher)}
    assert output["TOOL_START"] == {"tool": "business_search_hospitals", "label": "Checking information…"}
    assert output["TOOL_END"] == {"tool": "business_search_hospitals", "ok": True}


async def test_same_tool_repeated_calls_are_not_deduplicated():
    def plan(state):
        return {"messages": [AIMessage(content="", tool_calls=[
            {"id": str(i), "name": "business_search_hospitals", "args": {"limit": i}} for i in (1, 2)
        ])]}
    def tool(state):
        return {"messages": [ToolMessage(content="[]", tool_call_id=str(i)) for i in (1, 2)]}
    worker, publisher = worker_for([("plan", plan), ("tools", tool), ("respond", lambda s: {"messages": [AIMessage(content="No results")]})])
    await worker.handle(request())
    assert len([e for e in events(publisher) if e.event == "TOOL_START"]) == 2
    assert len([e for e in events(publisher) if e.event == "TOOL_END"]) == 2


async def test_resume_interrupted_after_mutation_is_not_executed_twice():
    executed = []

    def mutate(state):
        interrupt({"action": "CREATE_RESERVATION", "editable": ["note"], "display": {}, "args": {}})
        executed.append("mutation")
        return {"messages": [AIMessage(content="Saved") ]}

    worker, publisher = worker_for([("mutation", mutate)])
    await worker.handle(request())

    async def fail_on_token(event, trace):
        if event.event == "TOKEN":
            raise ConnectionError()

    publisher.side_effect = fail_on_token
    with pytest.raises(EventDeliveryError):
        await worker.handle(resume())
    publisher.side_effect = None
    worker = HospitalWorker(worker.graph, worker.store, publisher)
    await worker.handle(resume())
    assert executed == ["mutation"]
    assert events(publisher)[-1].event == "FAILED"


async def test_scaffold_cannot_report_success_after_approval(monkeypatch):
    from app.graph import builder
    monkeypatch.setattr(builder.action_module, "EXECUTE_ACTION_READY", False, raising=False)
    execute = AsyncMock()
    monkeypatch.setattr(builder, "execute_action", execute)
    with pytest.raises(NotImplementedError):
        await builder.execute_approved_action({"pending_action": {"approved": True}})
    execute.assert_not_awaited()


@pytest.mark.parametrize('mode,pending', [('HOSPITAL', False), ('HOSPITAL', True), ('HUMAN', False)])
async def test_handoff_merge_refreshes_context_and_logs_saved_state(mode, pending):
    from types import SimpleNamespace
    from unittest.mock import Mock
    child = '00000000-0000-0000-0000-000000000073'
    old = {'conversation_id': child, 'user': {'user_id': 1}, 'mode': mode,
           'selected_hospital_id': 7, 'summary': 'old', 'conditions': {'areas': ['GANGNAM']},
           'messages': [AIMessage('Keep hospital history')]}
    new = {**old, 'summary': 'new', 'conditions': {'areas': [], 'date_from': '2026-10-24'},
           'parent_conversation_id': 'thread'}
    graph = AsyncMock()
    graph.aget_state.side_effect = [SimpleNamespace(values=old, next=('approval',) if pending else (),
        config={'configurable': {'checkpoint_id': 'saved'}}), SimpleNamespace(values=new)]
    worker = HospitalWorker(graph, InMemoryStore(), AsyncMock())
    worker._log_handoff = Mock()
    await worker._initialize_child(request(), {'conversation_id': child, 'hospital_id': 7,
        'mode': mode, 'conditions': new['conditions'], 'parent_conversation_id': 'thread'},
        {'selected_hospital_id': 7, 'summary': 'new'})
    if mode == 'HOSPITAL' and not pending:
        graph.aupdate_state.assert_awaited_once_with({'configurable': {'thread_id': child}},
            {'summary': 'new', 'conditions': new['conditions'], 'parent_conversation_id': 'thread'},
            as_node='respond')
        assert worker._log_handoff.call_args.args[2:] == (new, 'context_refreshed')
    else:
        graph.aupdate_state.assert_not_awaited()
        assert worker._log_handoff.call_args.args[2:] == (old, 'preserved')
