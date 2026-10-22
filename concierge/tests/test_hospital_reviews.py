from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, START, END

from app.graph.state import AgentState
from app.mcp_client.tools import HOSPITAL_READ_TOOLS
from concierge.nodes.tools import hospital_tools


async def test_review_execution_forces_selected_hospital(monkeypatch):
    seen = []
    async def reviews(hospital_id: int):
        seen.append(hospital_id)
        return {"items": [], "page": 0, "size": 5, "total": 0}
    name = "business_get_hospital_reviews"
    assert name in HOSPITAL_READ_TOOLS
    tool = StructuredTool.from_function(coroutine=reviews, name=name, description="Read reviews")
    monkeypatch.setattr("app.mcp_client.client.get_tools", AsyncMock(return_value=[tool]))
    builder = StateGraph(AgentState)
    builder.add_node("tools", hospital_tools)
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    result = await builder.compile().ainvoke({"selected_hospital_id": 7, "messages": [AIMessage(
        content="", tool_calls=[{"id": "review", "name": name, "args": {"hospital_id": 999}}])],
    })
    assert seen == [7]
    assert result["messages"][0].tool_calls[0]["args"]["hospital_id"] == 7


async def test_procedure_review_lookup_forces_ten_latest(monkeypatch):
    seen = []
    async def reviews(hospital_id: int, procedure_code: str | None = None, size: int = 5):
        seen.append((hospital_id, procedure_code, size))
        return {"items": [], "page": 0, "size": size, "total": 0}
    name = "business_get_hospital_reviews"
    tool = StructuredTool.from_function(coroutine=reviews, name=name, description="Read reviews")
    monkeypatch.setattr("app.mcp_client.client.get_tools", AsyncMock(return_value=[tool]))
    builder = StateGraph(AgentState)
    builder.add_node("tools", hospital_tools)
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    graph = builder.compile()
    for call_id, args in (("a", {"procedure_code": "LIP_FILLER", "size": 5}), ("b", {"size": 5})):
        await graph.ainvoke({"selected_hospital_id": 7, "messages": [AIMessage(
            content="", tool_calls=[{"id": call_id, "name": name, "args": args}])]})
    assert seen == [(7, "LIP_FILLER", 10), (7, None, 5)]
