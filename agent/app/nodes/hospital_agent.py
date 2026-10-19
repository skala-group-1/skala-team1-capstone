"""hospital_agent — 병원 범위 질문에 LLM + 병원 도구로 답변 (ReAct)

- 입력 → 출력: messages, selected_hospital_id → tool_calls 있는 AIMessage 또는 draft
- LLM/도구: LLM_PRIMARY_MODEL tool-calling, HOSPITAL_READ_TOOLS + DESTRUCTIVE_TOOLS bind
- 프롬프트: prompts/hospital_agent.md
- 근거: 「AI Agent 설계」 4장 (다른 병원 질문 → 메인 대화창으로 돌아가기 안내)
"""

import uuid

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.graph.state import AgentState

_BOOK_KEYWORDS = ("예약", "book", "预约", "予約")


def hospital_agent(state: AgentState) -> dict:
    # TODO(agent): 아래 더미 로직을 LLM tool-calling 으로 교체
    # TODO(agent): 상담 요청 시 summarize_handoff.md 로 니즈 요약 카드 생성 → request_consultation 인자
    messages = state.get("messages") or []
    last = messages[-1] if messages else None

    if isinstance(last, ToolMessage):
        return {"draft": f"[hospital_agent 골격] 도구 결과 반영: {last.content}"}

    if isinstance(last, HumanMessage) and any(k in str(last.content).lower() for k in _BOOK_KEYWORDS):
        # 골격: 예약 요청 흐름(approval interrupt)을 CLI 에서 확인할 수 있도록 가짜 변경 도구 호출
        call = {
            "name": "business_create_reservation_request",
            "args": {"hospital_id": state.get("selected_hospital_id") or 1, "slot_id": 1,
                     "procedure_code": "DOUBLE_EYELID_NONINCISION", "idempotency_key": str(uuid.uuid4())},
            "id": f"call_{uuid.uuid4().hex[:8]}",
        }
        return {"messages": [AIMessage(content="", tool_calls=[call])]}

    return {"draft": "[hospital_agent 골격] 병원 질문 답변 자리"}
