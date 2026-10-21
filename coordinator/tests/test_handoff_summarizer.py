"""Main→sub handoff through the summarizer (HANDOFF_TO_SUB) with code-assembled fallback."""
import json

import httpx
from langchain_core.messages import HumanMessage

from coordinator.nodes.coordinator_tools import summarizer_handoff_summary

STATE = {"user": {"user_id": 1, "role": "CUSTOMER", "locale": "en"},
         "messages": [HumanMessage("I want rhinoplasty in Gangnam")]}
CANDIDATES = [{"id": 7, "name": "Seoul Beauty Clinic"}]
CARD = {"procedure": "rhinoplasty (RHINOPLASTY)", "preferredDates": None, "stayDays": None,
        "budget": None, "questions": [], "customerLocale": "en"}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeClient:
    last_request = None

    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None):
        FakeClient.last_request = json
        return FakeResponse(self._payload)


async def test_handoff_uses_summarizer_card(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient",
                        lambda timeout=None: FakeClient({"summaryCard": CARD, "text": "ctx"}))
    out = await summarizer_handoff_summary(STATE, 7, CANDIDATES, {"procedure_code": "RHINOPLASTY"})
    assert out["status"] == "summary_ready" and out["selected_hospital_id"] == 7
    assert json.loads(out["summary"]) == {"summaryCard": CARD, "text": "ctx"}
    assert FakeClient.last_request["purpose"] == "HANDOFF_TO_SUB"
    assert FakeClient.last_request["locale"] == "en"
    assert FakeClient.last_request["conditions"] == {"procedureCode": "RHINOPLASTY"}
    assert FakeClient.last_request["messages"] == [
        {"role": "user", "content": "I want rhinoplasty in Gangnam"}]


async def test_handoff_falls_back_when_summarizer_unavailable(monkeypatch):
    def refuse(timeout=None):
        raise RuntimeError("summarizer down")
    monkeypatch.setattr(httpx, "AsyncClient", refuse)
    out = await summarizer_handoff_summary(STATE, 7, CANDIDATES, {})
    assert out["status"] == "summary_ready"
    assert "not sent" in out["summary"]


async def test_korean_handoff_uses_summarizer(monkeypatch):
    ko_card = {**CARD, "procedure": "코 성형 (RHINOPLASTY)", "customerLocale": "ko"}
    monkeypatch.setattr(httpx, "AsyncClient",
                        lambda timeout=None: FakeClient({"summaryCard": ko_card, "text": "ctx"}))
    state = {**STATE, "user": {"user_id": 1, "role": "CUSTOMER", "locale": "ko"},
             "messages": [HumanMessage("강남에서 코 성형 받고 싶어요")]}
    out = await summarizer_handoff_summary(state, 7, CANDIDATES, {})
    assert out["status"] == "summary_ready"
    assert json.loads(out["summary"]) == {"summaryCard": ko_card, "text": "ctx"}
    assert FakeClient.last_request["locale"] == "ko"


async def test_handoff_falls_back_for_unsupported_locale(monkeypatch):
    def explode(timeout=None):
        raise AssertionError("summarizer must not be called for an unsupported locale")
    monkeypatch.setattr(httpx, "AsyncClient", explode)
    state = {**STATE, "user": {"user_id": 1, "role": "CUSTOMER", "locale": "fr"}}
    out = await summarizer_handoff_summary(state, 7, CANDIDATES, {})
    assert out["status"] == "summary_ready"
    assert "not sent" in out["summary"]


async def test_handoff_rejects_mismatched_card(monkeypatch):
    wrong = {**CARD, "customerLocale": "ja"}
    monkeypatch.setattr(httpx, "AsyncClient",
                        lambda timeout=None: FakeClient({"summaryCard": wrong, "text": "ctx"}))
    out = await summarizer_handoff_summary(STATE, 7, CANDIDATES, {})
    assert out["status"] == "summary_ready"
    assert "not sent" in out["summary"]


async def test_invalid_selection_skips_summarizer():
    out = await summarizer_handoff_summary(STATE, 99, CANDIDATES, {})
    assert out["status"] == "invalid_selection"
