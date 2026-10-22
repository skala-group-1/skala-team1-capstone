"""Aftercare nodes, routing and queue acceptance without external services."""

import importlib
import json
from datetime import date
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore

from aftercare.nodes.red_flag import has_warning_sign, safety_reply
from app.graph.routing import route_after_guard
from app.graph.state import AgentState
from app.workers.consumer import HospitalWorker
from app.workers.messages import AiTaskRequested

agent = importlib.import_module("aftercare.nodes.aftercare_agent")
context = importlib.import_module("aftercare.nodes.load_aftercare_context")

RESERVATION = {"id": 16, "status": "CONFIRMED", "hospital": {"id": 3, "name": "H3"},
               "procedure_code": "JAW_BOTOX",
               "slot": {"id": 683, "start_at": "2026-10-20T10:00:00+09:00", "doctor_name": "Dr. Kim"}}


def tool(name, result):
    async def run(**kwargs):
        return json.dumps(result)
    return StructuredTool.from_function(coroutine=run, name=name, description="test",
                                        args_schema={"type": "object", "properties": {}})


def base_state(**extra):
    return {"mode": "AFTERCARE", "selected_hospital_id": 3, "conversation_id": "c1",
            "user": {"user_id": 1, "role": "CUSTOMER", "locale": "ko"},
            "hospital_context": {"hospital_id": 3, "detail": {"id": 3, "name": "강남 H3 의원", "phone": "02-123-4567"}},
            "aftercare_context": {"reservation_id": 16, "procedure_code": "JAW_BOTOX",
                                  "start_at": RESERVATION["slot"]["start_at"], "days_since_procedure": 2},
            **extra}


# ---------------------------------------------------------------- warning signs

@pytest.mark.parametrize("text", [
    "피가 계속 나요", "열이 나고 오한이 있어요", "숨쉬기 힘들어요", "입술 피부가 하얗게 변했어요",
    "숨쉬기가 힘들고 얼굴이 갑자기 부었어요", "목이 부었어요", "한쪽만 갑자기 많이 부었어요",
    "I have a fever since last night", "The bleeding won't stop", "my vision is blurry, blurred vision",
    "出血不止怎么办", "发烧了", "熱があります", "息が苦しい",
])
def test_warning_signs_are_detected(text):
    assert has_warning_sign(text)


@pytest.mark.parametrize("text", [
    "붓기는 언제 빠지나요?", "얼굴이 좀 부었는데 정상인가요?", "When can I wear makeup?", "열은 없는데 조금 부었어요", "No fever, just mild swelling",
    "什么时候可以喝酒？", "いつからお酒を飲めますか", "",
])
def test_ordinary_questions_are_not_flagged(text):
    assert not has_warning_sign(text)


def test_safety_reply_includes_hospital_phone_and_119():
    text = safety_reply("ko", "강남 H3 의원", "02-123-4567")
    assert "강남 H3 의원 (02-123-4567)" in text and "119" in text and "상담사" in text
    assert "your clinic" in safety_reply("fr", None, None)


# ---------------------------------------------------------------- context

def test_days_since_procedure():
    assert context.days_since("2026-10-20T10:00:00+09:00", date(2026, 10, 22)) == 2
    assert context.days_since("2026-10-22T18:00:00+09:00", date(2026, 10, 22)) == 0
    assert context.days_since("2026-10-25T10:00:00+09:00", date(2026, 10, 22)) is None


async def test_context_comes_from_own_confirmed_reservation(monkeypatch):
    monkeypatch.setattr(context, "get_tools", AsyncMock(side_effect=lambda names: [
        tool("business_get_my_reservations", {"reservations": [RESERVATION]}),
        tool("business_get_hospital_detail", {"id": 3, "name": "H3", "phone": "02"}),
    ]))
    state = {"selected_hospital_id": 3, "action": {"type": "AFTERCARE_INTRO", "reservationId": 16}}
    update = await context.load_aftercare_context(state)
    assert update["aftercare_context"]["procedure_code"] == "JAW_BOTOX"
    assert update["conditions"]["procedure_code"] == "JAW_BOTOX"
    assert update["hospital_context"]["detail"]["phone"] == "02"
    # The reservation stays in state for later turns without an action.
    later = await context.load_aftercare_context({**state, **update, "action": None})
    assert later["aftercare_context"]["reservation_id"] == 16


