"""stub 모드에서 대표 도구 정상 1건 + 오류 1건.

TODO(mcp): 도구별 오류 케이스(404·409·403) 를 모두 채우기 (「MCP 설계」 4장: 각 도구 정상 1 + 오류 1 이상)
TODO(mcp): HttpBackendClient 테스트 — httpx.MockTransport 로 backend 응답(camelCase·오류 형식)을 흉내
"""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from business_mcp.server import mcp as business
from rag_mcp.server import mcp as rag


async def call(server, name, args):
    async with Client(server) as c:
        return (await c.call_tool(name, args)).structured_content


async def test_normalize_procedure():
    out = await call(business, "normalize_procedure", {"text": "double eyelid"})
    assert out["candidates"], out
    assert out["candidates"][0]["code"].startswith("DOUBLE_EYELID")


async def test_search_hospitals_filters_area():
    out = await call(business, "search_hospitals", {
        "procedure_code": "JAW_BOTOX", "date_from": "2026-10-20", "areas": ["GANGNAM"], "limit": 5})
    assert out["hospitals"] and all(h["area_code"] == "GANGNAM" for h in out["hospitals"])


async def test_unknown_procedure_is_tool_error():
    with pytest.raises(ToolError, match="normalize_procedure"):
        await call(business, "search_hospitals", {"procedure_code": "EYE_JOB", "date_from": "2026-10-20"})


async def test_hospital_not_found():
    with pytest.raises(ToolError, match="not found"):
        await call(business, "get_hospital_detail", {"hospital_id": 999})


async def test_reservation_idempotent():
    async with Client(business) as c:
        slots = (await c.call_tool("get_available_slots", {
            "hospital_id": 1, "procedure_code": "JAW_BOTOX", "date_from": "2026-10-21", "date_to": "2026-10-21"}
        )).structured_content["slots"]
        args = {"hospital_id": 1, "slot_id": slots[0]["id"], "procedure_code": "JAW_BOTOX", "idempotency_key": "k-1"}
        first = (await c.call_tool("create_reservation_request", args)).structured_content
        second = (await c.call_tool("create_reservation_request", args)).structured_content
    assert first["status"] == "PENDING" and first["id"] == second["id"]


async def test_plan_trip_infeasible_for_long_downtime():
    out = await call(business, "plan_trip", {
        "procedure_code": "DOUBLE_EYELID_INCISION", "hospital_ids": [1],
        "arrival_date": "2026-10-20", "departure_date": "2026-10-23"})
    assert out["plans"][0]["feasible"] is False


async def test_rag_search_and_resource():
    out = await call(rag, "search_procedure_docs", {"query": "jaw botox how it works", "procedure_code": "JAW_BOTOX"})
    assert out["chunks"] and out["chunks"][0]["uri"].startswith("doc://GUIDE_JAW_BOTOX#")
    async with Client(rag) as c:
        text = (await c.read_resource("doc://GUIDE_JAW_BOTOX"))[0].text
    assert "doc_id: GUIDE_JAW_BOTOX" in text


async def test_rag_no_result_message():
    out = await call(rag, "search_procedure_docs", {"query": "zzzz qqqq"})
    assert out["chunks"] == [] and "No grounded document" in out["message"]
