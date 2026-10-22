"""그래프 조립. 노드 연결은 「AI Agent 설계」 9-1(메인 v2)·4장(병원 서브그래프) 그림 그대로.

노드 로직은 역할별 패키지에, 공통 분기 조건은 graph/routing.py 에 둔다.
"""

from langgraph.graph import END, START, StateGraph

from app.graph import routing
from app.graph.state import AgentState
from app.nodes.respond import respond
from aftercare.graph import build_aftercare_subgraph
from concierge.nodes import execute_action as action_module
from concierge.nodes.approval import approval
from concierge.nodes.execute_action import execute_action
from concierge.nodes.hospital_agent import hospital_agent
from concierge.nodes.load_hospital_context import load_hospital_context
from concierge.nodes.tools import hospital_tools
from coordinator.nodes.ask_clarify import ask_clarify
from coordinator.nodes.extract_conditions import extract_conditions
from coordinator.nodes.guard_input import guard_input
from coordinator.nodes.guard_reply import guard_reply
from coordinator.nodes.load_memory import load_memory
from coordinator.nodes.memory_propose import memory_propose
from coordinator.nodes.open_hospital_conversation import open_hospital_conversation
from coordinator.nodes.planner_agent import planner_agent
from coordinator.nodes.tools import planner_tools


async def execute_approved_action(state: AgentState) -> dict:
    # Fail closed while a checkout still has the scaffold mutation node.
    if not getattr(action_module, "EXECUTE_ACTION_READY", False):
        raise NotImplementedError("Approved action execution is not connected")
    return await execute_action(state)


def build_hospital_subgraph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("load_hospital_context", load_hospital_context)
    g.add_node("hospital_agent", hospital_agent)
    g.add_node("hospital_tools", hospital_tools)
    g.add_node("approval", approval)
    g.add_node("execute_action", execute_approved_action)

    g.add_edge(START, "load_hospital_context")
    g.add_edge("load_hospital_context", "hospital_agent")
    g.add_conditional_edges("hospital_agent", routing.route_after_hospital_agent,
                            {"hospital_tools": "hospital_tools", "approval": "approval", "end": END})
    g.add_edge("hospital_tools", "hospital_agent")
    g.add_conditional_edges("approval", routing.route_after_approval,
                            {"execute_action": "execute_action", "hospital_agent": "hospital_agent"})
    g.add_conditional_edges("execute_action", routing.route_after_execute,
                            {"hospital_agent": "hospital_agent", "end": END})
    return g


def build_main_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("load_memory", load_memory)
    g.add_node("guard_input", guard_input)
    g.add_node("guard_reply", guard_reply)
    g.add_node("open_hospital_conversation", open_hospital_conversation)
    g.add_node("extract_conditions", extract_conditions)
    g.add_node("ask_clarify", ask_clarify)
    g.add_node("planner_agent", planner_agent)
    g.add_node("tools", planner_tools)
    g.add_node("memory_propose", memory_propose)
    g.add_node("respond", respond)
    g.add_node("hospital_subgraph", build_hospital_subgraph().compile())
    g.add_node("aftercare_subgraph", build_aftercare_subgraph().compile())

    g.add_edge(START, "load_memory")
    g.add_edge("load_memory", "guard_input")
    g.add_conditional_edges("guard_input", routing.route_after_guard, {
        "guard_reply": "guard_reply",
        "open_hospital_conversation": "open_hospital_conversation",
        "extract_conditions": "extract_conditions",
        "hospital_subgraph": "hospital_subgraph",
        "aftercare_subgraph": "aftercare_subgraph",
        "end": END,
    })
    g.add_conditional_edges("extract_conditions", routing.route_after_extract,
                            {"ask_clarify": "ask_clarify", "planner_agent": "planner_agent"})
    g.add_conditional_edges("planner_agent", routing.route_after_planner,
                            {"tools": "tools", "memory_propose": "memory_propose"})
    g.add_edge("tools", "planner_agent")
    g.add_edge("memory_propose", "respond")
    for node in ("guard_reply", "ask_clarify", "open_hospital_conversation", "hospital_subgraph", "aftercare_subgraph"):
        g.add_edge(node, "respond")
    g.add_edge("respond", END)
    return g


def compile_graph(checkpointer=None, store=None):
    """checkpointer·store 는 harness.memory.open_checkpointer_and_store() 로 연다."""
    return build_main_graph().compile(checkpointer=checkpointer, store=store)
