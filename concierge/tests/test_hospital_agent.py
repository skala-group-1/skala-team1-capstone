"""Hospital node checks without external services."""
import importlib
import json
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

from concierge.nodes.hospital_reply import internal_labels, patient_reply

agent = importlib.import_module("concierge.nodes.hospital_agent")
context = importlib.import_module("concierge.nodes.load_hospital_context")


def call(name, args, id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": id}])


def fake_tool(name):
    async def lookup(hospital_id: int, procedure_code: str = ""):
        return {"id": hospital_id}
    return StructuredTool.from_function(coroutine=lookup, name=name, description="test lookup")


@pytest.fixture
def state():
    return {"mode": "HOSPITAL", "selected_hospital_id": 7, "user": {"locale": "ja"},
            "hospital_context": {"hospital_id": 7, "detail": {"id": 7}},
            "messages": [HumanMessage("予約したいです")]}


def model_setup(monkeypatch, responses):
    async def reads(name, args):
        return {
            "business_list_doctors": {"doctors": [{"id": 11, "name": "Test doctor"}]},
            "business_get_price_options": {"options": []},
            "business_get_available_slots": {"slots": [{"id": 12, "doctor_id": 11,
                "start_at": "2026-10-22T10:00:00+09:00", "status": "AVAILABLE"}]},
        }[name]
    monkeypatch.setattr("concierge.nodes.actions.lookup", AsyncMock(side_effect=reads))
    class Model:
        def __init__(self):
            self.bound_tool_names = []

        def bind_tools(self, tools, **kwargs):
            self.bound_tool_names.append([tool["name"] if isinstance(tool, dict) else tool.name for tool in tools])
            return self
    model = Model()
    model.ainvoke = AsyncMock(side_effect=responses)
    monkeypatch.setattr(agent, "_model", lambda: model)
    monkeypatch.setattr(agent, "get_tools", AsyncMock(return_value=[
        fake_tool("business_get_available_slots"), fake_tool(agent.BOOK)]))
    return model


async def test_context_cache(monkeypatch):
    loader = AsyncMock(return_value=[fake_tool(name) for name in (
        "business_get_hospital_detail", "business_list_doctors", "business_get_price_options")])
    monkeypatch.setattr(context, "get_tools", loader)
    state = {"selected_hospital_id": 7, "conditions": {"procedure_code": "JAW_BOTOX"}}
    update = await context.load_hospital_context(state)
    assert "JAW_BOTOX" in update["hospital_context"]["prices"]
    await context.load_hospital_context({**state, **update})
    assert loader.await_count == 1
    assert "business_get_available_slots" not in loader.call_args.args[0]


async def test_context_hospital_change(monkeypatch):
    monkeypatch.setattr(context, "get_tools", AsyncMock(return_value=[
        fake_tool("business_get_hospital_detail"), fake_tool("business_list_doctors")]))
    result = await context.load_hospital_context({"selected_hospital_id": 8,
        "hospital_context": {"hospital_id": 7, "detail": {"id": 7}}})
    assert result["hospital_context"]["detail"]["id"] == 8
    assert result["hospital_booking"] == {}


async def test_missing_hospital(monkeypatch):
    loader = AsyncMock()
    monkeypatch.setattr(context, "get_tools", loader)
    with pytest.raises(ValueError, match="selected hospital"):
        await context.load_hospital_context({})
    loader.assert_not_awaited()


async def test_partial_choices_and_question(monkeypatch, state):
    model = model_setup(monkeypatch, [call(agent.COLLECT, {"procedure_code": "JAW_BOTOX"}),
                                    AIMessage(content="ご希望の日付と時間を教えてください。")])
    result = await agent.hospital_agent(state)
    assert result["hospital_booking"] == {"procedure_code": "JAW_BOTOX"}
    assert "日付" in result["draft"]
    assert '"locale": "ja"' in model.ainvoke.call_args.args[0][1].content
    assert isinstance(result["messages"][-1], ToolMessage)


async def test_forces_selected_hospital(monkeypatch, state):
    model_setup(monkeypatch, [call("business_get_available_slots", {"hospital_id": 999,
        "procedure_code": "JAW_BOTOX", "date_from": "2026-10-22", "date_to": "2026-10-22"})])
    result = await agent.hospital_agent(state)
    assert result["messages"][-1].tool_calls[0]["args"]["hospital_id"] == 7


def slot_messages():
    return [call("business_get_available_slots", {"hospital_id": 7, "procedure_code": "JAW_BOTOX"}),
            ToolMessage(content=json.dumps({"slots": [{"id": 12, "start_at": "2026-10-22T10:00:00+09:00", "status": "AVAILABLE"}]}), tool_call_id="c1")]


async def test_proposes_matching_fresh_slot(monkeypatch, state):
    state["hospital_booking"] = {"date": "2026-10-22", "time": "10:00", "procedure_code": "JAW_BOTOX"}
    state["messages"] += slot_messages()
    model_setup(monkeypatch, [call(agent.BOOK, {"hospital_id": 999, "slot_id": 12, "procedure_code": "JAW_BOTOX"})])
    result = await agent.hospital_agent(state)
    args = result["messages"][-1].tool_calls[0]["args"]
    assert args["hospital_id"] == 7 and args["slot_id"] == 12
    assert args["idempotency_key"]


@pytest.mark.parametrize("invalid", ["missing", "stale", "wrong_time", "wrong_procedure"])
async def test_invalid_booking(monkeypatch, state, invalid):
    state["hospital_booking"] = {"date": "2026-10-22", "time": "10:00", "procedure_code": "JAW_BOTOX"}
    state["messages"] += slot_messages()
    if invalid == "missing":
        state["hospital_booking"].pop("time")
    elif invalid == "stale":
        state["messages"].append(HumanMessage("book"))
    elif invalid == "wrong_time":
        state["hospital_booking"]["time"] = "11:00"
    args = {"hospital_id": 7, "slot_id": 12, "procedure_code": "OTHER" if invalid == "wrong_procedure" else "JAW_BOTOX"}
    model_setup(monkeypatch, [call(agent.BOOK, args), AIMessage(content="Please confirm your booking choices.")])
    result = await agent.hospital_agent(state)
    assert result["messages"][-1].status == "error"
    assert result["draft"]


async def test_human_mode(monkeypatch, state):
    factory = AsyncMock()
    monkeypatch.setattr(agent, "_model", factory)
    assert await agent.hospital_agent({**state, "mode": "HUMAN"}) == {}
    factory.assert_not_called()


def test_invalid_preferences():
    previous = {"time": "10:00"}
    with pytest.raises(ValueError):
        agent._preferences(previous, {"time": "25:00"})
    assert previous == {"time": "10:00"}


@pytest.mark.parametrize("effort", ["low", None, ""])
def test_model_reasoning_effort_is_configurable(monkeypatch, effort):
    from app.config import Settings
    monkeypatch.setattr(agent, "get_settings", lambda: Settings(
        _env_file=None, openai_api_key="test-key", llm_reasoning_effort=effort,
    ))
    assert agent._model().reasoning_effort == (effort or None)


async def test_price_option_id_can_be_removed_without_changing_price():
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content="국산 제품: 150,000원, 50단위 × 2회.")
    assert await patient_reply("옵션 10: 국산 제품: 150,000원, 50단위 × 2회.", "ko", model) == (
        "국산 제품: 150,000원, 50단위 × 2회."
    )
    assert "literal copy editor" in model.ainvoke.call_args.args[0][0].content


