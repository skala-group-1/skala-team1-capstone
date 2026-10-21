"""Exercise the MCP boundary with backend-shaped HTTP responses, without DB writes."""
import json

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from business_mcp import server
from business_mcp.backend_client import HttpBackendClient
from business_mcp.context import CallContext
from mcp_common.casing import keys_to_snake


@pytest.fixture
async def backend_response(monkeypatch):
    response = {"requests": []}

    def handle(request):
        response["requests"].append(request)
        assert request.headers["X-Acting-User-Id"] == "3"
        assert request.headers["X-Service-Token"] == "test-token"
        assert request.headers["X-Trace-Id"] == "test-trace"
        if response.get("timeout"):
            raise httpx.ReadTimeout("test timeout", request=request)
        return httpx.Response(response["status"], json=response["body"])

    backend = HttpBackendClient("http://backend/internal", "test-token")
    await backend._client.aclose()
    backend._client = httpx.AsyncClient(base_url="http://backend/internal",
                                       transport=httpx.MockTransport(handle))
    monkeypatch.setattr(server, "backend", backend)
    monkeypatch.setattr(server, "current_context", lambda: CallContext(3, "test-trace", "zh"))
    try:
        yield response
    finally:
        await backend._client.aclose()


async def test_trip_plan_preserves_procedure_not_offered(backend_response):
    backend_response.update(status=200, body={"plans": [{
        "hospitalId": 1, "hospitalName": "Demo clinic", "slot": None,
        "procedureCode": "NOSE_FILLER", "downtimeDays": 1, "recoveryEndDate": None,
        "bufferDays": None, "feasible": False, "reason": "PROCEDURE_NOT_OFFERED",
    }]})
    async with Client(server.mcp) as client:
        result = await client.call_tool("plan_trip", {
            "hospital_ids": [1], "procedure_code": "NOSE_FILLER",
            "arrival_date": "2026-10-22", "departure_date": "2026-10-28",
        })
    plan = result.structured_content["plans"][0]
    assert plan["reason"] == "PROCEDURE_NOT_OFFERED"
    assert plan["feasible"] is False and plan["slot"] is None


async def test_slot_conflict_preserves_backend_alternative(backend_response):
    backend_response.update(status=409, body={
        "code": "SLOT_UNAVAILABLE", "message": "Slot unavailable", "traceId": "test-trace",
        "details": {"alternatives": [{"id": 8813, "startAt": "2026-10-22T15:30:00+09:00",
                                     "endAt": "2026-10-22T16:00:00+09:00", "status": "AVAILABLE"}]},
    })
    async with Client(server.mcp) as client:
        with pytest.raises(ToolError, match=r"8813 \(2026-10-22T15:30:00\+09:00\)"):
            await client.call_tool("create_reservation_request", {
                "hospital_id": 1, "slot_id": 8812, "procedure_code": "JAW_BOTOX",
                "idempotency_key": "test-no-write",
            })


@pytest.mark.parametrize("procedure,expected", [
    ({"procedure": {"code": "DOUBLE_EYELID_NONINCISION", "name": "Non-incisional double eyelid"}},
     "DOUBLE_EYELID_NONINCISION"),
    ({"procedureCode": "JAW_BOTOX"}, "JAW_BOTOX"),
    ({"procedure": {"name": "Unknown procedure"}}, None),
    ({"procedure": None}, None),
    ({}, None),
])
async def test_reservation_preserves_backend_procedure_code_without_guessing(backend_response, procedure, expected):
    backend_response.update(status=200, body=[{
        "id": 23, "status": "PENDING", "source": "AI",
        "hospital": {"id": 41, "name": "Demo clinic"},
        "slot": {"id": 11432, "startAt": "2026-10-22T10:30:00+09:00",
                 "endAt": "2026-10-22T11:00:00+09:00", "status": "HELD"},
        "createdAt": "2026-10-21T12:00:00+09:00", **procedure,
    }])
    async with Client(server.mcp) as client:
        result = await client.call_tool("get_my_reservations", {})
    reservation, = result.structured_content["reservations"]
    assert reservation["procedure_code"] == expected
    assert "procedure" not in reservation
    assert reservation["hospital"]["id"] == 41
    assert reservation["slot"]["start_at"] == "2026-10-22T10:30:00+09:00"
    request, = backend_response["requests"]
    assert request.method == "GET" and request.url.path == "/internal/reservations/mine"


