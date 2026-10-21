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