# Display guard regression cases use deliberately noncompliant model responses.
async def test_clean_reply_does_not_call_model():
    model = AsyncMock()
    text = "턱 보톡스는 150,000원이며, 2026-10-22 10:00에 가능합니다."
    assert await patient_reply(text, "ko", model) == text
    model.ainvoke.assert_not_awaited()


@pytest.mark.parametrize("locale,text", [
    ("ko", "턱 보톡스: 150,000원, 2026-10-22 10:00. 병원 승인 대기 중입니다."),
    ("en", "Jaw Botox: KRW 150,000, 2026-10-22 10:00. Awaiting hospital approval."),
    ("ja", "エラボトックス: 150,000ウォン、2026-10-22 10:00。病院の承認待ちです。"),
    ("zh", "瘦脸肉毒素注射：150,000韩元，2026-10-22 10:00。等待医院批准。"),
])
async def test_rewrite_removes_codes_and_ids_preserving_facts(locale, text):
    original = "JAW_BOTOX: 150,000 KRW, Slot 12: 2026-10-22 10:00. PENDING."
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content=text)
    assert await patient_reply(original, locale, model) == text
    assert model.ainvoke.await_count == 1
    request = json.loads(model.ainvoke.call_args.args[0][-1].content)
    assert request["locale"] == locale


