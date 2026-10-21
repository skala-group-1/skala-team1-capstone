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
        self.bindings = []

    def bind_tools(self, tools, **kwargs):
        self.bindings.append(kwargs)
        self.names = getattr(self, "names", set()) | {t.name for t in tools}
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
    assert model.names == {"procedure_consultation", "hospital_lookup", "collect_conditions"}
    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_tool_a_round_trip_is_unavailable_not_invented_evidence():
    model = ScriptedModel(call("procedure_consultation", {"question": "Explain pico toning"}),
                          AIMessage(content="External search is not connected."))
    result = await run_coordinator({"messages": [HumanMessage("Explain pico toning")]}, model)
    assert result["draft"] == "Unable to complete this request. Please try again later."


@pytest.mark.asyncio
async def test_missing_sort_prevents_lookup():
    loader = AsyncMock()
    tools, _ = make_coordinator_tools(loader, initial_state={"conditions": {"procedure_code": "JAW_BOTOX"}})
    response = await tools[1].ainvoke({"operation": "search", "arguments": {
        "procedure_code": "JAW_BOTOX", "date_from": "2026-10-22"}})
    assert response["status"] == "needs_input"
    assert response["missing"] == ["sort_by", "budget_max_krw", "consult_language"]
    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_caps_at_five_and_round_trip_summary_without_connection():
    @tool
    async def business_search_hospitals(procedure_code: str, date_from: str, sort_by: str, limit: int):
        """Existing MCP search boundary."""
        assert limit == 5
        return {"hospitals": [{"id": n, "name": f"Clinic {n}"} for n in range(1, 9)], "total": 8}

    loader = AsyncMock(return_value=[business_search_hospitals])
    state = {"conditions": {"procedure_code": "JAW_BOTOX"}, "optional_conditions_asked": True, "user": {"locale": "en"}, "messages": [HumanMessage(
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
    assert "candidates" not in second
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
    result = await run_coordinator({"messages": [HumanMessage("Explain")]}, model)
    assert result["candidates"] == []
    assert "Stopped" not in result["draft"]


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
    result = await run_coordinator({"messages": [HumanMessage("Reservations")]}, model, business_loader=loader)
    assert "SECRET" not in str(result) + str(model.history)
    assert result["draft"] == "Unable to complete this request. Please try again later."


@pytest.mark.asyncio
async def test_whitespace_key_fails_before_api(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "openai_api_key", "not-a-real-key\n")
    result = await run_coordinator({"user": {"locale": "ja"}, "messages": []})
    assert result["draft"] == "処理できませんでした。後ほど再度お試しください。"
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
        "command": os.environ.get("MCP_TEST_PYTHON", str(root / "mcp/.venv/bin/python")), "args": ["-m", "business_mcp.server"],
        "cwd": str(root / "mcp"), "env": {"MCP_TRANSPORT": "stdio", "USE_STUB": "true",
        "DEFAULT_ACTING_USER_ID": "1"}}}, tool_name_prefix=True)

    async def loader():
        return await client.get_tools(server_name="business")

    state = {"optional_conditions_asked": True, "user": {"locale": "en"}, "messages": [HumanMessage("Jaw botox October 22–24, sorted by price.")]}
    tools, results = make_coordinator_tools(loader, initial_state=state)
    found = await tools[1].ainvoke({"operation": "search", "arguments": {"procedure_code": "JAW_BOTOX",
        "date_from": "2026-10-22", "date_to": "2026-10-24", "sort_by": "PRICE"}})
    assert 0 < len(found["hospitals"]) <= 5
    for h in found["hospitals"]:
        print(h["id"], h["name"], h.get("min_price_krw"))
    compared = await tools[1].ainvoke({"operation": "compare", "arguments": {
        "hospital_ids": [h["id"] for h in found["hospitals"][:3]]}})
    assert 1 <= len(compared["columns"]) <= 3
    assert compared["procedure_code"] == "JAW_BOTOX"
    chosen = found["hospitals"][0]
    state["messages"].append(HumanMessage(f"For this test, I choose hospital ID {chosen['id']}."))
    brief = await tools[1].ainvoke({"operation": "prepare_handoff", "arguments": {"hospital_id": chosen["id"]}})
    assert brief["status"] == "summary_ready"
    assert chosen["name"] in brief["summary"]
    assert results["selected_hospital_id"] == chosen["id"]
    print(brief["summary"])


