"""MCP 클라이언트 — business-mcp·rag-mcp 를 하나의 MultiServerMCPClient 로 묶는다 (「MCP 설계」 1장).

D-31: 가짜 도구를 agent 안에 따로 만들지 않는다.
- USE_FAKE_TOOLS=true  → 두 MCP 서버를 stdio 로 직접 띄우고 USE_STUB=true (mock JSON 응답).
                          agent 는 처음부터 진짜 MCP 경로(도구 이름·스키마)로 개발된다.
- USE_FAKE_TOOLS=false → compose 의 streamable HTTP 서버 (BUSINESS_MCP_URL, RAG_MCP_URL).
서버 이름 "business"/"rag" + tool_name_prefix=True → 도구명 business_search_hospitals, rag_search_procedure_docs ...
"""

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import get_settings

_client: MultiServerMCPClient | None = None
_tools: list[BaseTool] | None = None


def _connections() -> dict:
    s = get_settings()
    if s.use_fake_tools:
        def stdio(module: str) -> dict:
            return {
                "transport": "stdio",
                "command": "uv",
                "args": ["run", "--project", str(s.mcp_project_dir), "python", "-m", module],
                "env": {"MCP_TRANSPORT": "stdio", "USE_STUB": "true"},
                "cwd": str(s.mcp_project_dir),
            }
        return {"business": stdio("business_mcp.server"), "rag": stdio("rag_mcp.server")}
    return {
        "business": {"transport": "streamable_http", "url": s.business_mcp_url},
        "rag": {"transport": "streamable_http", "url": s.rag_mcp_url},
    }


def get_client() -> MultiServerMCPClient:
    # TODO(agent): tool_interceptors 로 x-acting-user-id·x-trace-id 헤더 주입 (「MCP 설계」 1장: LLM 인자에 노출 금지)
    global _client
    if _client is None:
        _client = MultiServerMCPClient(_connections(), tool_name_prefix=True)
    return _client


async def get_tools(allowed: tuple[str, ...] | None = None) -> list[BaseTool]:
    """도구 목록을 처음 한 번만 불러와 캐시. allowed 가 있으면 그 이름만."""
    global _tools
    if _tools is None:
        _tools = await get_client().get_tools()
        # TODO(agent): 시작 시 기대 도구(PLANNER_TOOLS·HOSPITAL_READ_TOOLS·DESTRUCTIVE_TOOLS)가 모두 있는지 검사하고 없으면 경고
    if allowed is None:
        return _tools
    return [t for t in _tools if t.name in allowed]
