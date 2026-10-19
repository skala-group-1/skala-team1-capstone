"""camelCase ↔ snake_case 변환.

12 계약서 1장: backend JSON 은 camelCase, MCP 도구 입출력(Python)은 snake_case.
business-mcp 가 경계에서 한 번만 변환한다 (agent 는 snake_case 만 본다).
"""

from __future__ import annotations

import re
from typing import Any

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])([A-Z])")


def to_snake(name: str) -> str:
    """priceKrw → price_krw, holdExpiresAt → hold_expires_at"""
    return _CAMEL_BOUNDARY.sub(r"_\1", name).lower()


def to_camel(name: str) -> str:
    """price_krw → priceKrw"""
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def keys_to_snake(value: Any) -> Any:
    """dict/list 를 재귀로 돌며 key 만 snake_case 로 바꾼다 (값은 그대로)."""
    if isinstance(value, dict):
        return {to_snake(k) if isinstance(k, str) else k: keys_to_snake(v) for k, v in value.items()}
    if isinstance(value, list):
        return [keys_to_snake(v) for v in value]
    return value


def keys_to_camel(value: Any) -> Any:
    if isinstance(value, dict):
        return {to_camel(k) if isinstance(k, str) else k: keys_to_camel(v) for k, v in value.items()}
    if isinstance(value, list):
        return [keys_to_camel(v) for v in value]
    return value
