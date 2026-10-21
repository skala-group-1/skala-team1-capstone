"""guard_input — 의도 분류 + 가드레일

- 입력 → 출력: 마지막 사용자 메시지 → intent, guard_flags
- LLM/도구: LLM_FAST_MODEL structured output
- 프롬프트: prompts/guard_input.md
- 근거: 「AI Agent 설계」 5장 노드 명세, 7장 가드레일 표, 「공통 계약서」 Intent·GuardFlag enum
"""

from app.graph.state import AgentState


def guard_input(state: AgentState) -> dict:
    action = state.get("action") or {}
    if action.get("type") == "SELECT_HOSPITAL":
        return {"intent": "SELECT", "guard_flags": [],
                "selected_hospital_id": action.get("hospitalId")}
    # A previous SELECT must not route a later ordinary message back to selection.
    return {"intent": "SEARCH", "guard_flags": state.get("guard_flags") or []}
