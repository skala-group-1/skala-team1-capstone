import pytest

from app import translate


class FakeStructuredLLM:
    """structured output LLM 대역. 호출된 프롬프트를 기록한다."""

    def __init__(self, result):
        self._result = result
        self.calls: list[str] = []

    async def ainvoke(self, prompt: str):
        self.calls.append(prompt)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result(prompt) if callable(self._result) else self._result


@pytest.fixture
def fake_llm(monkeypatch):
    """translate._structured_llm 을 가짜로 바꾼다. install(결과 모델 | 예외 | 함수) → FakeStructuredLLM."""
    def install(result):
        llm = FakeStructuredLLM(result)
        monkeypatch.setattr(translate, "_structured_llm", lambda schema: llm)
        return llm
    return install
