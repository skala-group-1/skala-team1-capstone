"""backend /internal/** 클라이언트.

- BackendClient       : 도구가 의존하는 인터페이스. 반환값은 모두 snake_case dict
- HttpBackendClient   : 실제 backend 호출 (USE_STUB=false)
- StubBackendClient   : mock JSON 근사 구현 (USE_STUB=true) → stub_backend.py

backend 쪽 계약 (「공통 계약서」 8장 + feat/be-bootstrap InternalCatalogController 기준)
- 헤더 X-Service-Token, X-Acting-User-Id 는 필수. 없으면 401
- X-Trace-Id 는 그대로 응답 헤더로 돌려준다 → 로그 상관관계에 사용
- locale 파라미터가 없으면 backend 가 acting user 의 locale 로 고른다
- 변경 API 는 Idempotency-Key 헤더
- compare 요청 바디 필드는 procedureCode (「API·이벤트 명세」의 procedure 는 alias 로만 허용)
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

import httpx

from business_mcp import errors
from business_mcp.config import settings
from business_mcp.context import CallContext
from mcp_common.casing import keys_to_camel, keys_to_snake


class BackendClient(Protocol):
    async def normalize_procedure(self, ctx: CallContext, text: str) -> dict[str, Any]: ...

    async def search_hospitals(self, ctx: CallContext, params: dict[str, Any]) -> dict[str, Any]: ...

    async def get_hospital_detail(self, ctx: CallContext, hospital_id: int) -> dict[str, Any]: ...

    async def list_doctors(self, ctx: CallContext, hospital_id: int, procedure_code: str | None) -> list[dict]: ...

    async def get_price_options(self, ctx: CallContext, hospital_id: int, procedure_code: str) -> list[dict]: ...

    async def get_available_slots(
        self, ctx: CallContext, hospital_id: int, procedure_code: str,
        date_from: str, date_to: str, doctor_id: int | None,
    ) -> list[dict]: ...

    async def compare_hospitals(self, ctx: CallContext, hospital_ids: list[int], procedure_code: str) -> dict: ...

    async def get_my_reservations(self, ctx: CallContext, status: str | None) -> list[dict]: ...

    async def plan_trip(self, ctx: CallContext, body: dict[str, Any]) -> dict[str, Any]: ...

    async def create_reservation(self, ctx: CallContext, body: dict[str, Any], idempotency_key: str) -> dict: ...

    async def cancel_reservation(self, ctx: CallContext, reservation_id: int, reason: str | None) -> dict: ...

    async def request_consultation(self, ctx: CallContext, body: dict[str, Any], idempotency_key: str) -> dict: ...


class HttpBackendClient:
    """실제 backend 호출. 타임아웃 3s, 5xx·타임아웃은 1회 재시도 후 ToolError (「MCP 설계」 1장)."""

    def __init__(self, base_url: str | None = None, service_token: str | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url=(base_url or settings.backend_internal_url).rstrip("/"),
            timeout=settings.backend_timeout_s,
        )
        self._service_token = service_token or settings.service_token

    def _headers(self, ctx: CallContext, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "X-Service-Token": self._service_token,
            "X-Acting-User-Id": str(ctx.acting_user_id),
            "X-Trace-Id": ctx.trace_id,
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def _request(
        self, method: str, path: str, ctx: CallContext, *,
        params: dict[str, Any] | None = None, json: Any = None, idempotency_key: str | None = None,
    ) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        if ctx.locale:
            params.setdefault("locale", ctx.locale)
        for attempt in range(2):  # 최초 1회 + 재시도 1회
            try:
                resp = await self._client.request(
                    method, path, params=params,
                    json=keys_to_camel(json) if json is not None else None,
                    headers=self._headers(ctx, idempotency_key),
                )
            except httpx.TimeoutException:
                if attempt == 0:
                    continue
                raise errors.temporary_backend_error()
            if resp.status_code >= 500 and attempt == 0:
                await asyncio.sleep(0.2)
                continue
            if resp.status_code >= 400:
                body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
                raise errors.from_backend_error(resp.status_code, body)
            return keys_to_snake(resp.json())
        raise errors.temporary_backend_error()

    # --- 조회 ---------------------------------------------------------------
    async def normalize_procedure(self, ctx, text):
        return await self._request("GET", "/procedures/normalize", ctx, params={"text": text})

    async def search_hospitals(self, ctx, params):
        # Conditions 와 같은 쿼리 이름 (camelCase). areas 는 리스트 → areas=A&areas=B
        query = keys_to_camel(params)
        return await self._request("GET", "/hospitals/search", ctx, params=query)

    async def get_hospital_detail(self, ctx, hospital_id):
        return await self._request("GET", f"/hospitals/{hospital_id}", ctx, params={"lite": "true"})

    async def list_doctors(self, ctx, hospital_id, procedure_code):
        return await self._request(
            "GET", f"/hospitals/{hospital_id}/doctors", ctx, params={"procedureCode": procedure_code})

    async def get_price_options(self, ctx, hospital_id, procedure_code):
        return await self._request(
            "GET", f"/hospitals/{hospital_id}/prices", ctx, params={"procedureCode": procedure_code})

    async def get_available_slots(self, ctx, hospital_id, procedure_code, date_from, date_to, doctor_id):
        return await self._request("GET", f"/hospitals/{hospital_id}/slots", ctx, params={
            "procedureCode": procedure_code, "dateFrom": date_from, "dateTo": date_to, "doctorId": doctor_id,
        })

    async def compare_hospitals(self, ctx, hospital_ids, procedure_code):
        return await self._request("POST", "/hospitals/compare", ctx,
                                   json={"hospital_ids": hospital_ids, "procedure_code": procedure_code})

    async def get_my_reservations(self, ctx, status):
        # 「MCP 설계」는 /internal/reservations?userId= 로 적혀 있으나 「공통 계약서」 8장 /internal/reservations/mine 을 따른다.
        # acting user 는 X-Acting-User-Id 헤더로 backend 가 판단.
        # TODO(mcp): backend BE-13 구현 후 경로 재확인 (현재 feat/be-bootstrap 에는 조회 7종만 있음)
        return await self._request("GET", "/reservations/mine", ctx, params={"status": status})

    async def plan_trip(self, ctx, body):
        # TODO(mcp): backend BE-14 (POST /internal/trip-plans) 구현 후 연결 확인
        return await self._request("POST", "/trip-plans", ctx, json=body)

    # --- 변경 (agent 승인 interrupt 를 거친 뒤에만 호출됨) --------------------
    async def create_reservation(self, ctx, body, idempotency_key):
        # TODO(mcp): backend BE-10/13 구현 후 409 SLOT_UNAVAILABLE details.alternatives 형식 확인
        return await self._request("POST", "/reservations", ctx, json=body, idempotency_key=idempotency_key)

    async def cancel_reservation(self, ctx, reservation_id, reason):
        return await self._request("POST", f"/reservations/{reservation_id}/cancel", ctx, json={"reason": reason})

    async def request_consultation(self, ctx, body, idempotency_key):
        # TODO(mcp): backend BE-16 구현 후 확인. consent=false 면 409 CONSENT_REQUIRED
        return await self._request("POST", "/consultations", ctx, json=body, idempotency_key=idempotency_key)


def build_client() -> BackendClient:
    if settings.use_stub:
        from business_mcp.stub_backend import StubBackendClient

        return StubBackendClient()
    return HttpBackendClient()
