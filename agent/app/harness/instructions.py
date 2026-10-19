"""Harness — Instructions (「Harness 명세」). 프롬프트는 prompts/*.md 에만 두고 코드에 하드코딩하지 않는다."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(name: str) -> str:
    """prompts/{name}.md 본문을 돌려준다.

    TODO(agent): 상단 `version:` 메타를 파싱해 LangSmith 메타데이터로 남기기
    TODO(agent): 테스트 — 모든 노드가 쓰는 프롬프트 파일이 존재하는지 (「Harness 명세」 Instructions 테스트)
    """
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
