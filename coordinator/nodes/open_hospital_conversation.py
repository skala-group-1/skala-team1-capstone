"""Open a selected hospital through the contracted MCP tool; parent stays MAIN."""
import asyncio
from uuid import UUID

from app.graph.state import AgentState
from coordinator.nodes.coordinator_tools import decode_result, load_business_tools, summarizer_handoff_summary


async def run_open_hospital_conversation(state: AgentState, *, business_loader=None) -> dict:
    action = state.get("action") or {}
    hospital_id = action.get("hospitalId") if action.get("type") == "SELECT_HOSPITAL" else None
    prepared = await summarizer_handoff_summary(state, hospital_id, state.get("candidates") or [],
                                                state.get("conditions") or {})
    locale = (state.get("user") or {}).get("locale", "en")
    if prepared["status"] != "summary_ready":
        messages = {"en": "Please select a hospital from the current results.",
                    "ko": "현재 검색 결과에서 병원을 선택해 주세요.",
                    "zh": "请从当前搜索结果中选择医院。", "ja": "現在の検索結果から病院を選択してください。"}
        return {"draft": messages.get(locale, messages["en"]), "summary": None,
                "selected_hospital_id": None, "opened_conversation": None}
    update = {"summary": prepared["summary"], "selected_hospital_id": hospital_id, "opened_conversation": None}
    try:
        parent_id = str(UUID(state["conversation_id"]))
        tools = await (business_loader or load_business_tools)()
        target = next(t for t in tools if t.name == "business_open_hospital_conversation")
        result = decode_result(await asyncio.wait_for(target.ainvoke({
            "hospital_id": hospital_id, "parent_conversation_id": parent_id}), 20))
        conversation_id = str(UUID(result["id"]))
        returned_hospital = result.get("hospital") or {}
        if (conversation_id == parent_id or type(returned_hospital.get("id")) is not int
                or returned_hospital["id"] != hospital_id or result.get("mode") not in ("HOSPITAL", "HUMAN")
                or (result.get("conditions") is not None and not isinstance(result["conditions"], dict))):
            raise ValueError("Invalid hospital conversation")
        update["opened_conversation"] = {
            "conversation_id": conversation_id, "hospital_id": hospital_id, "mode": result["mode"],
            "parent_conversation_id": result.get("parent_conversation_id"),
            "consultation_id": result.get("consultation_id"), "conditions": result["conditions"],
        }
    except Exception:
        messages = {"en": "Unable to open the hospital conversation. Please try again later.",
                    "ko": "병원 대화를 열지 못했습니다. 잠시 후 다시 시도해 주세요.",
                    "zh": "暂时无法打开医院对话，请稍后重试。", "ja": "病院との会話を開けませんでした。後ほど再度お試しください。"}
        return {**update, "draft": messages.get(locale, messages["en"])}
    messages = {"en": "Hospital conversation opened.", "ko": "병원 대화를 열었습니다.",
                "zh": "已打开医院对话。", "ja": "病院との会話を開きました。"}
    return {**update, "draft": messages.get(locale, messages["en"])}


async def open_hospital_conversation(state: AgentState) -> dict:
    """Keep MCP calls on the worker's event loop."""
    return await run_open_hospital_conversation(state)
