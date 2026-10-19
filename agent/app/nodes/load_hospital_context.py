"""load_hospital_context — 병원 요약·조건을 system 에 주입

- 입력 → 출력: selected_hospital_id, conditions, summary → (system 컨텍스트)
- LLM/도구: business_get_hospital_detail (lite)
- 근거: 「AI Agent 설계」 4장, D-20 (새 대화창 초기 state 에 conditions·summary 복사)
"""

from app.graph.state import AgentState


def load_hospital_context(state: AgentState) -> dict:
    # TODO(agent): 병원 상세(lite) 조회 → system 메시지 또는 state 필드로 주입 (매 턴 반복 조회 피하기)
    # TODO(agent): conditions·summary·parent_conversation_id 는 open_hospital_conversation 이 넣어둔 값 사용
    return {}
