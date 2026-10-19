"""guard_reply — 추천·의료판단·보장·범위밖·주입 요청에 대한 안전 응답 + 대안 제시

- 입력 → 출력: guard_flags → draft (안전 응답)
- LLM/도구: 규칙 + (선택) LLM, MEDICAL_JUDGMENT 는 rag_search_procedure_docs 로 일반 정보만
- 프롬프트: prompts/system_base.md
- 근거: 03 문서 7장 가드레일 표, D-01 (추천 금지 → 정렬 기준 선택 버튼)
"""

from app.graph.state import AgentState


def guard_reply(state: AgentState) -> dict:
    # TODO(agent): 플래그별 응답 (RECOMMEND_REQUEST → 정렬 기준 버튼, MEDICAL_JUDGMENT → 일반 정보 + 상담사 연결 버튼 ...)
    # TODO(agent): 사용자 locale 로 답변
    flags = ", ".join(state.get("guard_flags") or [])
    return {"draft": f"[guard_reply 골격] flags={flags}"}