@pytest.mark.parametrize("reservation", [
    {**RESERVATION, "status": "CANCELLED"},
    {**RESERVATION, "hospital": {"id": 9}},
    {**RESERVATION, "id": 99},
])
async def test_context_rejects_unusable_reservation(monkeypatch, reservation):
    monkeypatch.setattr(context, "get_tools", AsyncMock(return_value=[
        tool("business_get_my_reservations", {"reservations": [reservation]})]))
    with pytest.raises(ValueError):
        await context.load_aftercare_context(
            {"selected_hospital_id": 3, "action": {"type": "AFTERCARE_INTRO", "reservationId": 16}})


def test_status_line_and_sections_follow_the_day():
    assert agent.status_line(0, "ko") == "오늘은 시술 당일이에요."
    assert agent.status_line(5, "ja") == "今日は施術後5日目です。"
    assert agent.status_line(None, "fr").startswith("Your procedure hasn't happened yet")
    assert agent.intro_sections(None)[:5] == agent.PERIODS
    assert agent.intro_sections(0)[:2] == ("Procedure day", "Days 1–3")
    assert agent.intro_sections(40)[:1] == ("After 1 month",)
    assert all(len(h) == 8 for h in agent.HEADINGS.values())


def test_plain_codes_removes_internal_labels():
    from concierge.nodes.hospital_reply import internal_labels
    text = agent.plain_codes("After SHURINK see AFTERCARE_SHURINK. JAW_BOTOX stays.", "SHURINK")
    assert "SHURINK" not in text and "Shurink" in text
    assert agent.plain_codes("JAW_BOTOX day", "JAW_BOTOX") == "Jaw Botox day"
    assert not internal_labels(agent.plain_codes("SHURINK", "SHURINK"))


async def test_intro_retries_once_when_reply_guard_rejects(monkeypatch):
    chunk = {"chunk_id": "a", "doc_id": "AFTERCARE_JAW_BOTOX", "title": "t", "section": "Days 1–3",
             "text": "Avoid pressing.", "score": 1, "uri": "doc://AFTERCARE_JAW_BOTOX#days-1-3"}
    monkeypatch.setattr(agent, "get_tools", AsyncMock(return_value=[tool("rag_search_procedure_docs", {"chunks": [chunk]})]))
    replies = iter(["", "", "턱 보톡스 안내"])  # fallback probe, rejected draft, accepted draft
    monkeypatch.setattr(agent, "patient_reply", AsyncMock(side_effect=lambda text, *a: "FALLBACK" if not next(replies) else "턱 보톡스 안내"))
    model = fake_model(monkeypatch, [AIMessage(content="x"), AIMessage(content="y")])
    update = await agent.aftercare_agent(base_state(messages=[], action={"type": "AFTERCARE_INTRO", "reservationId": 16}))
    assert update["draft"].endswith("턱 보톡스 안내")
    assert model.ainvoke.await_count == 2


@pytest.mark.parametrize("days, period", [
    (None, "Before procedure"), (0, "Procedure day"), (1, "Days 1–3"), (3, "Days 1–3"),
    (4, "Days 4–7"), (8, "Weeks 2–4"), (30, "Weeks 2–4"), (31, "After 1 month"),
])
def test_current_period_matches_document_sections(days, period):
    assert agent.current_period(days) == period
    assert period == "Before procedure" or period in agent.SECTIONS


# ---------------------------------------------------------------- agent

