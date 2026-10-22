"""Aftercare subgraph. Reuses the concierge tool, approval and execution nodes.

load_aftercare_context → aftercare_agent ─┬─ aftercare_tools → aftercare_agent
                                          ├─ approval → execute_action → (HUMAN: end | aftercare_agent)
                                          └─ end
"""

from langgraph.graph import END, START, StateGraph

from app.graph import routing
from app.graph.state import AgentState
from aftercare.nodes.aftercare_agent import aftercare_agent
from aftercare.nodes.load_aftercare_context import load_aftercare_context
from concierge.nodes.approval import approval
from concierge.nodes.execute_action import execute_action
from concierge.nodes.tools import hospital_tools


def build_aftercare_subgraph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("load_aftercare_context", load_aftercare_context)
    g.add_node("aftercare_agent", aftercare_agent)
    g.add_node("aftercare_tools", hospital_tools)
    g.add_node("approval", approval)
    g.add_node("execute_action", execute_action)

    g.add_edge(START, "load_aftercare_context")
    g.add_edge("load_aftercare_context", "aftercare_agent")
    g.add_conditional_edges("aftercare_agent", routing.route_after_hospital_agent,
                            {"hospital_tools": "aftercare_tools", "approval": "approval", "end": END})
    g.add_edge("aftercare_tools", "aftercare_agent")
    g.add_conditional_edges("approval", routing.route_after_approval,
                            {"execute_action": "execute_action", "hospital_agent": "aftercare_agent"})
    g.add_conditional_edges("execute_action", routing.route_after_execute,
                            {"hospital_agent": "aftercare_agent", "end": END})
    return g
