"""DONE.suggestions 선택지 칩: 선택형 질문일 때만, 답변에 있는 이름 그대로 최대 4개."""
import json
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from coordinator.nodes.planner_agent import run_coordinator
from coordinator.nodes.suggest_choices import clean_choices, suggest_choices


class ScriptedModel:
    def __init__(self, *replies):
        self.replies = iter(replies)
        self.history = []

    def bind_tools(self, tools, **kwargs):
        return self

    async def ainvoke(self, messages):
        self.history.append(messages)
        return next(self.replies)


@pytest.mark.asyncio
async def test_extracts_choices_for_closed_question():
    model = ScriptedModel(AIMessage(content='["매몰법", "절개법"]'))
    answer = "쌍커풀 수술에는 매몰법과 절개법이 있는데, 어떤 걸 원하시나요?"
    assert await suggest_choices(answer, "ko", model) == ["매몰법", "절개법"]
    payload = json.loads(model.history[0][1].content)
    assert payload == {"locale": "ko", "answer": answer}


@pytest.mark.asyncio
async def test_non_question_answer_skips_the_model():
    model = ScriptedModel()  # ainvoke would raise StopIteration if called
    assert await suggest_choices("보톡스는 근육 움직임을 줄이는 시술이에요.", "ko", model) == []
    assert model.history == []


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["not json", '{"answer": "no"}', '```json\n["강남", "명동"]\n```'])
async def test_model_output_is_parsed_defensively(content):
    expected = ["강남", "명동"] if content.startswith("```") else []
    model = ScriptedModel(AIMessage(content=content))
    assert await suggest_choices("강남과 명동 중 어디가 편하세요?", "ko", model) == expected


def test_clean_choices_caps_dedupes_and_drops_junk():
    assert clean_choices(["  매몰법 ", "매몰법", 3, "", "x" * 41, "절개법", "A", "B", "C"]) == [
        "매몰법", "절개법", "A", "B"]


@pytest.mark.asyncio
async def test_run_coordinator_attaches_suggestions_to_update():
    answer = "레이저리프팅, 레이저토닝, 보톡스 중 뭐가 궁금하세요?"
    model = ScriptedModel(AIMessage(content=answer))
    suggest = ScriptedModel(AIMessage(content='["레이저리프팅", "레이저토닝", "보톡스"]'))
    update = await run_coordinator(
        {"user": {"locale": "ko"}, "messages": [HumanMessage("피부가 처지는 것 같아")]},
        model, business_loader=AsyncMock(), suggest_model=suggest)
    assert update["draft"] == answer
    assert update["suggestions"] == ["레이저리프팅", "레이저토닝", "보톡스"]


def test_suggest_client_is_cached_minimal_and_untagged(monkeypatch):
    import langchain_openai

    from app.config import get_settings
    from coordinator.nodes import suggest_choices as module

    captured = []

    class CaptureOnly:
        def __init__(self, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "llm_reasoning_effort", "low")
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", CaptureOnly)
    monkeypatch.setattr(module, "_client", None)
    first = module.suggest_client()
    assert module.suggest_client() is first and len(captured) == 1
    assert captured[0]["reasoning_effort"] == "minimal"
    assert "tags" not in captured[0]  # USER_ANSWER_TAG 가 붙으면 TOKEN 으로 샌다


def test_suggest_client_refuses_bad_key(monkeypatch):
    from app.config import get_settings
    from coordinator.nodes import suggest_choices as module

    monkeypatch.setattr(get_settings(), "openai_api_key", "bad key\n")
    monkeypatch.setattr(module, "_client", None)
    assert module.suggest_client() is None


@pytest.mark.asyncio
async def test_run_coordinator_without_suggest_model_stays_empty():
    model = ScriptedModel(AIMessage(content="매몰법과 절개법 중 어떤 걸 원하시나요?"))
    update = await run_coordinator(
        {"user": {"locale": "ko"}, "messages": [HumanMessage("쌍커풀 하고 싶어")]},
        model, business_loader=AsyncMock())
    assert update["suggestions"] == []
