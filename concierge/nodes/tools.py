"""tools — hospital_agent 가 요청한 MCP 도구 실행

- 입력 → 출력: 마지막 AIMessage.tool_calls → ToolMessage 들
- LLM/도구: business-mcp / rag-mcp (mcp_client.client.get_tools)
- 근거: 「Harness 명세」 Tools (절단·ToolError→ToolMessage·hospital_id 주입·tool_ledger)
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, ToolMessage

from app.graph.state import AgentState
from app.mcp_client.tools import HOSPITAL_READ_TOOLS
from concierge.nodes.load_hospital_context import selected_hospital, tool_data

REVIEWS_PER_PROCEDURE = 10


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
        if call["name"] == "business_get_hospital_reviews" and args.get("procedure_code"):
            args["size"] = REVIEWS_PER_PROCEDURE  # 시술 필터 조회는 모델이 정한 size 와 무관하게 최신 10개
        calls.append({**call, "args": args})
    scoped_last = last.model_copy(update={"tool_calls": calls})
    state = {**state, "messages": [*state["messages"][:-1], scoped_last]}
    # TODO(agent): harness.tools 래퍼 적용 (4,000자 절단, ToolError → status=error, tool_ledger 기록)
    # TODO(agent): loop.tool_counts 갱신 (같은 인자 3회 차단용)
    result = await ToolNode(tools, handle_tool_errors=True).ainvoke(state)
    slot_calls = {c["id"]: c["args"] for c in calls if c["name"] == "business_get_available_slots"}
    for index, message in enumerate(result["messages"]):
        if not isinstance(message, ToolMessage) or message.status == "error" or message.tool_call_id not in slot_calls:
            continue
        args = slot_calls[message.tool_call_id]
        try:
            start, end = date.fromisoformat(args["date_from"]), date.fromisoformat(args["date_to"])
            data = tool_data(message)
            for slot in data["slots"]:
                instant = datetime.fromisoformat(slot["start_at"])
                finish = datetime.fromisoformat(slot["end_at"])
                if finish.tzinfo is None or finish <= instant:
                    raise ValueError("Unverifiable slot end time")
                if instant.tzinfo is None or not start <= instant.astimezone(ZoneInfo("Asia/Seoul")).date() <= end:
                    raise ValueError("Slot outside the requested dates")
                if args.get("doctor_id") is not None and slot.get("doctor_id") != args["doctor_id"]:
                    raise ValueError("Slot outside the requested doctor")
        except (KeyError, TypeError, ValueError):
            result["messages"][index] = ToolMessage(
                content="Slot lookup returned unverifiable dates or doctor scope. Do not present these slots or claim no availability. Ask to retry the exact requested range.",
                tool_call_id=message.tool_call_id, status="error")
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
