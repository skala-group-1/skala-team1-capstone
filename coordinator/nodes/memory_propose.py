"""memory_propose — 저장할 만한 안정적 선호 감지 → MEMORY_PROPOSAL 제안 (저장은 동의 후)

- 입력 → 출력: conditions, messages, profile → memory_proposal
- LLM/도구: 규칙 또는 LLM_FAST_MODEL
- 근거: 「AI Agent 설계」 9-4, D-25 (동의 후 저장. 저장은 action SAVE_PROFILE 작업에서)
"""

from app.graph.state import AgentState


def memory_propose(state: AgentState) -> dict:
    # TODO(agent): conditions 의 areas·budget·procedure 가 profile 과 다르면 AiProfile 형태로 제안 (「공통 계약서」 AiProfile)
    # TODO(agent): SSE MEMORY_PROPOSAL 발행. 사용자가 거절하면 저장하지 않음 (테스트: 거절 시 미저장)
    return {"memory_proposal": None}