def fake_model(monkeypatch, responses):
    class Model:
        bound = None

        def bind_tools(self, tools, **kwargs):
            self.bound = [t["name"] if isinstance(t, dict) else t.name for t in tools]
            return self
    model = Model()
    model.ainvoke = AsyncMock(side_effect=responses)
    monkeypatch.setattr(agent, "_model", lambda: model)
    return model


async def test_intro_summarizes_only_this_procedure_document(monkeypatch):
    chunks = [
        {"chunk_id": "a", "doc_id": "AFTERCARE_JAW_BOTOX", "title": "Jaw Botox — Aftercare Guide",
         "section": "Days 1–3", "text": "Avoid pressing the jaw.", "score": 1, "uri": "doc://AFTERCARE_JAW_BOTOX#days-1-3"},
        {"chunk_id": "b", "doc_id": "COMMON_AFTERCARE_GENERAL", "title": "General", "section": "Sun protection",
         "text": "Use sunscreen.", "score": 1, "uri": "doc://COMMON_AFTERCARE_GENERAL#sun"},
        {"chunk_id": "c", "doc_id": "AFTERCARE_JAW_BOTOX", "title": "Jaw Botox — Aftercare Guide",
         "section": "Procedure day", "text": "Stay upright.", "score": 1, "uri": "doc://AFTERCARE_JAW_BOTOX#procedure-day"},
    ]
    rag = AsyncMock(return_value=[tool("rag_search_procedure_docs", {"chunks": chunks})])
    monkeypatch.setattr(agent, "get_tools", rag)
    model = fake_model(monkeypatch, [AIMessage(content="턱 보톡스 사후관리 안내입니다. 오늘은 시술 후 2일째예요.")])
    update = await agent.aftercare_agent(base_state(messages=[], action={"type": "AFTERCARE_INTRO", "reservationId": 16}))
    # The day line is fixed text; the model writes only the body.
    assert update["draft"].startswith("오늘은 시술 후 2일째예요.\n\n턱 보톡스")
    sent = json.loads(model.ainvoke.await_args.args[0][1].content.split("\n", 1)[1])
    # Day 2: today's period only (procedure day is skipped), with localized headings.
    assert [d["heading"] for d in sent["documents"]] == ["시술 후 1~3일"]
    assert sent["days_since_procedure"] == 2 and sent["current_period"] == "Days 1–3"
    assert {c["doc_id"] for c in update["citations"]} == {"AFTERCARE_JAW_BOTOX"}


async def test_intro_without_document_does_not_call_model(monkeypatch):
    monkeypatch.setattr(agent, "get_tools", AsyncMock(return_value=[tool("rag_search_procedure_docs", {"chunks": []})]))
    model = fake_model(monkeypatch, [])
    update = await agent.aftercare_agent(base_state(messages=[], action={"type": "AFTERCARE_INTRO", "reservationId": 16}))
    assert "찾지 못했어요" in update["draft"]
    model.ainvoke.assert_not_awaited()


async def test_warning_sign_gets_fixed_safety_reply_without_model(monkeypatch):
    monkeypatch.setattr(agent, "get_tools", AsyncMock())
    model = fake_model(monkeypatch, [])
    update = await agent.aftercare_agent(base_state(messages=[HumanMessage("피가 계속 나요 어떡하죠")]))
    assert "02-123-4567" in update["draft"] and "119" in update["draft"]
    model.ainvoke.assert_not_awaited()


async def test_counselor_request_prepares_approval_card(monkeypatch):
    prepared = {"tool": "business_request_consultation", "args": {"hospital_id": 3}}
    prepare = AsyncMock(return_value=prepared)
    monkeypatch.setattr(agent, "prepare_action", prepare)
    update = await agent.aftercare_agent(base_state(messages=[HumanMessage("상담사 연결해 주세요")]))
    assert update["pending_action"] is prepared
    assert update["messages"][0].tool_calls[0]["name"] == "business_request_consultation"


