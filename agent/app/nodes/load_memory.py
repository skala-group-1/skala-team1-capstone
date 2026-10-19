"""load_memory — 장기 프로필 → state.profile

- 입력 → 출력: user.user_id → profile
- LLM/도구: 없음. LangGraph store (PostgresStore, namespace ("user", user_id), key "profile")
- 프롬프트: 없음
- 근거: 「AI Agent 설계」 9-4 장기 기억, D-25
"""

from langgraph.config import get_store

from app.graph.state import AgentState
from app.harness.memory import PROFILE_KEY, PROFILE_NAMESPACE


def load_memory(state: AgentState) -> dict:
    user_id = (state.get("user") or {}).get("user_id")
    if user_id is None:
        return {"profile": None}
    # TODO(agent): 저장 동의(SAVE_PROFILE)한 사용자만 값이 있음. 민감 필드(skinConcerns)는 로그 마스킹
    item = get_store().get((PROFILE_NAMESPACE, str(user_id)), PROFILE_KEY)
    return {"profile": item.value if item else None}
