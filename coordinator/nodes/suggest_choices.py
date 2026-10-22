"""suggest_choices — 답변이 선택형 질문일 때 칩 라벨 추출 (DONE.suggestions).

- 답변 토큰이 모두 스트리밍된 뒤 실행되는 후처리 LLM 1회. USER_ANSWER_TAG 가 없는
  모델만 받는다 (태그가 있으면 workers/consumer.py 가 TOKEN 으로 사용자에게 중계한다).
- 실패하거나 선택형이 아니면 빈 리스트: 칩은 보조 UX 라 답변 자체를 막지 않는다.
- 계약: DONE {answer, sources, suggestions?} — 최대 4개, 사용자 locale.
  FE 는 칩을 탭하면 문구를 그대로 message 로 보낸다 (frontend/src/types/contract.ts).
"""

import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.harness.instructions import load_prompt

logger = logging.getLogger(__name__)

MAX_CHOICES = 4
MAX_LABEL_LENGTH = 40
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

_client = None


def suggest_client():
    """Shared across turns: a fresh client per answer would pay connection setup again.

    USER_ANSWER_TAG 금지 (붙이면 workers/consumer.py 가 TOKEN 으로 사용자에게 중계).
    단순 추출 작업이라 minimal reasoning + 짧은 출력 상한으로 칩 지연을 줄인다.
    """
    global _client
    if _client is None:
        import langchain_openai

        from app.config import get_settings
        settings = get_settings()
        key = settings.openai_api_key
        if not key or any(c.isspace() for c in key):
            return None
        options = {"reasoning_effort": "minimal"} if settings.llm_reasoning_effort else {}
        _client = langchain_openai.ChatOpenAI(model=settings.llm_primary_model, api_key=key,
                                              timeout=15, max_retries=0, max_tokens=300, **options)
    return _client


def clean_choices(names):
    """Dedupe and trim free-form labels into at most four short chips."""
    choices = []
    for name in names or []:
        if not isinstance(name, str):
            continue
        label = " ".join(name.split())
        if label and len(label) <= MAX_LABEL_LENGTH and label not in choices:
            choices.append(label)
        if len(choices) == MAX_CHOICES:
            break
    return choices


async def suggest_choices(answer, locale, model):
    """Extract chip labels when the answer asks the user to pick among stated options."""
    if not isinstance(answer, str) or not ("?" in answer or "？" in answer):
        return []
    try:
        reply = await model.ainvoke([
            SystemMessage(content=load_prompt("suggest_choices", directory=PROMPTS_DIR)),
            HumanMessage(content=json.dumps({"locale": locale, "answer": answer}, ensure_ascii=False)),
        ])
        content = (reply.content or "").strip()
        if content.startswith("```"):
            content = content.strip("`").removeprefix("json").strip()
        parsed = json.loads(content)
    except Exception as error:
        # Never stringify provider errors: they can contain credentials.
        logger.warning("suggest_choices skipped (%s)", type(error).__name__)
        return []
    return clean_choices(parsed if isinstance(parsed, list) else [])
