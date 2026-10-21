"""Coordinator offline graphs plus opt-in existing mock MCP integration."""
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from coordinator.nodes.coordinator_tools import make_coordinator_tools, load_business_tools
from coordinator.nodes.planner_agent import run_coordinator, chat_with_mock_hospitals


class ScriptedModel:
    def __init__(self, *replies):
        self.replies = iter(replies)
        self.history = []

    def bind_tools(self, tools, **kwargs):
        self.names = {t.name for t in tools}
        return self

    async def ainvoke(self, messages):
        self.history.append(messages)
        return next(self.replies)


def call(name, args, identifier="one"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": identifier}])


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["en", "zh", "ja"])
async def test_intake_preserves_login_language_without_tools(locale):
    loader = AsyncMock()
    model = ScriptedModel(AIMessage(content="Which area would you like to discuss?"))
    result = await run_coordinator({"user": {"locale": locale}, "messages": [HumanMessage("Hello")]},
                                   model, business_loader=loader)
    assert result["draft"]
    assert json.loads(model.history[0][1].content)["locale"] == locale
    assert model.names == {"procedure_consultation", "hospital_lookup"}
    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_tool_a_round_trip_is_unavailable_not_invented_evidence():
    model = ScriptedModel(call("procedure_consultation", {"question": "Explain pico toning"}),
                          AIMessage(content="External search is not connected."))
    await run_coordinator({"messages": [HumanMessage("Explain pico toning")]}, model)
    assert isinstance(model.history[-1][-1], ToolMessage)
    assert json.loads(model.history[-1][-1].content)["status"] == "external_search_unavailable"


@pytest.mark.asyncio
async def test_missing_sort_prevents_lookup():
    loader = AsyncMock()
    tools, _ = make_coordinator_tools(loader)
    response = await tools[1].ainvoke({"operation": "search", "arguments": {
        "procedure_code": "JAW_BOTOX", "date_from": "2026-10-22"}})
    assert response == {"status": "needs_input", "missing": ["sort_by"]}
    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_caps_at_five_and_round_trip_summary_without_connection():
    @tool
    async def business_search_hospitals(procedure_code: str, date_from: str, sort_by: str, limit: int):
        """Existing MCP search boundary."""
        assert limit == 5
        return {"hospitals": [{"id": n, "name": f"Clinic {n}"} for n in range(1, 9)], "total": 8}

    loader = AsyncMock(return_value=[business_search_hospitals])
    state = {"user": {"locale": "en"}, "messages": [HumanMessage(
        "Jaw botox October 22, 2026. Sort by price. Not surgery.")]}
    model = ScriptedModel(call("hospital_lookup", {"operation": "search", "arguments": {
        "procedure_code": "JAW_BOTOX", "date_from": "2026-10-22", "sort_by": "PRICE"}}),
        AIMessage(content="Five matching clinics."))
    first = await run_coordinator(state, model, business_loader=loader)
    assert len(first["candidates"]) == 5
    state.update(first)
    state["messages"] += [AIMessage(content=first["draft"]), HumanMessage("I select Clinic 2.")]
    no_connection = AsyncMock(side_effect=AssertionError("Summary must be offline"))
    model = ScriptedModel(call("hospital_lookup", {"operation": "prepare_handoff", "arguments": {
        "hospital_id": 2}}), AIMessage(content="Unsent draft ready."))
    second = await run_coordinator(state, model, business_loader=no_connection)
    assert second["selected_hospital_id"] == 2
    for source_fact in ("Clinic 2", "JAW_BOTOX", "2026-10-22", "Not surgery"):
        assert source_fact in second["summary"]
    assert "not sent" in second["summary"]
    assert "mode" not in second
    no_connection.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("locale,title", [("zh", "交接摘要草稿"), ("ja", "引き継ぎ用下書き"), ("ko", "인계 요약")])
async def test_localized_summary_and_invalid_selection(locale, title):
    tools, results = make_coordinator_tools(AsyncMock(), initial_state={"user": {"locale": locale},
        "candidates": [{"id": 4, "name": "Clinic 4"}], "messages": [HumanMessage("Budget 200000 KRW")],
        "conditions": {"date_from": "2026-10-22"}})
    good = await tools[1].ainvoke({"operation": "prepare_handoff", "arguments": {"hospital_id": 4}})
    assert title in good["summary"]
    assert "200000 KRW" in good["summary"]
    bad = await tools[1].ainvoke({"operation": "prepare_handoff", "arguments": {"hospital_id": 999}})
    assert bad["status"] == "invalid_selection"
    assert results["summary"] is None and results["selected_hospital_id"] is None


