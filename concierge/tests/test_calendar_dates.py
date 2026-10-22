from datetime import date
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, START, END

from app.graph.state import AgentState
from concierge.nodes.calendar_dates import request_calendar, validate_slot_dates, slot_reply, availability_only
from concierge.nodes.hospital_agent import hospital_agent
from concierge.nodes.tools import hospital_tools


@pytest.mark.parametrize("text,today,start,end", [
    ("다음 주 가능해?", date(2026, 10, 22), "2026-10-26", "2026-11-01"),
    ("다다음주 예약 가능해?", date(2026, 12, 24), "2027-01-04", "2027-01-10"),
    ("내일 가능해?", date(2026, 12, 31), "2027-01-01", "2027-01-01"),
    ("모레 가능해?", date(2028, 2, 28), "2028-03-01", "2028-03-01"),
    ("11월 9일부터 15일까지 최수성 선생님", date(2026, 10, 22), "2026-11-09", "2026-11-15"),
    ("2026-12-30부터 2027-01-03까지", date(2026, 10, 22), "2026-12-30", "2027-01-03"),
    ("오늘 물어본 11월 9일", date(2026, 10, 22), "2026-11-09", "2026-11-09"),
])
def test_relative_dates(text, today, start, end):
    assert request_calendar(text, today) == {"date_from": start, "date_to": end}


def test_second_week_of_november_requires_explicit_dates():
    scope = request_calendar("11월 둘째 주 최수성 선생님 시간 알려줘", date(2026, 10, 22))
    assert scope["clarify"]
    assert ("2026-11-02", "2026-11-08") in scope["ranges"]
    assert ("2026-11-09", "2026-11-15") in scope["ranges"]


@pytest.mark.parametrize("text", ["내일 말고 다음 주", "다음 주 월요일", "내일부터 모레까지",
                                 "11월 둘째 주 말고 11월 2일"])
def test_compound_requests_are_not_overridden(text):
    assert request_calendar(text, date(2026, 10, 22)) == {}


@pytest.mark.parametrize("args", [
    {"date_from": "2026-11-09", "date_to": "2026-11-02"},
    {"date_from": "2026-02-30", "date_to": "2026-03-01"},
    {"date_from": "2026-11-02", "date_to": "2026-11-08"},
])
def test_invalid_or_different_week_is_rejected(args):
    with pytest.raises(ValueError):
        validate_slot_dates(args, {"date_from": "2026-11-09", "date_to": "2026-11-15"})


async def test_ambiguous_month_week_asks_before_model_or_slot_query(monkeypatch):
    model = AsyncMock()
    monkeypatch.setattr("concierge.nodes.hospital_agent._model", model)
    monkeypatch.setattr("concierge.nodes.hospital_agent.get_tools", AsyncMock(return_value=[]))
    result = await hospital_agent({"mode": "HOSPITAL", "selected_hospital_id": 1,
        "hospital_context": {"hospital_id": 1}, "user": {"locale": "ko"},
        "messages": [HumanMessage("2026년 11월 둘째 주 시간 알려줘")]})
    assert "시작일과 종료일" in result["draft"]
    model.assert_not_called()


async def test_model_wrong_week_is_corrected_before_mcp_execution(monkeypatch):
    class Model:
        def bind_tools(self, *args, **kwargs):
            return self
    name = "business_get_available_slots"
    def query(start, end, call_id):
        return AIMessage(content="", tool_calls=[{"name": name, "id": call_id, "args": {
            "hospital_id": 1, "date_from": start, "date_to": end, "doctor_id": 2}}])
    model = Model()
    model.ainvoke = AsyncMock(side_effect=[
        query("2026-11-02", "2026-11-08", "wrong"),
        query("2026-11-09", "2026-11-15", "correct"),
    ])
    async def slots(hospital_id: int, date_from: str, date_to: str, doctor_id: int):
        raise AssertionError("The agent node only proposes reads")
    tool = StructuredTool.from_function(coroutine=slots, name=name, description="test")
    monkeypatch.setattr("concierge.nodes.hospital_agent._model", lambda: model)
    monkeypatch.setattr("concierge.nodes.hospital_agent.get_tools", AsyncMock(return_value=[tool]))
    result = await hospital_agent({"mode": "HOSPITAL", "selected_hospital_id": 1,
        "hospital_context": {"hospital_id": 1}, "user": {"locale": "ko"},
        "messages": [HumanMessage("2026년 11월 9일부터 15일까지 최수성 선생님 시간 알려줘")]})
    assert result["messages"][1].status == "error"
    assert result["messages"][-1].tool_calls[0]["args"]["date_from"] == "2026-11-09"
    assert model.ainvoke.await_count == 2


@pytest.mark.parametrize("start,doctor,ok", [
    ("2026-11-09T10:00:00+09:00", 2, True),
    ("2026-11-08T16:00:00+00:00", 2, True),
    ("2026-11-02T10:00:00+09:00", 2, False),
    ("2026-11-09T10:00:00+09:00", 3, False),
    ("2026-11-09T10:00:00", 2, False),
])
async def test_out_of_scope_slot_results_never_reach_model_as_success(monkeypatch, start, doctor, ok):
    async def slots(hospital_id: int, date_from: str, date_to: str, doctor_id: int):
        return {"slots": [{"id": 99, "start_at": start, "end_at": "2026-11-09T11:00:00+09:00", "doctor_id": doctor}]}
    name = "business_get_available_slots"
    tool = StructuredTool.from_function(coroutine=slots, name=name, description="test slots")
    monkeypatch.setattr("app.mcp_client.client.get_tools", AsyncMock(return_value=[tool]))
    builder = StateGraph(AgentState)
    builder.add_node("tools", hospital_tools)
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    result = await builder.compile().ainvoke({"selected_hospital_id": 1,
        "messages": [AIMessage(content="", tool_calls=[{"name": name, "id": "slots", "args": {
            "hospital_id": 1, "date_from": "2026-11-09", "date_to": "2026-11-15", "doctor_id": 2}}])]})
    message = result["messages"][-1]
    assert (message.status == "success") == ok
    if not ok:
        assert start not in message.content


def test_verified_slot_reply_preserves_exact_dates_and_scope():
    args = {"date_from": "2026-11-09", "date_to": "2026-11-15"}
    text = slot_reply(args, {"slots": [{"start_at": "2026-11-09T11:30:00+09:00",
        "end_at": "2026-11-09T12:00:00+09:00", "doctor_name": "최수성"}]}, "ko")
    assert "2026-11-09 ~ 2026-11-15" in text
    assert "2026-11-09 11:30–12:00 (최수성)" in text
    assert "전체 예약 가능 시간 목록은 아닐 수" in text
    assert "반환되지" in slot_reply(args, {"slots": []}, "ko")
    assert availability_only("최수성 선생님 예약 가능한 시간 조회해줘")
    assert not availability_only("그 시간으로 예약해줘")
