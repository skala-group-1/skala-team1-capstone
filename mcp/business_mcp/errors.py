"""ToolError 규칙 (04 문서 1장 '오류 처리 규칙').

원칙: LLM 이 다음 행동을 고를 수 있게 메시지에 '무엇이 틀렸고 무엇을 하면 되는지'를 넣는다.
backend 오류 응답 형식은 12 계약서 3장 { code, message, traceId, details }.
"""

from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ToolError


def unknown_procedure(text: str, known_codes: list[str]) -> ToolError:
    return ToolError(
        f"Unknown procedure '{text}'. Use business_normalize_procedure first. "
        f"Known codes: {', '.join(known_codes)}"
    )


def not_found(resource: str, resource_id: Any, hint: str) -> ToolError:
    # 예: Hospital 999 not found. Use an id from business_search_hospitals results.
    return ToolError(f"{resource} {resource_id} not found. {hint}")


def slot_unavailable(slot_id: int, alternatives: list[dict[str, Any]]) -> ToolError:
    alts = ", ".join(f"{a['id']} ({a['start_at']})" for a in alternatives[:3]) or "none"
    return ToolError(f"Slot {slot_id} is no longer available. Nearest available slots: {alts}.")


def access_denied() -> ToolError:
    return ToolError("Not permitted for this user. Do not retry.")


def temporary_backend_error() -> ToolError:
    return ToolError("Temporary backend error. You may retry once.")


def from_backend_error(status: int, body: dict[str, Any] | None) -> ToolError:
    """backend 4xx/5xx 응답 → ToolError. HttpBackendClient 가 사용."""
    body = body or {}
    code = body.get("code", "")
    details = body.get("details") or {}
    if status == 403:
        return access_denied()
    if status == 404:
        return not_found(details.get("resource", "Resource"), "", "Use an id from previous tool results.")
    if code == "SLOT_UNAVAILABLE":
        return slot_unavailable(details.get("slotId", 0), details.get("alternatives", []))
    if code == "UNKNOWN_PROCEDURE":
        return unknown_procedure(details.get("text", ""), [c.get("code", "") for c in details.get("candidates", [])])
    if status >= 500:
        return temporary_backend_error()
    # TODO(mcp): 409 CONCURRENT_UPDATE / INVALID_STATE_TRANSITION / CONSENT_REQUIRED 등
    #            코드별 안내 문구를 04 문서 표 형식으로 추가 (12 계약서 3장 오류 코드 표)
    return ToolError(f"{code or 'ERROR'}: {body.get('message', 'Request failed')}")
