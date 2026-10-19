"""Harness — Guardrails (「Harness 명세」, 「AI Agent 설계」 7장).

적용 위치: guard_input 노드 / approval 노드 / respond 출력검사 / 도구 래퍼 / verify(Critic)

TODO(agent): 「AI Agent 설계」 7장 가드레일 표 6케이스를 tests/ 에 그대로 테스트로 옮기기
TODO(agent): 도구 결과·로그의 개인정보(이름·이메일·전화·여권번호) 마스킹 함수
TODO(agent): respond 출력검사 — 추천("best", "最好", "一番" 등)·의료판단·보장 표현 필터
TODO(agent): 답변에 있는 가격이 tool_ledger 에 없으면 "확인 필요"로 치환
"""


def mask_pii(text: str) -> str:
    # TODO(agent): 정규식으로 이메일·전화·여권번호 마스킹
    return text