PARENT_ID = "98b7eac5-0577-43c8-8601-4dfad34e6804"
OPEN_ARGS = {"hospital_id": 1, "parent_conversation_id": PARENT_ID}


@pytest.mark.parametrize("mode,status", [("HOSPITAL", 201), ("HUMAN", 200)])
async def test_open_conversation_preserves_backend_dto_and_request(backend_response, mode, status):
    body = {
        "id": "5b4c6ed6-0b77-4d10-823c-c745dd9143b8", "mode": mode,
        "hospital": {"id": 1, "name": "Demo clinic"}, "parentConversationId": PARENT_ID,
        "consultationId": 42 if mode == "HUMAN" else None,
        "conditions": {"procedureCode": "JAW_BOTOX", "budgetMaxKrw": 300000,
                       "dateFrom": "2026-10-22", "consultLanguage": "zh"},
        "createdAt": "2026-10-22T09:00:00+09:00",
        "messages": [{"role": "assistant", "text": "Existing response",
                      "sources": [{"docId": "HOSPITAL_1"}], "cards": {"hospitalId": 1},
                      "createdAt": "2026-10-22T09:01:00+09:00"}] if mode == "HUMAN" else None,
    }
    backend_response.update(status=status, body=body)
    async with Client(server.mcp) as client:
        result = await client.call_tool("open_hospital_conversation", OPEN_ARGS)
    assert result.structured_content == keys_to_snake(body)
    request, = backend_response["requests"]
    assert request.method == "POST" and request.url.path == "/internal/conversations"
    assert dict(request.url.params) == {"locale": "zh"}
    assert json.loads(request.content) == {"hospitalId": 1, "parentConversationId": PARENT_ID}
    assert "Idempotency-Key" not in request.headers


@pytest.mark.parametrize("status,code,message,attempts", [
    (401, "UNAUTHENTICATED", "UNAUTHENTICATED", 1),
    (403, "ACCESS_DENIED", "Do not retry", 1),
    (404, "NOT_FOUND", "not found", 1),
    (500, "INTERNAL_ERROR", "Temporary backend error", 2),
])
async def test_open_conversation_backend_errors(backend_response, status, code, message, attempts):
    backend_response.update(status=status, body={
        "code": code, "message": "Request failed", "traceId": "test-trace",
        "details": {"resource": "conversation"},
    })
    async with Client(server.mcp) as client:
        with pytest.raises(ToolError, match=message):
            await client.call_tool("open_hospital_conversation", OPEN_ARGS)
    assert len(backend_response["requests"]) == attempts


async def test_open_conversation_timeout_retries_once(backend_response):
    backend_response["timeout"] = True
    async with Client(server.mcp) as client:
        with pytest.raises(ToolError, match="Temporary backend error"):
            await client.call_tool("open_hospital_conversation", OPEN_ARGS)
    assert len(backend_response["requests"]) == 2


@pytest.mark.parametrize("args", [
    {}, {"hospital_id": 1}, {"parent_conversation_id": PARENT_ID},
    {**OPEN_ARGS, "hospital_id": 0}, {**OPEN_ARGS, "hospital_id": -1},
    {**OPEN_ARGS, "hospital_id": True}, {**OPEN_ARGS, "hospital_id": 1.5},
    {**OPEN_ARGS, "parent_conversation_id": "not-a-uuid"},
])
async def test_open_conversation_invalid_input_never_calls_backend(backend_response, args):
    async with Client(server.mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("open_hospital_conversation", args)
    assert backend_response["requests"] == []