@pytest.mark.parametrize("rewrite", [
    "턱 보톡스(JAW_BOTOX): 150,000원, 2026-10-22 10:00",
    "턱 보톡스: 15,000원, 2026-10-22 10:00",
    "턱 보톡스: 150,000원, 2026-10-23 10:00",
    "턱 보톡스: 150,000원, 2026-10-22 11:00",
    "턱 보톡스: 150,000원",
    "",
])
async def test_bad_rewrite_never_reaches_patient(rewrite):
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content=rewrite)
    original = "JAW_BOTOX: 150,000 KRW, 2026-10-22 10:00."
    result = await patient_reply(original, "ko", model)
    assert result != original and result != rewrite
    assert "다시" in result
    assert not internal_labels(result)
    assert model.ainvoke.await_count == 1


async def test_rewrite_provider_failure_is_not_exposed():
    model = AsyncMock()
    model.ainvoke.side_effect = RuntimeError("provider detail must not appear")
    result = await patient_reply("slot_id를 알려주세요.", "ko", model)
    assert "provider" not in result and "slot_id" not in result
    assert "다시" in result


async def test_rewrite_cannot_issue_tools():
    model = AsyncMock()
    model.ainvoke.return_value = call(agent.BOOK, {"slot_id": 12})
    result = await patient_reply("PENDING", "en", model)
    assert "Please send" in result


async def test_valid_citation_target_can_contain_code():
    model = AsyncMock()
    text = "See [the procedure guide](doc://JAW_BOTOX)."
    assert await patient_reply(text, "en", model) == text
    model.ainvoke.assert_not_awaited()


async def test_rewrite_cannot_drop_citations():
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content="Jaw Botox.")
    result = await patient_reply("JAW_BOTOX [guide](doc://JAW_BOTOX)", "en", model)
    assert result != "Jaw Botox."


def test_slot_time_is_not_treated_as_an_id():
    assert internal_labels("Slot 10:00") == []
    assert internal_labels("Slot 12: 10:00") == ["Slot 12:"]
    assert internal_labels("slot_id, doctorId, PENDING, ko/en/zh/ja")
    assert not internal_labels("VAT, KRW, Botox, Ultherapy, Shurink")


async def test_node_guards_final_draft_without_touching_booking(monkeypatch, state):
    state["user"]["locale"] = "ko"
    state["hospital_booking"] = {"procedure_code": "JAW_BOTOX"}
    model = model_setup(monkeypatch, [
        AIMessage(content="턱 보톡스(JAW_BOTOX) 가격은 150,000원입니다."),
        AIMessage(content="턱 보톡스 가격은 150,000원입니다."),
    ])
    result = await agent.hospital_agent(state)
    assert result["draft"] == "턱 보톡스 가격은 150,000원입니다."
    assert result["hospital_booking"] == {"procedure_code": "JAW_BOTOX"}
    assert model.ainvoke.await_count == 2


