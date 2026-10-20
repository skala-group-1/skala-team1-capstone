"""시술 용어집 (data/mock/out/glossary.json, 66건 — term_ko/en/zh/ja).

기동 시 한 번 로드하고, 번역 프롬프트에는 **원문에 등장하는 용어만** 골라 넣는다 (전체 주입 금지 — 토큰 낭비).
"""

import json

from app.config import get_settings

LANG_KEY = {"ko": "term_ko", "en": "term_en", "zh": "term_zh", "ja": "term_ja"}

_terms: list[dict] | None = None


def load_glossary() -> list[dict]:
    global _terms
    if _terms is None:
        _terms = json.loads(get_settings().glossary_path.read_text(encoding="utf-8"))
    return _terms


def select_terms(text: str, from_: str, to: str) -> list[tuple[str, str]]:
    """원문(from_ 언어)에 등장하는 용어만 (원문 용어, 타깃 용어) 쌍으로 돌려준다."""
    src_key = LANG_KEY.get(from_)
    dst_key = LANG_KEY.get(to)
    if not src_key or not dst_key:
        return []
    lowered = text.lower()
    pairs = []
    for term in load_glossary():
        src = term.get(src_key)
        dst = term.get(dst_key)
        if src and dst and src.lower() in lowered:
            pairs.append((src, dst))
    return pairs


def format_glossary(pairs: list[tuple[str, str]]) -> str:
    return "\n".join(f"- {src} → {dst}" for src, dst in pairs)