async def test_question_uses_rag_with_this_procedure(monkeypatch):
    monkeypatch.setattr(agent, "get_tools", AsyncMock(return_value=[
        tool(name, {}) for name in (*agent.AFTERCARE_READ_TOOLS, "business_request_consultation",
                                    "business_create_reservation_request")]))
    call = {"name": "rag_search_procedure_docs", "args": {"query": "swelling"}, "id": "r1"}
    model = fake_model(monkeypatch, [AIMessage(content="", tool_calls=[call])])
    update = await agent.aftercare_agent(base_state(messages=[HumanMessage("붓기는 언제 빠지나요?")]))
    sent = update["messages"][-1].tool_calls[0]
    assert sent["args"]["procedure_code"] == "JAW_BOTOX"
    # Reservations cannot be created or cancelled from the aftercare chat.
    assert "business_create_reservation_request" not in model.bound
    assert "business_request_consultation" in model.bound


async def test_rejected_handoff_keeps_localized_reply(monkeypatch):
    model = fake_model(monkeypatch, [])
    done = ToolMessage(content="rejected", tool_call_id="h1", status="success",
                       additional_kwargs={"approval_completed": True})
    update = await agent.aftercare_agent(base_state(messages=[HumanMessage("상담사 연결"), done], draft="거절했습니다"))
    assert update == {"draft": "거절했습니다"}
    model.ainvoke.assert_not_awaited()


def test_aftercare_uses_its_own_model(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("AFTERCARE_MODEL", "gpt-5.4-mini")
    get_settings.cache_clear()
    try:
        assert agent._model().model_name == "gpt-5.4-mini"
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- routing and queue

def test_aftercare_mode_routes_to_subgraph():
    assert route_after_guard({"mode": "AFTERCARE"}) == "aftercare_subgraph"
    assert route_after_guard({"mode": "HUMAN"}) == "end"


def test_main_graph_compiles_with_aftercare():
    from app.graph.builder import compile_graph
    assert "aftercare_subgraph" in compile_graph(MemorySaver()).get_graph().nodes


def request(**overrides):
    body = {"taskId": "t1", "conversationId": "c1", "user": {"id": 1, "role": "CUSTOMER", "locale": "ko"},
            "message": "", "action": {"type": "AFTERCARE_INTRO", "reservationId": 16},
            "requestedAt": "2026-10-22T10:00:00+09:00",
            "conversation": {"mode": "AFTERCARE", "hospitalId": 3, "parentConversationId": None}}
    return AiTaskRequested.model_validate({**body, **overrides})


def worker_for(node):
    g = StateGraph(AgentState)
    g.add_node("answer", node)
    g.add_edge(START, "answer")
    g.add_edge("answer", END)
    store = InMemoryStore()
    publisher = AsyncMock()
    return HospitalWorker(g.compile(checkpointer=MemorySaver(), store=store), store, publisher), publisher


async def test_worker_accepts_intro_without_message():
    seen = {}

    def answer(state):
        seen.update(mode=state["mode"], action=state["action"], hospital=state["selected_hospital_id"])
        return {"messages": [AIMessage(content="안내")]}

    worker, publisher = worker_for(answer)
    await worker.handle(request())
    assert [c.args[0].event for c in publisher.await_args_list][-1] == "DONE"
    assert seen == {"mode": "AFTERCARE", "action": {"type": "AFTERCARE_INTRO", "reservationId": 16}, "hospital": 3}


@pytest.mark.parametrize("changes", [
    {"action": {"type": "SELECT_HOSPITAL", "hospitalId": 3}},
    {"conversation": {"mode": "AFTERCARE"}},
])
async def test_worker_rejects_invalid_aftercare_tasks(changes):
    node = AsyncMock()
    worker, publisher = worker_for(node)
    await worker.handle(request(**changes))
    node.assert_not_awaited()
    assert [c.args[0].event for c in publisher.await_args_list] == ["FAILED"]
