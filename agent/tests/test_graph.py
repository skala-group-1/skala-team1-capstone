"""그래프 골격 테스트 — 노드 연결과 분기가 「AI Agent 설계」 그림대로인지. 노드 로직이 채워지면 케이스를 늘린다."""

import importlib
import json
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from app.graph import routing
from app.graph.builder import build_hospital_subgraph, build_main_graph, compile_graph

MAIN_NODES = {"load_memory", "guard_input", "guard_reply", "open_hospital_conversation", "extract_conditions",
              "ask_clarify", "planner_agent", "tools", "memory_propose", "respond", "hospital_subgraph"}
HOSPITAL_NODES = {"load_hospital_context", "hospital_agent", "hospital_tools", "approval", "execute_action"}


def test_mermaid_contains_all_nodes():
    main = build_main_graph().compile().get_graph().draw_mermaid()
    hospital = build_hospital_subgraph().compile().get_graph().draw_mermaid()
    assert all(n in main for n in MAIN_NODES)
    assert "verify" not in build_main_graph().nodes
    assert all(n in hospital for n in HOSPITAL_NODES)


def test_missing_conditions_goes_to_ask_clarify(config, monkeypatch):
    from app.graph import builder

    monkeypatch.setattr(builder, "extract_conditions", lambda state: {"missing": ["procedure_code", "date_from"]})
    monkeypatch.setattr(builder, "ask_clarify", lambda state: {"draft": "Which procedure and dates?"})
    graph = builder.compile_graph(MemorySaver(), InMemoryStore())
    r = graph.invoke({"messages": [HumanMessage("hi")]}, config)
    assert r["missing"] == ["procedure_code", "date_from"]
    assert r["messages"][-1].content == "Which procedure and dates?"


def test_full_conditions_goes_through_planner_to_response(config, monkeypatch):
    from app.graph import builder

    monkeypatch.setattr(builder, "planner_agent", lambda state: {"draft": "Hospital facts checked."})
    graph = builder.compile_graph(MemorySaver(), InMemoryStore())
    r = graph.invoke({"messages": [HumanMessage("jaw botox")],
                      "conditions": {"procedure_code": "JAW_BOTOX", "date_from": "2026-10-20"}}, config)
    assert r["messages"][-1].content == "Hospital facts checked."
    assert r["verify_attempts"] == 0 and r["draft"] is None


def test_guard_flag_goes_to_guard_reply(graph, config):
    r = graph.invoke({"messages": [HumanMessage("recommend best")], "guard_flags": ["RECOMMEND_REQUEST"]}, config)
    assert "guard_reply" in r["messages"][-1].content


def test_human_mode_stops_ai_reply(graph, config):
    r = graph.invoke({"messages": [HumanMessage("hello counselor")], "mode": "HUMAN"}, config)
    assert r["messages"][-1].type == "human"