@pytest.mark.asyncio
async def test_two_turn_conditions_search_and_selection():
    """Scripted model, real tool dispatch/merge; no external LLM or DB writes."""
    from coordinator.nodes.open_hospital_conversation import run_open_hospital_conversation
    from coordinator.nodes.guard_input import guard_input

    first_fields = {"procedure_code": "DOUBLE_EYELID_NONINCISION", "areas": ["GANGNAM", "MYEONGDONG"],
                    "date_from": "2026-10-20", "date_to": "2026-10-26", "sort_by": "REVIEW_COUNT"}

    @tool
    async def business_normalize_procedure(text: str):
        """Normalization boundary."""
        assert text == "매몰 쌍꺼풀"
        return {"candidates": [{"code": "DOUBLE_EYELID_NONINCISION", "name": text, "score": 1.0}]}

    @tool
    async def business_search_hospitals(procedure_code: str, areas: list[str], date_from: str,
                                       date_to: str, sort_by: str, budget_max_krw: int, language: str, limit: int):
        """Search boundary checks every retained filter."""
        assert {"procedure_code": procedure_code, "areas": areas, "date_from": date_from,
                "date_to": date_to, "sort_by": sort_by} == first_fields
        assert (budget_max_krw, language, limit) == (2000000, "zh", 5)
        return {"hospitals": [{"id": 17, "name": "Test hospital", "min_price_krw": 1500000}], "total": 1}

    loader = AsyncMock(return_value=[business_normalize_procedure, business_search_hospitals])
    state = {"user": {"locale": "ko"}, "messages": [HumanMessage("매몰 쌍꺼풀 강남/명동 10/20~26 리뷰 많은 순")]}
    first = await run_coordinator(state, ScriptedModel(
        call("hospital_lookup", {"operation": "normalize", "arguments": {"text": "매몰 쌍꺼풀"}}),
        call("collect_conditions", {"fields": first_fields}, "collect"), AIMessage(content="Question")), business_loader=loader)
    assert first["conditions"] == first_fields
    assert first["missing"] == ["budget_max_krw", "consult_language"]
    assert first["optional_conditions_asked"] is True
    assert "최대 예산" in first["draft"] and "상담 언어" in first["draft"]
    state.update(first)
    state["messages"] += [AIMessage(first["draft"]), HumanMessage("200만원 이하 중국어상담")]
    second = await run_coordinator(state, ScriptedModel(
        call("collect_conditions", {"fields": {"budget_max_krw": 2000000, "consult_language": "zh"}}),
        call("hospital_lookup", {"operation": "search", "arguments": {}}, "search"),
        AIMessage(content="Test hospital")), business_loader=loader)
    assert second["missing"] == []
    assert second["candidates"][0]["id"] == 17
    state.update(second)
    state["action"] = {"type": "SELECT_HOSPITAL", "hospitalId": 17}
    state.update(guard_input(state))
    selected = await run_open_hospital_conversation(state, business_loader=AsyncMock(return_value=[]))
    assert selected["selected_hospital_id"] == 17
    assert all(str(v) in selected["summary"] for v in (2000000, "zh", "2026-10-20", "REVIEW_COUNT"))
    assert selected["opened_conversation"] is None and "mode" not in selected


@pytest.mark.asyncio
async def test_optional_question_is_not_repeated_or_bypassed_within_turn():
    conditions = {"procedure_code": "JAW_BOTOX", "date_from": "2026-10-22", "sort_by": "PRICE"}
    loader = AsyncMock(return_value=[])
    tools, results = make_coordinator_tools(loader, initial_state={"conditions": {"procedure_code": "JAW_BOTOX"}})
    first = await tools[2].ainvoke({"fields": conditions})
    second = await tools[1].ainvoke({"operation": "search", "arguments": {}})
    assert first["missing"] == second["missing"] == ["budget_max_krw", "consult_language"]
    loader.assert_not_awaited()
    tools, _ = make_coordinator_tools(loader, initial_state=results)
    next_turn = await tools[2].ainvoke({"fields": {}})
    assert next_turn["missing"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["empty", "error", "missing_tool"])
