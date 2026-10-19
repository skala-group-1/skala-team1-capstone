"""verify (Critic) — 초안의 가격·날짜·병원·슬롯을 tool_ledger 와 대조

- 입력 → 출력: draft, tool_ledger → verify_passed, verify_attempts(+1), (불일치 시) 피드백 메시지
- LLM/도구: LLM_FAST_MODEL structured output 으로 사실 주장 추출 → 코드로 ledger 대조
- 프롬프트: (추가 필요) prompts/verify.md — 03 문서 8장 목록에는 없음
- 근거: 03 문서 9-3, D-24, 05 문서 Guardrails
"""

from app.graph.state import AgentState


def verify(state: AgentState) -> dict:
    # TODO(agent): 초안에서 금액·날짜/시각·병원명·회복일 추출 → tool_ledger 와 비교
    # TODO(agent): 불일치면 verify_passed=False + 어떤 값이 틀렸는지 SystemMessage 피드백 추가
    # TODO(agent): 재시도 후에도 불일치면 해당 값만 "확인 필요"로 치환 + audit VERIFY_FAILED
    # TODO(agent): SSE VERIFY {passed, attempts} 발행
    passed = True
    attempts = state.get("verify_attempts", 0) + (0 if passed else 1)
    return {"verify_passed": passed, "verify_attempts": attempts}