@pytest.fixture
def booking_graph(monkeypatch):
    """Exercise real async nodes/ToolNode/interrupt with deterministic boundaries.

    The mutation boundary is a spy; these tests do not claim a DB write.
    Live MCP connectivity is checked separately against the running servers.
    """
    hospital = importlib.import_module("concierge.nodes.hospital_agent")
    context = importlib.import_module("concierge.nodes.load_hospital_context")
    client = importlib.import_module("app.mcp_client.client")
    builder = importlib.import_module("app.graph.builder")

    async def detail(hospital_id: int):
        return {"id": hospital_id, "name": "Test hospital"}

    async def doctors(hospital_id: int):
        return {"doctors": [{"id": 11, "name": "Test doctor"}]}

    async def prices(hospital_id: int, procedure_code: str):
        return {"options": []}

    async def slots(hospital_id: int, procedure_code: str, date_from: str, date_to: str):
        return {"slots": [{"id": 12, "start_at": "2026-10-22T10:00:00+09:00",
                           "end_at": "2026-10-22T10:30:00+09:00", "status": "AVAILABLE", "doctor_id": 11}]}

    async def booking(hospital_id: int, slot_id: int, procedure_code: str):
        raise AssertionError("Mutation must only execute through the approval boundary")

    tools = [
        StructuredTool.from_function(coroutine=fn, name=name, description="Test MCP boundary")
        for name, fn in (
            ("business_get_hospital_detail", detail), ("business_list_doctors", doctors),
            ("business_get_price_options", prices),
            ("business_get_available_slots", slots), (hospital.BOOK, booking),
        )
    ]

    async def get_tools(allowed):
        return [t for t in tools if t.name in allowed]

    for module in (hospital, context, client):
        monkeypatch.setattr(module, "get_tools", get_tools)
    # Task 6 adds action preparation; keep this fixture usable before/after integration.
    if importlib.util.find_spec("concierge.nodes.actions"):
        monkeypatch.setattr(importlib.import_module("concierge.nodes.actions"), "get_tools", get_tools)

    def call(name, args, id):
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": id}])

    model = AsyncMock()
    model.bind_tools = lambda *args, **kwargs: model
    model.ainvoke.side_effect = [
        call(hospital.COLLECT, {"procedure_code": "JAW_BOTOX", "date": "2026-10-22", "time": "10:00"}, "prefs"),
        call("business_get_available_slots", {
            "hospital_id": 1, "procedure_code": "JAW_BOTOX",
            "date_from": "2026-10-22", "date_to": "2026-10-22",
        }, "slots"),
        call(hospital.BOOK, {"hospital_id": 1, "slot_id": 12, "procedure_code": "JAW_BOTOX"}, "book"),
        AIMessage(content="요청을 처리했습니다."),
    ]
    monkeypatch.setattr(hospital, "_model", lambda: model)

    async def mutation(state):
        action = state["pending_action"]
        assert action["approved"] is True
        return {"messages": [ToolMessage(content=json.dumps({"status": "PENDING"}),
                                         tool_call_id=action["tool_call_id"])], "pending_action": None}

    execute = AsyncMock(side_effect=mutation)
    monkeypatch.setattr(builder, "execute_action", execute)
    monkeypatch.setattr(builder.action_module, "EXECUTE_ACTION_READY", True, raising=False)
    return compile_graph(MemorySaver(), InMemoryStore()), execute


async def test_hospital_booking_interrupt_and_resume(booking_graph, config):
    graph, execute = booking_graph
    r = await graph.ainvoke({"messages": [HumanMessage("10월 22일 10시에 턱 보톡스 예약할래요")],
                            "mode": "HOSPITAL", "selected_hospital_id": 1}, config)
    pending = r["__interrupt__"][0].value
    assert pending["action"] == "CREATE_RESERVATION"
    assert pending["args"]["slot_id"] == 12
    assert pending["args"]["hospital_id"] == 1
    assert pending["args"]["idempotency_key"]
    execute.assert_not_awaited()
    r = await graph.ainvoke(Command(resume={"approved": True}), config)
    execute.assert_awaited_once()
    assert execute.call_args.args[0]["pending_action"]["args"] == pending["args"]
    assert not r.get("__interrupt__") and r["pending_action"] is None
    assert r["messages"][-1].content == "요청을 처리했습니다."


async def test_hospital_booking_rejected(booking_graph, config):
    graph, execute = booking_graph
    await graph.ainvoke({"messages": [HumanMessage("book please")], "mode": "HOSPITAL",
                        "selected_hospital_id": 1}, config)
    r = await graph.ainvoke(Command(resume={"approved": False, "reason": "no"}), config)
    execute.assert_not_awaited()
    assert any(isinstance(m, ToolMessage) and "User rejected" in m.content for m in r["messages"])
    assert not r.get("__interrupt__")


def test_planner_routes_to_memory_or_tools_without_verify():
    assert routing.route_after_planner({"messages": [AIMessage("Answer")]}) == "memory_propose"
    message = AIMessage(content="", tool_calls=[{
        "name": "business_search_hospitals", "args": {}, "id": "lookup",
    }])
    assert routing.route_after_planner({"messages": [message]}) == "tools"