async def test_search_zero_or_failure_clears_stale_cards_without_relaxing(mode):
    @tool
    async def business_search_hospitals(procedure_code: str, date_from: str, sort_by: str, limit: int):
        """Search boundary."""
        if mode == "error":
            raise RuntimeError("Bearer SECRET")
        return {"hospitals": [], "total": 0}

    loader = AsyncMock(return_value=[] if mode == "missing_tool" else [business_search_hospitals])
    conditions = {"procedure_code": "JAW_BOTOX", "date_from": "2026-10-22", "sort_by": "PRICE"}
    model = ScriptedModel(call("hospital_lookup", {"operation": "search", "arguments": {}}), AIMessage(content="No matches / unavailable"))
    result = await run_coordinator({"optional_conditions_asked": True, "conditions": conditions,
                                   "candidates": [{"id": 99}], "selected_hospital_id": 99, "summary": "old"},
                                  model, business_loader=loader)
    assert result["candidates"] == [] and result["summary"] is None and result["selected_hospital_id"] is None
    assert result["conditions"] == conditions
    assert "SECRET" not in str(result) + str(model.history)
    loader.assert_awaited_once()


@pytest.mark.asyncio
async def test_compare_uses_saved_procedure_and_only_displayed_ids():
    @tool
    async def business_compare_hospitals(hospital_ids: list[int], procedure_code: str):
        """Comparison boundary."""
        assert hospital_ids == [17, 24] and procedure_code == "JAW_BOTOX"
        return {"procedure_code": procedure_code, "columns": [{"hospital": {"id": 17}, "verified_at": None}]}

    loader = AsyncMock(return_value=[business_compare_hospitals])
    tools, _ = make_coordinator_tools(loader, initial_state={"conditions": {"procedure_code": "JAW_BOTOX"},
                                                           "candidates": [{"id": 17}, {"id": 24}]})
    bad = await tools[1].ainvoke({"operation": "compare", "arguments": {"hospital_ids": [99]}})
    assert bad["status"] == "invalid_selection"
    loader.assert_not_awaited()
    result = await tools[1].ainvoke({"operation": "compare", "arguments": {"hospital_ids": [17, 24]}})
    assert result["columns"][0]["verified_at"] is None


@pytest.mark.asyncio
async def test_filter_change_invalidates_previous_handoff_and_cards():
    tools, result = make_coordinator_tools(AsyncMock(), initial_state={"conditions": {"budget_max_krw": 2000000},
                        "candidates": [{"id": 1}], "summary": "old", "selected_hospital_id": 1})
    await tools[2].ainvoke({"fields": {"budget_max_krw": 1000000}})
    assert result["hospitals"] == [] and result["summary"] is None
    assert (await tools[1].ainvoke({"operation": "prepare_handoff", "arguments": {"hospital_id": 1}}))["status"] == "invalid_selection"


@pytest.mark.asyncio
async def test_sort_action_overrides_old_history_and_invalid_sort_is_rejected():
    state = {"conditions": {"sort_by": "PRICE"}, "action": {"type": "SET_SORT", "sortBy": "RATING"}}
    result = await run_coordinator(state, ScriptedModel(
        call("collect_conditions", {"fields": {"sort_by": "PRICE"}}), AIMessage("Question")))
    assert result["conditions"]["sort_by"] == "RATING"
    result = await run_coordinator({"action": {"type": "SET_SORT", "sortBy": "BEST"}}, ScriptedModel())
    assert result["draft"] == "Unable to complete this request. Please try again later."


@pytest.mark.parametrize("fields", [{"budget_max_krw": -1}, {"budget_max_krw": True}, {"sort_by": "BEST"},
    {"date_from": "2026-10-26", "date_to": "2026-10-20"}, {"areas": ["INVENTED"]}, {"extra": "no"}])
def test_invalid_conditions_rejected(fields):
    from pydantic import ValidationError
    from coordinator.nodes.coordinator_tools import ConditionPatch
    with pytest.raises(ValidationError):
        ConditionPatch.model_validate(fields)


@pytest.mark.asyncio
async def test_no_preference_stays_explicit_after_search_without_null_mcp_arguments():
    @tool
    async def business_search_hospitals(procedure_code: str, date_from: str, sort_by: str, limit: int):
        """No optional arguments needed when the user has no preference."""
        return {"hospitals": [], "total": 0}

    loader = AsyncMock(return_value=[business_search_hospitals])
    fields = {"procedure_code": "JAW_BOTOX", "date_from": "2026-10-22", "sort_by": "PRICE",
              "areas": None, "budget_max_krw": None, "consult_language": None}
    tools, result = make_coordinator_tools(loader, initial_state={"conditions": {"procedure_code": "JAW_BOTOX"}})
    await tools[1].ainvoke({"operation": "search", "arguments": fields})
    assert result["conditions"] == fields
    tools, _ = make_coordinator_tools(loader, initial_state=result)
    assert (await tools[2].ainvoke({"fields": {}}))["missing"] == []