@pytest.mark.parametrize("skipped_preferences", [False, True])
async def test_booking_tool_requires_recorded_choices_and_current_matching_slot(monkeypatch, state, skipped_preferences):
    state["messages"] = [HumanMessage(
        "Please book jaw Botox on October 22, 2026 at 10:00 and show the approval card.")]
    premature = [call(agent.BOOK, {"slot_id": 12, "procedure_code": "JAW_BOTOX"}, id="premature")] if skipped_preferences else []
    model = model_setup(monkeypatch, [
        *premature,
        call(agent.COLLECT, {"procedure_code": "JAW_BOTOX", "date": "2026-10-22", "time": "10:00"}, id="preferences"),
        call("business_get_available_slots", {"hospital_id": 7, "procedure_code": "JAW_BOTOX"}),
        call(agent.BOOK, {"hospital_id": 7, "slot_id": 12, "procedure_code": "JAW_BOTOX"}),
    ])
    update = await agent.hospital_agent(state)
    assert all(agent.BOOK not in names for names in model.bound_tool_names)
    if skipped_preferences:
        assert update["messages"][1].status == "error"
        assert "record_booking_preferences" in update["messages"][1].content
    assert update.get("pending_action") is None
    state = {**state, **update, "messages": [*state["messages"], *update["messages"], slot_messages()[-1]]}
    proposal = await agent.hospital_agent(state)
    assert agent.BOOK in model.bound_tool_names[-1]
    assert proposal["pending_action"]["args"]["slot_id"] == 12
    assert proposal["pending_action"]["approved"] is False


@pytest.mark.parametrize("invalid", ["missing", "stale", "wrong_time", "wrong_hospital", "wrong_procedure", "unavailable"])
async def test_booking_tool_hidden_until_prerequisites_match(monkeypatch, state, invalid):
    state["hospital_booking"] = {"date": "2026-10-22", "time": "10:00", "procedure_code": "JAW_BOTOX"}
    state["messages"] += slot_messages()
    if invalid == "missing":
        state["hospital_booking"].pop("time")
    elif invalid == "stale":
        state["messages"].append(HumanMessage("Please book it."))
    elif invalid == "wrong_time":
        state["hospital_booking"]["time"] = "11:00"
    elif invalid == "wrong_hospital":
        state["messages"][-2].tool_calls[0]["args"]["hospital_id"] = 8
    elif invalid == "wrong_procedure":
        state["messages"][-2].tool_calls[0]["args"]["procedure_code"] = "OTHER"
    else:
        state["messages"][-1].content = state["messages"][-1].content.replace("AVAILABLE", "BOOKED")
    model = model_setup(monkeypatch, [AIMessage(content="Please confirm your booking choices.")])
    await agent.hospital_agent(state)
    assert agent.BOOK not in model.bound_tool_names[0]


async def test_new_cancellation_request_after_booking_approval_is_available(monkeypatch, state):
    from concierge.nodes.actions import CANCEL
    state["messages"] += [
        call(agent.BOOK, {"slot_id": 12, "procedure_code": "JAW_BOTOX"}),
        ToolMessage(content='{"id": 23, "status": "PENDING"}', tool_call_id="c1",
                    additional_kwargs={"approval_completed": True}),
    ]
    model = model_setup(monkeypatch, [AIMessage(content="Your booking request is awaiting hospital approval.")])
    tools = [fake_tool(agent.BOOK), fake_tool(CANCEL), fake_tool("business_get_my_reservations")]
    monkeypatch.setattr(agent, "get_tools", AsyncMock(return_value=tools))
    await agent.hospital_agent(state)
    assert CANCEL not in model.bound_tool_names[0]
    state["messages"].append(HumanMessage("Please cancel reservation 23 and show the approval card."))
    model.ainvoke.side_effect = [call(CANCEL, {"reservation_id": 23}, id="cancel")]
    proposal = {"args": {"reservation_id": 23}, "approved": False}
    prepare = AsyncMock(return_value=proposal)
    monkeypatch.setattr(agent, "prepare_action", prepare)
    result = await agent.hospital_agent(state)
    assert CANCEL in model.bound_tool_names[-1]
    assert result["pending_action"] == proposal
    prepare.assert_awaited_once()
