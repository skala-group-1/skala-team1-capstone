"""tools — hospital_agent 가 요청한 MCP 도구 실행

- 입력 → 출력: 마지막 AIMessage.tool_calls → ToolMessage 들
- LLM/도구: business-mcp / rag-mcp (mcp_client.client.get_tools)
- 근거: 「Harness 명세」 Tools (절단·ToolError→ToolMessage·hospital_id 주입·tool_ledger)
"""

from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, ToolMessage

from app.graph.state import AgentState
from app.mcp_client.tools import HOSPITAL_READ_TOOLS
from concierge.nodes.load_hospital_context import selected_hospital, tool_data


async def hospital_tools(state: AgentState) -> dict:
    from app.mcp_client.client import get_tools  # MCP 연결은 실제 도구 호출 시점에만 (lazy)

    tools = await get_tools(HOSPITAL_READ_TOOLS)
    hospital_id = selected_hospital(state)
    last = state["messages"][-1]
    if not isinstance(last, AIMessage):
        raise ValueError("Expected hospital tool calls")
    by_name = {tool.name: tool for tool in tools}
    calls = []
    for call in last.tool_calls:
        tool = by_name.get(call["name"])
        if call["name"].startswith("rag_search_") and (
            tool is None or "hospital_id" not in tool.args
        ):
            raise ValueError("RAG tool does not support hospital-scoped search")
        args = dict(call["args"])
        if tool is not None and "hospital_id" in tool.args:
            args["hospital_id"] = hospital_id
        calls.append({**call, "args": args})
    scoped_last = last.model_copy(update={"tool_calls": calls})
    state = {**state, "messages": [*state["messages"][:-1], scoped_last]}
    # TODO(agent): harness.tools 래퍼 적용 (4,000자 절단, ToolError → status=error, tool_ledger 기록)
    # TODO(agent): loop.tool_counts 갱신 (같은 인자 3회 차단용)
    result = await ToolNode(tools, handle_tool_errors=True).ainvoke(state)
    # Retain the authoritative scoped calls in the checkpoint as well.
    result["messages"] = [scoped_last, *result["messages"]]
    citations = {c["uri"]: c for c in state.get("citations") or []}
    rag_ids = {c["id"] for c in calls if c["name"].startswith("rag_search_")}
    for message in result["messages"]:
        if not isinstance(message, ToolMessage) or message.tool_call_id not in rag_ids or message.status == "error":
            continue
        for chunk in tool_data(message).get("chunks", []):
            if all(isinstance(chunk.get(key), str) for key in ("doc_id", "title", "section", "uri", "text")):
                citations[chunk["uri"]] = {
                    key: chunk[key] for key in ("doc_id", "title", "section", "uri")
                } | {"snippet": chunk["text"]}
    result["citations"] = list(citations.values())
    return result
