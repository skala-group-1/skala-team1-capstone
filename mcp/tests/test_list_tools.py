"""list_tools 스냅샷: 도구 이름·description·힌트 누락 방지 (04 문서 4장).

도구를 추가·삭제하면 아래 목록도 고치고 agent 담당에게 공유한다 (13 문서 3장).
"""

from fastmcp import Client

from business_mcp.server import mcp as business
from rag_mcp.server import mcp as rag

BUSINESS_READ = {
    "normalize_procedure", "search_hospitals", "get_hospital_detail", "list_doctors", "get_price_options",
    "get_available_slots", "compare_hospitals", "get_my_reservations", "plan_trip",
}
BUSINESS_WRITE = {"create_reservation_request", "cancel_reservation", "request_consultation"}
RAG_TOOLS = {"search_procedure_docs", "search_hospital_docs"}


async def test_business_tools_snapshot():
    async with Client(business) as c:
        tools = {t.name: t for t in await c.list_tools()}
    assert set(tools) == BUSINESS_READ | BUSINESS_WRITE
    for name, tool in tools.items():
        assert tool.description and len(tool.description) > 40, f"{name}: description 부족"
        assert tool.annotations is not None, f"{name}: annotations 없음"
        assert tool.output_schema, f"{name}: Pydantic 반환(outputSchema) 없음"
        if name in BUSINESS_READ:
            assert tool.annotations.read_only_hint is True, name
        else:
            assert tool.annotations.destructive_hint is True, name
            assert tool.annotations.idempotent_hint is True, name


async def test_rag_tools_and_resources():
    async with Client(rag) as c:
        tools = {t.name: t for t in await c.list_tools()}
        templates = {t.uri_template for t in await c.list_resource_templates()}
    assert set(tools) == RAG_TOOLS
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert templates == {"doc://{doc_id}", "doc://{doc_id}/sections/{section}"}
