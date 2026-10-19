"""그래프 골격 테스트 — 노드 연결과 분기가 03 문서 그림대로인지. 노드 로직이 채워지면 케이스를 늘린다."""

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graph import routing
from app.graph.builder import build_hospital_subgraph, build_main_graph

MAIN_NODES = {"load_memory", "guard_input", "guard_reply", "open_hospital_conversation", "extract_conditions",
              "ask_clarify", "planner_agent", "tools", "verify", "memory_propose", "respond", "hospital_subgraph"}
HOSPITAL_NODES = {"load_hospital_context", "hospital_agent", "hospital_tools", "approval", "execute_action"}


def test_mermaid_contains_all_nodes():
    main = build_main_graph().compile().get_graph().draw_mermaid()
    hospital = build_hospital_subgraph().compile().get_graph().draw_mermaid()
    assert all(n in main for n in MAIN_NODES)
    assert all(n in hospital for n in HOSPITAL_NODES)


def test_missing_conditions_goes_to_ask_clarify(graph, config):
    r = graph.invoke({"messages": [HumanMessage("hi")]}, config)
    assert r["missing"] == ["procedure_code", "date_from"]
    assert "ask_clarify" in r["messages"][-1].content


def test_full_conditions_goes_through_planner_and_verify(graph, config):
    r = graph.invoke({"messages": [HumanMessage("jaw botox")],
                      "conditions": {"procedure_code": "JAW_BOTOX", "date_from": "2026-10-20"}}, config)
    assert "planner_agent" in r["messages"][-1].content
    assert r["verify_attempts"] == 0 and r["draft"] is None


def test_guard_flag_goes_to_guard_reply(graph, config):
    r = graph.invoke({"messages": [HumanMessage("recommend best")], "guard_flags": ["RECOMMEND_REQUEST"]}, config)
    assert "guard_reply" in r["messages"][-1].content


def test_human_mode_stops_ai_reply(graph, config):
    r = graph.invoke({"messages": [HumanMessage("hello counselor")], "mode": "HUMAN"}, config)
    assert r["messages"][-1].type == "human"


def test_hospital_booking_interrupt_and_resume(graph, config):
    r = graph.invoke({"messages": [HumanMessage("예약할래요")], "mode": "HOSPITAL", "selected_hospital_id": 1}, config)
    pending = r["__interrupt__"][0].value
    assert pending["action"] == "CREATE_RESERVATION"
    r = graph.invoke(Command(resume={"approved": True}), config)
    assert "execute_action" in r["messages"][-1].content


def test_hospital_booking_rejected(graph, config):
    graph.invoke({"messages": [HumanMessage("book please")], "mode": "HOSPITAL", "selected_hospital_id": 1}, config)
    r = graph.invoke(Command(resume={"approved": False, "reason": "no"}), config)
    assert "User rejected" in r["messages"][-1].content


def test_verify_retries_once():
    assert routing.route_after_verify({"verify_passed": False, "verify_attempts": 1}) == "planner_agent"
    assert routing.route_after_verify({"verify_passed": False, "verify_attempts": 2}) == "memory_propose"
    assert routing.route_after_verify({"verify_passed": True, "verify_attempts": 0}) == "memory_propose"
