import pytest
from fastapi.testclient import TestClient

from app import summarize as summarize_module
from app.main import app


class FakeStructuredLLM:
    """structured output LLM 대역. 호출된 프롬프트를 기록한다."""

    def __init__(self, result):
        self._result = result
        self.calls: list[str] = []

    async def ainvoke(self, prompt: str):
        self.calls.append(prompt)
        return self._result(prompt) if callable(self._result) else self._result


@pytest.fixture
def fake_llm(monkeypatch):
    """summarize._structured_llm 을 가짜로 바꾼다. install(CardDraft | 함수) → FakeStructuredLLM."""
    def install(result):
        llm = FakeStructuredLLM(result)
        monkeypatch.setattr(summarize_module, "_structured_llm", lambda: llm)
        return llm
    return install


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
