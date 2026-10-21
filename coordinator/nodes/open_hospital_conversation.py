"""Validate selection and retain an unsent handoff until MCP creation is available."""
from app.graph.state import AgentState
from coordinator.nodes.coordinator_tools import prepare_handoff_summary


def open_hospital_conversation(state: AgentState) -> dict:
    action = state.get("action") or {}
    hospital_id = action.get("hospitalId") if action.get("type") == "SELECT_HOSPITAL" else state.get("selected_hospital_id")
    prepared = prepare_handoff_summary(state, hospital_id, state.get("candidates") or [],
                                       state.get("conditions") or {})
    if prepared["status"] != "summary_ready":
        locale = (state.get("user") or {}).get("locale", "en")
        messages = {"en": "Please select a hospital from the current results.",
                    "ko": "현재 검색 결과에서 병원을 선택해 주세요.",
                    "zh": "请从当前搜索结果中选择医院。", "ja": "現在の検索結果から病院を選択してください。"}
        return {"draft": messages.get(locale, messages["en"]), "summary": None, "selected_hospital_id": None}
    # shortcut: creation MCP is not contracted yet, connect after the MCP owner adds it.
    return {"draft": prepared["summary"], "summary": prepared["summary"],
            "selected_hospital_id": hospital_id}
