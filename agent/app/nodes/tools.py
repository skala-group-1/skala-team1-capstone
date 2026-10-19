"""tools — planner_agent / hospital_agent 가 요청한 MCP 도구 실행

- 입력 → 출력: 마지막 AIMessage.tool_calls → ToolMessage 들
- LLM/도구: business-mcp / rag-mcp (mcp_client.client.get_tools)
- 근거: 「Harness 명세」 Tools (절단·ToolError→ToolMessage·hospital_id 주입·tool_ledger)
"""

from langgraph.prebuilt import ToolNode

from app.graph.state import AgentState
from app.mcp_client.tools import HOSPITAL_READ_TOOLS, PLANNER_TOOLS


async def _run(state: AgentState, allowed: tuple[str, ...]) -> dict:
    from app.mcp_client.client import get_tools  # MCP 연결은 실제 도구 호출 시점에만 (lazy)

    tools = await get_tools(allowed)
    # TODO(agent): harness.tools 래퍼 적용 (4,000자 절단, ToolError → status=error, tool_ledger 기록)
    # TODO(agent): loop.tool_counts 갱신 (같은 인자 3회 차단용)
    return await ToolNode(tools, handle_tool_errors=True).ainvoke(state)


async def planner_tools(state: AgentState) -> dict:
    return await _run(state, PLANNER_TOOLS)


async def hospital_tools(state: AgentState) -> dict:
    # TODO(agent): 실행 전에 tool_calls args 의 hospital_id 를 state.selected_hospital_id 로 덮어쓰기 (「AI Agent 설계」 4장)
    return await _run(state, HOSPITAL_READ_TOOLS)
