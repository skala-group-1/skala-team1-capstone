"""Approval invariants with mock MCP and an actual LangGraph interrupt/resume."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import ToolException
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.graph.state import AgentState
from concierge.nodes import actions
from concierge.nodes.approval import approval
from concierge.nodes.execute_action import execute_action

execution = importlib.import_module("concierge.nodes.execute_action")


class State(AgentState, total=False):
    conversation_id: str
    consultation_id: int
    task_id: str


def state():
    return {"selected_hospital_id": 7, "mode": "HOSPITAL", "user": {"user_id": 1, "locale": "ja"},
            "conversation_id": "ac55e772-a184-494d-8ca7-703ad4850360", "task_id": "task-1",
            "hospital_context": {"detail": {"name": "Test clinic"}},
            "hospital_booking": {"procedure_code": "JAW_BOTOX", "date": "2026-10-22", "time": "10:00"},
            "messages": [HumanMessage(content="Please book October 22 at 10:00.")]}


def call(tool=actions.BOOK, args=None):
    return {"id": "call-1", "name": tool, "args": args if args is not None else {
        "hospital_id": 999, "slot_id": 12, "procedure_code": "JAW_BOTOX", "price_option_id": 5}}


def mock_reads(monkeypatch):
    async def lookup(name, args):
        return {
            "business_list_doctors": {"doctors": [{"id": 11, "name": "Dr Test"}]},
            "business_get_price_options": {"options": [{"id": 5, "price_krw": 150000, "vat_included": False}]},
            "business_get_available_slots": {"slots": [{"id": 12, "doctor_id": 11,
                "start_at": "2026-10-22T10:00:00+09:00", "status": "AVAILABLE"}]},
            "business_get_my_reservations": {"reservations": [{"id": 30, "hospital": {"id": 7}, "status": "PENDING"}]},
        }[name]
    mock = AsyncMock(side_effect=lookup)
    monkeypatch.setattr(actions, "lookup", mock)
    return mock


async def prepared(monkeypatch, tool=actions.BOOK, args=None):
    mock_reads(monkeypatch)
    s, c = state(), call(tool, args)
    s["pending_action"] = await actions.prepare_action(s, c)
    s["messages"].append(AIMessage(content="", tool_calls=[{**c, "args": s["pending_action"]["args"]}]))
    return s


def graph():
    builder = StateGraph(State)
    builder.add_node("approval", approval)
    async def execute(s: State):
        return await execute_action(s)
    builder.add_node("execute", execute)
    builder.add_edge(START, "approval")
    builder.add_conditional_edges("approval", lambda s: "execute" if s.get("pending_action") else END,
                                  {"execute": "execute", END: END})
    builder.add_edge("execute", END)
    return builder.compile(checkpointer=MemorySaver())


@pytest.mark.parametrize("approved,count", [(True, 1), (False, 0)])
async def test_interrupt_before_any_mutation_and_exactly_once_on_approval(monkeypatch, approved, count):
    s = await prepared(monkeypatch)
    mutation = AsyncMock(return_value={"id": 30, "status": "PENDING", "hospital": {"id": 7}})
    monkeypatch.setattr(execution, "lookup", mutation)
    g, config = graph(), {"configurable": {"thread_id": "approval-test"}}
    result = await g.ainvoke(s, config)
    mutation.assert_not_awaited()
    pending = result["__interrupt__"][0].value
    assert pending["args"]["hospital_id"] == 7
    assert "150,000" in str(pending["display"])
    result = await g.ainvoke(Command(resume={"approved": approved, "editedArgs": {"note": "hello"}}), config)
    assert mutation.await_count == count
    assert result["pending_action"] is None
    await g.ainvoke(Command(resume={"approved": True}), config)
    assert mutation.await_count == count
    if approved:
        assert mutation.call_args.args[1]["note"] == "hello"


@pytest.mark.parametrize("edits", [{"hospital_id": 8}, {"slot_id": 13}, {"idempotency_key": "new"},
                                    {"consent": True}, {"note": {"bad": "type"}}, ["note"]])
async def test_uneditable_or_invalid_edits_never_mutate(monkeypatch, edits):
    s = await prepared(monkeypatch)
    mutation = AsyncMock()
    monkeypatch.setattr(execution, "lookup", mutation)
    g, config = graph(), {"configurable": {"thread_id": "edits-test"}}
    await g.ainvoke(s, config)
    result = await g.ainvoke(Command(resume={"approved": True, "editedArgs": edits}), config)
    mutation.assert_not_awaited()
    assert result["messages"][-1].status == "error"


async def test_replayed_proposal_uses_stable_key(monkeypatch):
    mock_reads(monkeypatch)
    s, c = state(), call()
    a = await actions.prepare_action(s, c)
    b = await actions.prepare_action(s, c)
    assert a["args"]["idempotency_key"] == b["args"]["idempotency_key"]
    c["id"] = "call-2"
    assert (await actions.prepare_action(s, c))["args"]["idempotency_key"] != a["args"]["idempotency_key"]


async def test_mcp_retries_receive_same_idempotency_key(monkeypatch):
    s = await prepared(monkeypatch)
    s["pending_action"]["approved"] = True
    mutation = AsyncMock(return_value={"id": 30, "status": "PENDING"})
    monkeypatch.setattr(execution, "lookup", mutation)
    await execute_action(s)
    await execute_action(s)
    assert mutation.await_args_list[0] == mutation.await_args_list[1]


@pytest.mark.parametrize("error", [ToolException("SLOT_UNAVAILABLE: alternative 13 at 11:00"),
                                  RuntimeError("secret-provider-details")])
async def test_failure_never_claims_success_or_switches_mode(monkeypatch, error):
    s = await prepared(monkeypatch)
    s["pending_action"]["approved"] = True
    mutation = AsyncMock(side_effect=error)
    monkeypatch.setattr(execution, "lookup", mutation)
    result = await execute_action(s)
    assert result["messages"][-1].status == "error"
    assert "mode" not in result
    assert "secret-provider-details" not in result["messages"][-1].content
    if isinstance(error, ToolException):
        assert "alternative 13" in result["messages"][-1].content
    mutation.assert_awaited_once()


@pytest.mark.parametrize("result", [{}, {"id": 3, "status": "ERROR"}, {"error": "denied"}])
async def test_malformed_mutation_response_is_failure(monkeypatch, result):
    s = await prepared(monkeypatch)
    s["pending_action"]["approved"] = True
    monkeypatch.setattr(execution, "lookup", AsyncMock(return_value=result))
    assert (await execute_action(s))["messages"][-1].status == "error"


async def test_cancellation_is_scoped_and_approved(monkeypatch):
    s = await prepared(monkeypatch, actions.CANCEL, {"reservation_id": 30})
    mutation = AsyncMock(return_value={"id": 30, "status": "CANCELLED"})
    monkeypatch.setattr(execution, "lookup", mutation)
    with pytest.raises(ValueError, match="approval"):
        await execute_action(s)
    mutation.assert_not_awaited()
    g, config = graph(), {"configurable": {"thread_id": "cancel"}}
    await g.ainvoke(s, config)
    await g.ainvoke(Command(resume={"approved": True, "editedArgs": {"reason": "changed plans"}}), config)
    mutation.assert_awaited_once_with(actions.CANCEL, {"reservation_id": 30, "reason": "changed plans"})
    with pytest.raises(ValueError, match="own reservation"):
        await actions.prepare_action(state(), call(actions.CANCEL, {"reservation_id": 99}))


CARD = {"procedure": "Botox", "preferred_dates": None, "stay_days": None, "budget": None,
        "questions": [], "customer_locale": "ja"}


async def test_summary_is_reviewed_then_consented_before_handoff(monkeypatch):
    summary = AsyncMock(return_value=CARD)
    monkeypatch.setattr(actions, "summarize", summary)
    s = await prepared(monkeypatch, actions.HANDOFF, {"hospital_id": 999, "consent": True,
                                                        "summary_card": {"procedure": "invented"}})
    assert s["pending_action"]["args"]["summary_card"] == CARD
    assert s["pending_action"]["args"]["consent"] is False
    mutation = AsyncMock(return_value={"id": 701, "status": "WAITING"})
    monkeypatch.setattr(execution, "lookup", mutation)
    g, config = graph(), {"configurable": {"thread_id": "handoff"}}
    interrupted = await g.ainvoke(s, config)
    assert "Botox" in str(interrupted["__interrupt__"][0].value["display"])
    mutation.assert_not_awaited()
    result = await g.ainvoke(Command(resume={"approved": True}), config)
    assert result["mode"] == "HUMAN" and result["consultation_id"] == 701
    assert mutation.call_args.args[1]["consent"] is True
    assert mutation.call_args.args[1]["conversation_id"] == state()["conversation_id"]
    summary.assert_awaited_once()


async def test_no_consultation_without_consent(monkeypatch):
    monkeypatch.setattr(actions, "summarize", AsyncMock(return_value=CARD))
    s = await prepared(monkeypatch, actions.HANDOFF, {})
    s["pending_action"]["approved"] = True
    mutation = AsyncMock()
    monkeypatch.setattr(execution, "lookup", mutation)
    with pytest.raises(ValueError, match="consent"):
        await execute_action(s)
    mutation.assert_not_awaited()


@pytest.mark.parametrize("approved", [True, False])
async def test_korean_review_form_then_explicit_handoff(monkeypatch, approved):
    def unexpected_http(**kwargs):
        pytest.fail("Korean review card must not call the separate summarizer")
    monkeypatch.setattr(actions.httpx, "AsyncClient", unexpected_http)
    s = state()
    s["user"]["locale"] = "ko"
    s["messages"] = [HumanMessage(content="턱 보톡스 상담사 연결 폼을 보여주세요."),
                     AIMessage(content="확인되지 않은 가격 999원")]
    c = call(actions.HANDOFF, {})
    pending = await actions.prepare_action(s, c)
    card = pending["args"]["summary_card"]
    assert card["customer_locale"] == "ko"
    assert card["procedure"] == "사각턱 보톡스"
    assert card["preferred_dates"] == "2026-10-22"
    assert card["budget"] is None
    assert card["questions"] == [s["messages"][0].content]
    s["pending_action"] = pending
    s["messages"].append(AIMessage(content="", tool_calls=[{**c, "args": pending["args"]}]))
    mutation = AsyncMock(return_value={"id": 701, "status": "WAITING"})
    monkeypatch.setattr(execution, "lookup", mutation)
    g, config = graph(), {"configurable": {"thread_id": f"ko-handoff-{approved}"}}
    result = await g.ainvoke(s, config)
    assert result["__interrupt__"][0].value["action"] == "REQUEST_CONSULTATION"
    assert result["__interrupt__"][0].value["args"]["summaryCard"]["customerLocale"] == "ko"
    mutation.assert_not_awaited()
    result = await g.ainvoke(Command(resume={"approved": approved}), config)
    assert mutation.await_count == int(approved)
    assert result["mode"] == ("HUMAN" if approved else "HOSPITAL")
    if approved:
        assert result["consultation_id"] == 701
        assert mutation.call_args.args[1]["consent"] is True


async def test_korean_review_leaves_unknown_choices_empty():
    s = state()
    s["user"]["locale"] = "ko"
    s["hospital_booking"] = {}
    s["conditions"] = {"date_from": "2026-10-22", "date_to": "2026-10-26"}
    card = await actions.summarize(s)
    assert card["procedure"] == "확인 필요"
    assert card["preferred_dates"] is None
    assert card["stay_days"] is None


@pytest.mark.parametrize("message", ["상담 요약 폼과 연결 확인 버튼을 보여주세요.",
                                     "I want to talk to a counselor", "Please connect me to a counselor"])
async def test_explicit_form_request_cannot_be_replaced_with_chat_text(monkeypatch, message):
    hospital = importlib.import_module("concierge.nodes.hospital_agent")
    monkeypatch.setattr(hospital, "get_tools", AsyncMock(return_value=[SimpleNamespace(name=actions.HANDOFF)]))
    monkeypatch.setattr(hospital, "_model", lambda: pytest.fail("Explicit form request needs no model"))
    s = state()
    s["user"]["locale"] = "ko"
    s["hospital_context"]["hospital_id"] = 7
    s["messages"] = [HumanMessage(content=message)]
    result = await hospital.hospital_agent(s)
    assert result["pending_action"]["action"] == "REQUEST_CONSULTATION"
    assert result["pending_action"]["args"]["consent"] is False
    assert isinstance(result["pending_action"]["args"]["summary_card"]["procedure"], str)
    assert result["messages"][0].tool_calls[0]["name"] == actions.HANDOFF
    assert result["draft"] is None


@pytest.mark.parametrize("message", ["I don't want to talk to a counselor", "What does a counselor do?",
                                     "상담 요약 폼을 보여주지 마세요", "상담사 연결 취소해줘"])
def test_counselor_mentions_and_rejections_do_not_open_form(message):
    hospital = importlib.import_module("concierge.nodes.hospital_agent")
    assert not hospital.requests_counselor_form(message)


async def test_english_handoff_without_chosen_procedure_uses_explicit_unknown(monkeypatch):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, json={"summaryCard": {"procedure": None, "customerLocale": "en"}})))
    monkeypatch.setattr(actions.httpx, "AsyncClient", lambda **kw: client)
    monkeypatch.setattr(actions, "get_settings", lambda: SimpleNamespace(summarizer_url="http://summary"))
    s = state()
    s["user"]["locale"] = "en"
    card = await actions.summarize(s)
    assert card["procedure"] == "Needs confirmation"
    assert card["customer_locale"] == "en"


async def test_summary_failure_never_proposes_handoff(monkeypatch):
    monkeypatch.setattr(actions, "summarize", AsyncMock(side_effect=RuntimeError("unavailable")))
    with pytest.raises(RuntimeError):
        await actions.prepare_action(state(), call(actions.HANDOFF, {}))


async def test_real_summary_http_contract_uses_patient_facts(monkeypatch):
    monkeypatch.setattr(actions, "get_settings", lambda: SimpleNamespace(summarizer_url="http://summary"))
    request_json = []
    def handler(request):
        assert request.url.path == "/summarize"
        request_json.append(json.loads(request.content))
        return httpx.Response(200, json={"summaryCard": {"procedure": "Botox", "customerLocale": "ja"}, "text": ""})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(actions.httpx, "AsyncClient", lambda **kw: client)
    s = state()
    s["messages"].append(AIMessage(content="unsupported medical claim"))
    s["conditions"] = {"budget_max_krw": 150000}
    card = await actions.summarize(s)
    assert card["customer_locale"] == "ja"
    assert request_json[0]["conditions"] == {"budgetMaxKrw": 150000}
    assert request_json[0]["purpose"] == "NEEDS_CARD"
    assert len(request_json[0]["messages"]) == 1


@pytest.mark.parametrize("locale", ["en", "ko", "zh", "ja"])
async def test_approval_display_is_localized_without_internal_json(monkeypatch, locale):
    mock_reads(monkeypatch)
    s = state()
    s["user"]["locale"] = locale
    pending = await actions.prepare_action(s, call())
    display = pending["display"]
    from concierge.nodes.action_display import label
    from concierge.nodes.hospital_reply import internal_labels
    assert display["title"] == label("book", locale)
    assert not internal_labels(" ".join(r["value"] for r in display["rows"]))
    assert all(not r["value"].startswith("{") for r in display["rows"])
    assert "150,000 KRW" in str(display)
    assert label("excluded", locale) in str(display)


async def test_changed_hospital_cannot_execute_approved_action(monkeypatch):
    s = await prepared(monkeypatch)
    s["pending_action"]["approved"] = True
    s["selected_hospital_id"] = 8
    mutation = AsyncMock()
    monkeypatch.setattr(execution, "lookup", mutation)
    with pytest.raises(ValueError, match="hospital changed"):
        await execute_action(s)
    mutation.assert_not_awaited()


async def test_consultation_rejection_never_shares_summary(monkeypatch):
    monkeypatch.setattr(actions, "summarize", AsyncMock(return_value=CARD))
    s = await prepared(monkeypatch, actions.HANDOFF, {})
    mutation = AsyncMock()
    monkeypatch.setattr(execution, "lookup", mutation)
    g, config = graph(), {"configurable": {"thread_id": "handoff-rejected"}}
    await g.ainvoke(s, config)
    result = await g.ainvoke(Command(resume={"approved": False}), config)
    mutation.assert_not_awaited()
    assert result["mode"] == "HOSPITAL"


async def test_cancellation_cannot_report_a_different_reservation(monkeypatch):
    s = await prepared(monkeypatch, actions.CANCEL, {"reservation_id": 30})
    s["pending_action"]["approved"] = True
    monkeypatch.setattr(execution, "lookup", AsyncMock(return_value={"id": 31, "status": "CANCELLED"}))
    result = await execute_action(s)
    assert result["messages"][-1].status == "error"


@pytest.mark.parametrize("body,status", [({"summaryCard": {"procedure": "invented", "customerLocale": "en"}}, 200),
                                        ({"summaryCard": {"procedure": 123, "customerLocale": "ja"}}, 200),
                                        ({}, 503)])
async def test_summary_http_failure_or_invalid_card_is_not_approved(monkeypatch, body, status):
    monkeypatch.setattr(actions, "get_settings", lambda: SimpleNamespace(summarizer_url="http://summary"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body)))
    monkeypatch.setattr(actions.httpx, "AsyncClient", lambda **kw: client)
    with pytest.raises((ValueError, httpx.HTTPStatusError)):
        await actions.prepare_action(state(), call(actions.HANDOFF, {}))


@pytest.mark.parametrize("approved", [True, False])
async def test_duplicate_resume_cannot_approve_a_second_mutation_in_same_task(monkeypatch, approved):
    from langchain_core.tools import StructuredTool
    hospital = importlib.import_module("concierge.nodes.hospital_agent")
    s = await prepared(monkeypatch)
    s["hospital_context"]["hospital_id"] = 7
    mutation = AsyncMock(return_value={"id": 30, "status": "PENDING"})
    monkeypatch.setattr(execution, "lookup", mutation)
    async def book(hospital_id: int):
        raise AssertionError("Only execute_action may mutate")
    tool = StructuredTool.from_function(coroutine=book, name=actions.BOOK, description="test")
    loader = AsyncMock(return_value=[tool])
    monkeypatch.setattr(hospital, "get_tools", loader)
    model = AsyncMock()
    bound_names = []
    def bind(tools, **kwargs):
        bound_names.extend(t.name for t in tools if hasattr(t, "name"))
        return model
    model.bind_tools = bind
    model.ainvoke.side_effect = [
        AIMessage(content="", tool_calls=[{**call(), "id": "unrequested-second-mutation"}]),
        AIMessage(content="Please send a new request for another action."),
    ]
    monkeypatch.setattr(hospital, "_model", lambda: model)
    builder = StateGraph(State)
    builder.add_node("approval", approval)
    async def execute(s: State):
        return await execute_action(s)
    builder.add_node("execute", execute)
    builder.add_node("hospital", hospital.hospital_agent)
    builder.add_edge(START, "approval")
    builder.add_conditional_edges("approval", lambda s: "execute" if s.get("pending_action") else "hospital")
    builder.add_edge("execute", "hospital")
    builder.add_edge("hospital", END)
    g = builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "single-approval"}}
    await g.ainvoke(s, config)
    result = await g.ainvoke(Command(resume={"approved": approved}), config)
    assert not result.get("__interrupt__")
    assert actions.BOOK not in bound_names
    loader.assert_not_awaited()
    model.ainvoke.assert_not_awaited()
    assert mutation.await_count == (1 if approved else 0)
    await g.ainvoke(Command(resume={"approved": True}), config)
    assert mutation.await_count == (1 if approved else 0)
    assert not hospital._action_finished([*result["messages"], HumanMessage(content="New action please")])


@pytest.mark.parametrize("locale", ["en", "ko", "zh", "ja"])
@pytest.mark.parametrize("status", ["PENDING", "CONFIRMED", "REJECTED", "EXPIRED", "CANCELLED"])
async def test_verified_reservation_result_finishes_without_model(monkeypatch, locale, status):
    hospital = importlib.import_module("concierge.nodes.hospital_agent")
    s = await prepared(monkeypatch, actions.CANCEL if status == "CANCELLED" else actions.BOOK,
                       {"reservation_id": 30} if status == "CANCELLED" else None)
    s["user"]["locale"] = locale
    s["pending_action"]["approved"] = True
    monkeypatch.setattr(execution, "lookup", AsyncMock(return_value={"id": 30, "status": status}))
    update = await execute_action(s)
    model = AsyncMock(side_effect=AssertionError("A verified result must not be rewritten"))
    monkeypatch.setattr(hospital, "_model", model)
    reply = await hospital.hospital_agent({**s, **update})
    assert reply["draft"] == execution.RESERVATION_REPLY[status][("en", "ko", "zh", "ja").index(locale)]
    model.assert_not_called()


@pytest.mark.parametrize("locale", ["en", "ko", "zh", "ja"])
async def test_declining_action_returns_localized_result_without_model(monkeypatch, locale):
    hospital = importlib.import_module("concierge.nodes.hospital_agent")
    approvals = importlib.import_module("concierge.nodes.approval")
    s = await prepared(monkeypatch)
    s["user"]["locale"] = locale
    monkeypatch.setattr(approvals, "interrupt", lambda _: {"approved": False})
    update = approval(s)
    model = AsyncMock(side_effect=AssertionError("A declined action must not be rewritten"))
    monkeypatch.setattr(hospital, "_model", model)
    result = await hospital.hospital_agent({**s, **update})
    assert result["draft"] == approvals.REJECTION_REPLY[locale]
    assert update["pending_action"] is None
    model.assert_not_called()
