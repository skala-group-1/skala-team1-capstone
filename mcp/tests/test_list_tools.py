"""list_tools 스냅샷: 도구 이름·description·힌트 누락 방지 (「MCP 설계」 4장).

도구를 추가·삭제하면 아래 목록도 고치고 agent 담당에게 공유한다 (「파트별 착수 가이드」 3장).
"""

from fastmcp import Client

from business_mcp.server import mcp as business
from rag_mcp.server import mcp as rag

BUSINESS_READ = {
    "normalize_procedure", "search_hospitals", "get_hospital_detail", "list_doctors", "get_price_options",
    "get_available_slots", "compare_hospitals", "get_my_reservations", "plan_trip", "get_hospital_reviews",
}
BUSINESS_WRITE = {"create_reservation_request", "cancel_reservation", "request_consultation"}
BUSINESS_NAVIGATION = {"open_hospital_conversation"}
RAG_TOOLS = {"search_procedure_docs", "search_hospital_docs"}


async def test_business_tools_snapshot():
    async with Client(business) as c:
        tools = {t.name: t for t in await c.list_tools()}
    assert set(tools) == BUSINESS_READ | BUSINESS_WRITE | BUSINESS_NAVIGATION
    assert len(tools) == 14
    for name, tool in tools.items():
        assert tool.description and len(tool.description) > 40, f"{name}: description 부족"
        assert tool.annotations is not None, f"{name}: annotations 없음"
        assert tool.output_schema, f"{name}: Pydantic 반환(outputSchema) 없음"
        if name in BUSINESS_READ:
            assert tool.annotations.read_only_hint is True, name
        elif name in BUSINESS_WRITE:
            assert tool.annotations.destructive_hint is True, name
            assert tool.annotations.idempotent_hint is True, name
        else:
            assert tool.annotations.read_only_hint is False
            assert tool.annotations.destructive_hint is False
            assert tool.annotations.idempotent_hint is True
            assert tool.annotations.open_world_hint is False
    schema = tools["open_hospital_conversation"].input_schema
    assert set(schema["properties"]) == set(schema["required"]) == {
        "hospital_id", "parent_conversation_id",
    }
    assert schema["properties"]["hospital_id"]["exclusiveMinimum"] == 0
    assert schema["properties"]["parent_conversation_id"]["format"] == "uuid"
    assert set(tools["open_hospital_conversation"].output_schema["properties"]) == {
        "id", "mode", "hospital", "parent_conversation_id", "consultation_id",
        "conditions", "created_at", "messages",
    }


async def test_rag_tools_and_resources():
    async with Client(rag) as c:
        tools = {t.name: t for t in await c.list_tools()}
        templates = {t.uri_template for t in await c.list_resource_templates()}
    assert set(tools) == RAG_TOOLS
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert templates == {"doc://{doc_id}", "doc://{doc_id}/sections/{section}"}
