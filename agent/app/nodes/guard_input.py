"""guard_input — 의도 분류 + 가드레일

- 입력 → 출력: 마지막 사용자 메시지 → intent, guard_flags
- LLM/도구: LLM_FAST_MODEL structured output
- 프롬프트: prompts/guard_input.md
- 근거: 03 문서 5장 노드 명세, 7장 가드레일 표, 12 문서 Intent·GuardFlag enum
"""

from app.graph.state import AgentState


def guard_input(state: AgentState) -> dict:
    # TODO(agent): LLM structured output 으로 {intent, guard_flags} 분류 (저비용 모델)
    # TODO(agent): INJECTION 감지 시 감사 로그 (05 문서 Guardrails)
    # TODO(agent): 카드 버튼 action(SELECT_HOSPITAL 등)이 들어오면 LLM 없이 intent 결정 (12 문서 CreateTaskRequest.action)
    # 골격: 이미 state 에 값이 있으면 유지(테스트·CLI 용), 없으면 SEARCH
    return {
        "intent": state.get("intent") or "SEARCH",
        "guard_flags": state.get("guard_flags") or [],
    }