@pytest.mark.asyncio
async def test_skipped_collection_recovers_filters_and_discards_medical_prose():
    model = ScriptedModel(AIMessage("埋线恢复快 GANGNAM budget_max_krw"),
        call("collect_conditions", {"fields": {"areas": ["GANGNAM", "MYEONGDONG"],
             "date_from": "2026-10-20", "date_to": "2026-10-27"}}),
        AIMessage("埋线恢复快"))
    result = await run_coordinator({"user": {"locale": "zh"}, "messages": [HumanMessage(
        "10월 20일부터 일주일 강남이나 명동") ]}, model)
    assert any(b.get("tool_choice") == "collect_conditions" for b in model.bindings)
    assert result["conditions"]["areas"] == ["GANGNAM", "MYEONGDONG"]
    assert result["conditions"]["date_to"] == "2026-10-27"
    assert result["missing"]
    assert not any(term in result["draft"] for term in ("恢复", "GANGNAM", "budget_max_krw"))


@pytest.mark.asyncio
async def test_normalization_failure_keeps_explicit_filters_and_blocks_hallucinated_final():
    loader = AsyncMock(side_effect=RuntimeError("Bearer SECRET"))
    fields = {"procedure_code": "매몰 쌍꺼풀", "budget_max_krw": 2000000, "consult_language": "zh"}
    saved = {"areas": ["GANGNAM", "MYEONGDONG"], "date_from": "2026-10-20",
             "date_to": "2026-10-27", "sort_by": "REVIEW_COUNT"}
    model = ScriptedModel(call("collect_conditions", {"fields": fields}),
                          AIMessage("Clinic invented, painless, 100 KRW"))
    result = await run_coordinator({"conditions": saved, "user": {"locale": "zh"},
                                   "candidates": [{"id": 99}], "messages": []}, model, business_loader=loader)
    assert result["conditions"] == {**saved, "budget_max_krw": 2000000, "consult_language": "zh"}
    assert result["draft"] == "暂时无法完成请求，请稍后重试。"
    assert result["candidates"] == []
    assert "SECRET" not in str(result)


@pytest.mark.asyncio
async def test_raw_procedure_is_normalized_and_required_search_uses_retained_filters():
    @tool
    async def business_normalize_procedure(text: str):
        """Backend normalizer."""
        assert text == "매몰 쌍꺼풀"
        return {"candidates": [{"code": "DOUBLE_EYELID_NONINCISION", "name": "埋线双眼皮", "score": 1}]}

    @tool
    async def business_search_hospitals(procedure_code: str, areas: list[str], date_from: str,
                                       date_to: str, sort_by: str, budget_max_krw: int, language: str, limit: int):
        """Backend search rejects unnormalized input."""
        assert procedure_code == "DOUBLE_EYELID_NONINCISION"
        assert areas == ["GANGNAM", "MYEONGDONG"]
        assert (date_from, date_to, budget_max_krw, language, limit) == ("2026-10-20", "2026-10-27", 2000000, "zh", 5)
        return {"hospitals": [{"id": 17, "name": "测试医院", "min_price_krw": 1500000, "review_count": 20}], "total": 1}

    loader = AsyncMock(return_value=[business_normalize_procedure, business_search_hospitals])
    model = ScriptedModel(call("collect_conditions", {"fields": {"procedure_code": "매몰 쌍꺼풀",
                          "budget_max_krw": 2000000, "consult_language": "zh"}}),
                          AIMessage("No need to search: painless surgery at invented clinic"))
    result = await run_coordinator({"user": {"locale": "zh"}, "optional_conditions_asked": True,
        "conditions": {"areas": ["GANGNAM", "MYEONGDONG"], "date_from": "2026-10-20",
                       "date_to": "2026-10-27", "sort_by": "REVIEW_COUNT"}}, model, business_loader=loader)
    assert result["conditions"]["procedure_code"] == "DOUBLE_EYELID_NONINCISION"
    assert result["candidates"][0]["id"] == 17
    assert "测试医院" in result["draft"] and "1,500,000 KRW" in result["draft"]
    assert not any(term in result["draft"] for term in ("painless", "invented", "REVIEW_COUNT", "GANGNAM"))


