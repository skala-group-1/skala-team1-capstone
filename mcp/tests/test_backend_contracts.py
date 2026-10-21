"""Exercise the MCP boundary with backend-shaped HTTP responses, without DB writes."""
import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from business_mcp import server
from business_mcp.backend_client import HttpBackendClient
from business_mcp.context import CallContext


@pytest.fixture
async def backend_response(monkeypatch):
    response = {}

    def handle(request):
        assert request.headers["X-Acting-User-Id"] == "3"
        assert request.headers["X-Service-Token"] == "test-token"
        assert request.headers["X-Trace-Id"] == "test-trace"
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
