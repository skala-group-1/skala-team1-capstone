import importlib
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.state import AgentState
from concierge.nodes.tools import hospital_tools

hospital = importlib.import_module("concierge.nodes.hospital_agent")


def search_tool(name, seen):
    async def search(query: str, hospital_id: int | None = None):
        seen.append(hospital_id)
        return {"chunks": [{
            "doc_id": "FAQ", "section": "visit", "title": "Visit guide",
            "uri": "doc://FAQ#visit", "text": "Bring your appointment confirmation.",
        }]}
    return StructuredTool.from_function(coroutine=search, name=name, description="Scoped RAG search")


@pytest.mark.parametrize("name", ["rag_search_hospital_docs", "rag_search_procedure_docs"])
@pytest.mark.parametrize("supplied", [None, 999])
async def test_agent_overwrites_model_hospital(monkeypatch, name, supplied):
    tool = search_tool(name, [])
    model = AsyncMock()
    model.bind_tools = lambda *args, **kwargs: model
    model.ainvoke.return_value = AIMessage(content="", tool_calls=[
        {"name": name, "id": "call", "args": {"query": "aftercare", "hospital_id": supplied}},
    ])
    monkeypatch.setattr(hospital, "_model", lambda: model)
    monkeypatch.setattr(hospital, "get_tools", AsyncMock(return_value=[tool]))
    result = await hospital.hospital_agent({
        "selected_hospital_id": 1, "mode": "HOSPITAL",
        "hospital_context": {"hospital_id": 1}, "user": {"locale": "ko"},
        "messages": [HumanMessage("주의사항 알려줘")],
    })
    assert result["messages"][-1].tool_calls[0]["args"]["hospital_id"] == 1


@pytest.mark.parametrize("name", ["rag_search_hospital_docs", "rag_search_procedure_docs"])
async def test_execution_boundary_scopes_calls_and_collects_sources(monkeypatch, name):
    seen = []
    monkeypatch.setattr("app.mcp_client.client.get_tools", AsyncMock(return_value=[search_tool(name, seen)]))
    builder = StateGraph(AgentState)
    builder.add_node("tools", hospital_tools)
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    graph = builder.compile(checkpointer=MemorySaver())
    result = await graph.ainvoke({
        "selected_hospital_id": 7,
        "messages": [AIMessage(id="ai-call", content="", tool_calls=[
            {"name": name, "id": "call", "args": {"query": "visit", "hospital_id": 999}},
        ])],
    }, {"configurable": {"thread_id": name}})
    assert seen == [7]
    assert len(result["messages"]) == 2
    assert result["messages"][0].tool_calls[0]["args"]["hospital_id"] == 7
    assert result["citations"][0]["uri"] == "doc://FAQ#visit"
    assert result["citations"][0]["snippet"] == "Bring your appointment confirmation."


async def test_old_unscoped_rag_server_is_not_called(monkeypatch):
    seen = []
    async def old_search(query: str):
        seen.append(query)
        return {}
    tool = StructuredTool.from_function(coroutine=old_search, name="rag_search_procedure_docs", description="Old API")
    monkeypatch.setattr("app.mcp_client.client.get_tools", AsyncMock(return_value=[tool]))
    with pytest.raises(ValueError, match="hospital-scoped"):
        await hospital_tools({"selected_hospital_id": 1, "messages": [AIMessage(
            content="", tool_calls=[{"id": "call", "name": tool.name, "args": {"query": "care"}}],
        )]})
    assert not seen


@pytest.mark.parametrize("question", [
    "How long is the requested appointment time held for approval?",
    "What happens if the clinic makes no decision within 30 minutes?",
    "How can I cancel my reservation? Just explain the process.",
    "What exact deposit amount is required for every booking?",
    "예약 취소 절차를 설명해 주세요.",
    "预约的定金是多少？",
    "予約のキャンセル方法を教えてください。",
])
async def test_policy_answer_reads_current_hospital_evidence_before_finishing(monkeypatch, question):
    seen = []
    tool = search_tool("rag_search_hospital_docs", seen)
    model = AsyncMock()
    model.bind_tools = lambda *args, **kwargs: model
    model.ainvoke.side_effect = [
        AIMessage(content="An ungrounded policy answer."),
        AIMessage(content="Bring your appointment confirmation. [Visit guide](doc://FAQ#visit)"),
    ]
    monkeypatch.setattr(hospital, "_model", lambda: model)
    monkeypatch.setattr(hospital, "get_tools", AsyncMock(return_value=[tool]))
    monkeypatch.setattr("app.mcp_client.client.get_tools", AsyncMock(return_value=[tool]))
    graph = StateGraph(AgentState)
    graph.add_node("agent", hospital.hospital_agent)
    graph.add_node("tools", hospital_tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", lambda s: "tools" if getattr(s["messages"][-1], "tool_calls", None) else END)
    graph.add_edge("tools", "agent")
    result = await graph.compile().ainvoke({
        "selected_hospital_id": 7, "mode": "HOSPITAL",
        "hospital_context": {"hospital_id": 7}, "user": {"locale": "en"},
        "messages": [HumanMessage(question)],
    })
    assert seen == [7]
    assert "ungrounded" not in result["draft"]
    assert result["citations"][0]["uri"] == "doc://FAQ#visit"
    assert model.ainvoke.await_count == 2


async def test_policy_lookup_uses_current_turn_not_an_older_question(monkeypatch):
    tool = search_tool("rag_search_hospital_docs", [])
    model = AsyncMock()
    model.bind_tools = lambda *args, **kwargs: model
    model.ainvoke.return_value = AIMessage(content="The policy is unconfirmed.")
    monkeypatch.setattr(hospital, "_model", lambda: model)
    monkeypatch.setattr(hospital, "get_tools", AsyncMock(return_value=[tool]))
    previous_call = AIMessage(content="", tool_calls=[{
        "name": tool.name, "id": "old", "args": {"query": "booking", "hospital_id": 7}}])
    messages = [HumanMessage("How does booking work?"), previous_call,
                ToolMessage(content='{"chunks": []}', tool_call_id="old"),
                HumanMessage("What deposit is required?")]
    result = await hospital.hospital_agent({
        "selected_hospital_id": 7, "mode": "HOSPITAL",
        "hospital_context": {"hospital_id": 7}, "user": {"locale": "en"}, "messages": messages})
    assert result["messages"][-1].tool_calls[0]["name"] == tool.name
    assert result["messages"][-1].tool_calls[0]["args"]["query"] == "What deposit is required?"


@pytest.mark.parametrize("status", ["success", "error"])
async def test_policy_lookup_attempt_is_not_repeated(monkeypatch, status):
    tool = search_tool("rag_search_hospital_docs", [])
    model = AsyncMock()
    model.bind_tools = lambda *args, **kwargs: model
    model.ainvoke.return_value = AIMessage(content="Please confirm the policy with the clinic.")
    monkeypatch.setattr(hospital, "_model", lambda: model)
    monkeypatch.setattr(hospital, "get_tools", AsyncMock(return_value=[tool]))
    messages = [HumanMessage("What deposit is required?"), AIMessage(content="", tool_calls=[{
        "name": tool.name, "id": "current", "args": {"query": "deposit", "hospital_id": 7}}]),
        ToolMessage(content='{"chunks": []}', tool_call_id="current", status=status)]
    result = await hospital.hospital_agent({
        "selected_hospital_id": 7, "mode": "HOSPITAL",
        "hospital_context": {"hospital_id": 7}, "user": {"locale": "en"}, "messages": messages})
    assert result["draft"] == "Please confirm the policy with the clinic."
    assert not result["messages"]
