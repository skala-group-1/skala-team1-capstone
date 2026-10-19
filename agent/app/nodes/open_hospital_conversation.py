"""open_hospital_conversation — 병원 선택 시 새 대화창(새 thread_id) 생성

- 입력 → 출력: selected_hospital_id, conditions, summary → SSE CONVERSATION_OPENED {conversationId, hospitalId}
- LLM/도구: backend POST /internal/conversations (세션 생성이라 승인 불필요)
- 프롬프트: 없음 (요약이 필요하면 summarize_handoff.md 재사용 검토)
- 근거: 「AI Agent 설계」 1장, D-20
"""

from app.graph.state import AgentState


def open_hospital_conversation(state: AgentState) -> dict:
    # TODO(agent): hospital_id 결정 (action.hospitalId 또는 "2번 병원" 발화 → candidates[1])
    # TODO(agent): POST /internal/conversations {hospitalId, parentConversationId} 호출
    #   ※ 「공통 계약서」 8장은 business-mcp 가 호출한다고 적혀 있지만 「MCP 설계」 도구 12개에 해당 도구가 없음 → MCP 도구 추가 or agent 직접 호출 결정 필요
    # TODO(agent): 새 thread 초기 state = conditions + summary + parent_conversation_id, mode=HOSPITAL 로 저장
    # TODO(agent): SSE CONVERSATION_OPENED 이벤트 발행 (workers/events.py)
    return {"draft": f"[open_hospital_conversation 골격] hospital={state.get('selected_hospital_id')}"}