@pytest.mark.asyncio
async def test_collection_refusal_cannot_become_user_facing_claim():
    result = await run_coordinator({"user": {"locale": "zh"}}, ScriptedModel(
        AIMessage("恢复快"), AIMessage("恢复快")))
    assert result["draft"] == "暂时无法完成请求，请稍后重试。"
    assert result["candidates"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("action", [{}, {"type": "SELECT_HOSPITAL", "hospitalId": 99},
                                    {"type": "SELECT_HOSPITAL", "hospitalId": True}])
async def test_open_requires_explicit_current_candidate(action):
    from coordinator.nodes.open_hospital_conversation import run_open_hospital_conversation
    loader = AsyncMock()
    result = await run_open_hospital_conversation({"action": action, "selected_hospital_id": 17,
        "candidates": [{"id": 17, "name": "Hospital"}]}, business_loader=loader)
    assert result["opened_conversation"] is None
    loader.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["HOSPITAL", "HUMAN"])
@pytest.mark.parametrize("conditions", [None, {}, {"budget_max_krw": 1000000}])
async def test_open_maps_real_conversation_without_changing_parent(mode, conditions):
    from coordinator.nodes.open_hospital_conversation import run_open_hospital_conversation
    parent = "11111111-1111-4111-8111-111111111111"
    child = "22222222-2222-4222-8222-222222222222"
    older_parent = "33333333-3333-4333-8333-333333333333"

    @tool
    async def business_open_hospital_conversation(hospital_id: int, parent_conversation_id: str):
        """Existing authorized conversation operation."""
        assert hospital_id == 17 and parent_conversation_id == parent
        return {"id": child, "hospital": {"id": 17, "name": "Hospital"}, "mode": mode,
                "conditions": conditions, "parent_conversation_id": older_parent,
                "consultation_id": 42 if mode == "HUMAN" else None}

    result = await run_open_hospital_conversation({"mode": "MAIN", "conversation_id": parent,
        "action": {"type": "SELECT_HOSPITAL", "hospitalId": 17}, "user": {"locale": "zh"},
        "candidates": [{"id": 17, "name": "Hospital"}], "conditions": {"budget_max_krw": 2000000}},
        business_loader=AsyncMock(return_value=[business_open_hospital_conversation]))
    assert result["opened_conversation"] == {"conversation_id": child, "hospital_id": 17, "mode": mode,
        "conditions": conditions, "parent_conversation_id": older_parent,
        "consultation_id": 42 if mode == "HUMAN" else None}
    assert result["selected_hospital_id"] == 17 and "2000000" in result["summary"]
    assert "mode" not in result and result["draft"] == "已打开医院对话。"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["error", "missing_tool", "wrong_hospital", "same_id", "bad_id", "bad_mode"])
async def test_open_failure_emits_no_conversation(failure):
    from coordinator.nodes.open_hospital_conversation import run_open_hospital_conversation
    parent = "11111111-1111-4111-8111-111111111111"

    @tool
    async def business_open_hospital_conversation(hospital_id: int, parent_conversation_id: str):
        """Invalid backend results must never become a UI event."""
        if failure == "error":
            raise RuntimeError("Bearer SECRET")
        return {"id": parent if failure == "same_id" else ("invalid" if failure == "bad_id" else "22222222-2222-4222-8222-222222222222"),
            "hospital": {"id": 99 if failure == "wrong_hospital" else 17},
            "mode": "MAIN" if failure == "bad_mode" else "HOSPITAL", "conditions": {}}

    result = await run_open_hospital_conversation({"conversation_id": parent,
        "action": {"type": "SELECT_HOSPITAL", "hospitalId": 17}, "candidates": [{"id": 17}]},
        business_loader=AsyncMock(return_value=[] if failure == "missing_tool" else [business_open_hospital_conversation]))
    assert result["opened_conversation"] is None and "mode" not in result
    assert "SECRET" not in str(result)
    assert "Unable to open" in result["draft"]


@pytest.mark.asyncio
async def test_model_cannot_resolve_ambiguous_procedure_without_new_user_turn():
    @tool
    async def business_normalize_procedure(text: str):
        """An ambiguous choice needs a human, not a model-selected valid code."""
        return {"candidates": [{"code": "A", "name": "Choice A", "score": 0.8},
                               {"code": "B", "name": "Choice B", "score": 0.8}]}

    tools, results = make_coordinator_tools(AsyncMock(return_value=[business_normalize_procedure]))
    await tools[2].ainvoke({"fields": {"procedure_code": "ambiguous name"}})
    response = await tools[2].ainvoke({"fields": {"procedure_code": "A", "budget_max_krw": 2000000}})
    assert "procedure_code" in response["missing"]
    assert "procedure_code" not in results["conditions"]
    assert results["conditions"]["budget_max_krw"] == 2000000
    assert len(response["normalization"]["candidates"]) == 2
