"""extract_conditions — 대화에서 조건 추출·병합 + 시술명 정규화

- 입력 → 출력: messages, conditions, profile → conditions(병합), missing
- LLM/도구: LLM structured output + business_normalize_procedure
- 프롬프트: prompts/extract_conditions.md
- 근거: 「AI Agent 설계」 3장(필수 조건), 9-4(프로필로 빈 조건 미리 채움), 「공통 계약서」 Conditions
"""

from app.graph.state import REQUIRED_CONDITIONS, AgentState


def extract_conditions(state: AgentState) -> dict:
    conditions = dict(state.get("conditions") or {})
    # TODO(agent): LLM 으로 마지막 메시지에서 조건 추출 → 기존 conditions 에 누적 병합
    # TODO(agent): 시술명은 business_normalize_procedure 로 표준 코드화 (UNKNOWN_PROCEDURE 면 후보 제시)
    # TODO(agent): profile 이 있으면 빈 조건을 채우고 "지난번 선호 기준" 고지 문구 준비 (「AI Agent 설계」 9-4)
    # TODO(agent): CONDITIONS SSE 이벤트 발행 {conditions, missing}
    conditions.setdefault("sort_by", "REVIEW_COUNT")
    missing = [k for k in REQUIRED_CONDITIONS if not conditions.get(k)]
    return {"conditions": conditions, "missing": missing}
