"""Real LangGraph streams with deterministic model/tools; no live LLM or DB claims."""

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
        "conversationId": "c6d49de7-d0ab-4c99-a0d7-ec0880ac4995", "hospitalId": 1,
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
