"""respond — 최종 답변을 메시지로 만들고 카드·근거·계획 이벤트 발행

- 입력 → 출력: draft, citations, candidates, trip_plans → AIMessage, draft=None
- LLM/도구: 규칙 + (필요 시) LLM
- 프롬프트: prompts/system_base.md
- 근거: 03 문서 5장, 6장(언어 처리), 12 문서 6장 SSE (DONE {answer, sources})
"""

from langchain_core.messages import AIMessage

from app.graph.state import AgentState


def respond(state: AgentState) -> dict:
    # TODO(agent): 사용자 locale 확인, 금지표현 필터 (harness.guardrails), 근거(citations) 첨부
    # TODO(agent): RESULT_CARDS / TRIP_PLAN / DONE SSE 이벤트 발행 (workers/events.py)
    draft = state.get("draft")
    if not draft:
        return {}
    return {"messages": [AIMessage(content=draft)], "draft": None, "verify_attempts": 0, "verify_passed": None}
