"""ask_clarify — 누락 조건 역질문 (여러 항목이면 한 번에 묶어서)

- 입력 → 출력: missing → draft (역질문 1개)
- LLM/도구: LLM
- 프롬프트: prompts/ask_clarify.md
- 근거: 03 문서 3장 (반복: 다음 사용자 메시지가 같은 thread 로 들어와 extract_conditions 로 재진입)
"""

from app.graph.state import AgentState


def ask_clarify(state: AgentState) -> dict:
    # TODO(agent): 사용자 locale 로 자연스러운 역질문 생성. 예산·상담언어는 "상관없음" 선택지
    return {"draft": f"[ask_clarify 골격] missing={state.get('missing')}"}
