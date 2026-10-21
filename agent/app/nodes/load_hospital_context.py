"""Conversation-scoped hospital facts. Availability is deliberately never cached."""

import json

from langchain_core.messages import ToolMessage

from app.graph.state import AgentState
from app.mcp_client.client import get_tools


def tool_data(result):
    """Decode MCP adapter structured artifacts or JSON text without inventing facts."""
    if isinstance(result, ToolMessage):
        if result.status == "error":
            raise ValueError("Hospital context lookup failed")
        artifact = result.artifact
        if isinstance(artifact, dict) and isinstance(artifact.get("structured_content"), dict):
            return artifact["structured_content"]
        result = result.content
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        return json.loads(result)
    if isinstance(result, list):
        texts = [block["text"] for block in result
                 if isinstance(block, dict) and block.get("type") == "text"]
        if len(texts) == 1:
            return json.loads(texts[0])
    raise ValueError("Expected structured MCP data")


def selected_hospital(state: AgentState) -> int:
    hospital_id = state.get("selected_hospital_id")
    if type(hospital_id) is not int or hospital_id <= 0:
        raise ValueError("A selected hospital is required")
    return hospital_id


async def load_hospital_context(state: AgentState) -> dict:
    hospital_id = selected_hospital(state)
    previous = state.get("hospital_context") or {}
    context = dict(previous) if previous.get("hospital_id") == hospital_id else {"hospital_id": hospital_id}
    prices = dict(context.get("prices") or {})
    booking = state.get("hospital_booking") or {}
    if previous and previous.get("hospital_id") != hospital_id:
        booking = {}
    procedure = booking.get("procedure_code") or (state.get("conditions") or {}).get("procedure_code")
    requests = []
    if "detail" not in context:
        requests.append(("detail", "business_get_hospital_detail", {"hospital_id": hospital_id}))
    if "doctors" not in context:
        requests.append(("doctors", "business_list_doctors", {"hospital_id": hospital_id}))
    if procedure and procedure not in prices:
        requests.append(("prices", "business_get_price_options", {"hospital_id": hospital_id, "procedure_code": procedure}))
    if requests:
        tools = {tool.name: tool for tool in await get_tools(tuple(name for _, name, _ in requests))}
        for key, name, args in requests:
            if name not in tools:
                raise ValueError(f"Required MCP tool unavailable: {name}")
            data = tool_data(await tools[name].ainvoke(args))
            if key == "detail" and data.get("id") != hospital_id:
                raise ValueError("Hospital context does not match the selected hospital")
            if key == "prices":
                prices[procedure] = data
            else:
                context[key] = data
    context["prices"] = prices
    update = {"hospital_context": context}
    if previous and previous.get("hospital_id") != hospital_id:
        update["hospital_booking"] = {}
    return update