@pytest.mark.asyncio
async def test_repeated_tool_call_is_blocked():
    args = {"question": "Explain"}
    model = ScriptedModel(call("procedure_consultation", args),
                          call("procedure_consultation", args, "two"), AIMessage(content="Stopped"))
    await run_coordinator({"messages": [HumanMessage("Explain")]}, model)
    assert json.loads(model.history[-1][-1].content)["status"] == "stopped"


@pytest.mark.asyncio
async def test_business_only_loader(monkeypatch):
    client = type("Client", (), {"get_tools": AsyncMock(return_value=[])})()
    monkeypatch.setattr("app.mcp_client.client.get_client", lambda: client)
    await load_business_tools()
    client.get_tools.assert_awaited_once_with(server_name="business")


@pytest.mark.asyncio
async def test_provider_exception_never_exposes_message():
    loader = AsyncMock(side_effect=RuntimeError("Bearer SECRET"))
    model = ScriptedModel(call("hospital_lookup", {"operation": "reservations", "arguments": {}}),
                          AIMessage(content="Unavailable"))
    await run_coordinator({"messages": [HumanMessage("Reservations")]}, model, business_loader=loader)
    assert "SECRET" not in model.history[-1][-1].content
    assert json.loads(model.history[-1][-1].content)["status"] == "unavailable"


@pytest.mark.asyncio
async def test_whitespace_key_fails_before_api(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "openai_api_key", "not-a-real-key\n")
    result = await run_coordinator({"user": {"locale": "ja"}, "messages": []})
    assert "API_KEY_WHITESPACE" in result["draft"]
    assert "not-a-real-key" not in result["draft"]


@pytest.mark.asyncio
async def test_cli_preserves_history_and_prints_summary():
    snapshots = []

    async def runner(state, **kwargs):
        snapshots.append(list(state["messages"]))
        assert state["user"]["locale"] == "ja"
        if len(snapshots) == 1:
            return {"draft": "Clinic Three, ID 3", "candidates": [{"id": 3, "name": "Clinic Three"}]}
        assert state["candidates"][0]["id"] == 3
        return {"draft": "Draft ready", "summary": "UNSENT BRIEF", "selected_hospital_id": 3}

    inputs = iter(["Find hospitals", "I select ID 3", "/exit"])
    output = []
    await chat_with_mock_hospitals("ja", read=lambda _: next(inputs), write=output.append, runner=runner)
    assert len(snapshots) == 2 and len(snapshots[1]) == 3
    assert any("UNSENT BRIEF" in line for line in output)


@pytest.mark.asyncio
async def test_mock_mcp_list_and_summary():
    """RUN_MOCK_MCP=1 enables real stdio MCP + repository mock JSON, no LLM."""
    if os.environ.get("RUN_MOCK_MCP") != "1":
        pytest.skip("Set RUN_MOCK_MCP=1")
    from langchain_mcp_adapters.client import MultiServerMCPClient
    root = Path(__file__).resolve().parents[2]
    client = MultiServerMCPClient({"business": {"transport": "stdio",
        "command": str(root / "mcp/.venv/bin/python"), "args": ["-m", "business_mcp.server"],
        "cwd": str(root / "mcp"), "env": {"MCP_TRANSPORT": "stdio", "USE_STUB": "true",
        "DEFAULT_ACTING_USER_ID": "1"}}}, tool_name_prefix=True)

    async def loader():
        return await client.get_tools(server_name="business")

    state = {"user": {"locale": "en"}, "messages": [HumanMessage("Jaw botox October 22–24, sorted by price.")]}
    tools, results = make_coordinator_tools(loader, initial_state=state)
    found = await tools[1].ainvoke({"operation": "search", "arguments": {"procedure_code": "JAW_BOTOX",
        "date_from": "2026-10-22", "date_to": "2026-10-24", "sort_by": "PRICE"}})
    assert 0 < len(found["hospitals"]) <= 5
    for h in found["hospitals"]:
        print(h["id"], h["name"], h.get("min_price_krw"))
    chosen = found["hospitals"][0]
    state["messages"].append(HumanMessage(f"For this test, I choose hospital ID {chosen['id']}."))
    brief = await tools[1].ainvoke({"operation": "prepare_handoff", "arguments": {"hospital_id": chosen["id"]}})
    assert brief["status"] == "summary_ready"
    assert chosen["name"] in brief["summary"]
    assert results["selected_hospital_id"] == chosen["id"]
    print(brief["summary"])
