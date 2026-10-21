"""탐색 그래프가 요청한 MCP 조회 도구 실행."""

from langgraph.prebuilt import ToolNode

from app.graph.state import AgentState
from app.mcp_client.tools import PLANNER_TOOLS


async def planner_tools(state: AgentState) -> dict:
    from app.mcp_client.client import get_tools  # MCP 연결은 실제 도구 호출 시점에만 (lazy)

    tools = await get_tools(PLANNER_TOOLS)
    # TODO(agent): harness.tools 래퍼 및 loop.tool_counts 갱신
    return await ToolNode(tools, handle_tool_errors=True).ainvoke(state)
