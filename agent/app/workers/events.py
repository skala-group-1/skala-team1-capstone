"""SSE 이벤트 타입 (「공통 계약서」 6장). agent 는 ai.task.event 로 발행하고 backend 가 SSE 로 중계한다.

규칙: 한 작업의 마지막 이벤트는 반드시 DONE / FAILED / APPROVAL_REQUIRED 중 하나.
"""

from enum import StrEnum


class SseEvent(StrEnum):
    STATUS = "STATUS"
    TOKEN = "TOKEN"
    TOOL_START = "TOOL_START"
    TOOL_END = "TOOL_END"
    CONDITIONS = "CONDITIONS"
    RESULT_CARDS = "RESULT_CARDS"
    CONVERSATION_OPENED = "CONVERSATION_OPENED"
    MODE_CHANGED = "MODE_CHANGED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    TRIP_PLAN = "TRIP_PLAN"
    MEMORY_PROPOSAL = "MEMORY_PROPOSAL"
    VERIFY = "VERIFY"
    DONE = "DONE"
    FAILED = "FAILED"


TERMINAL_EVENTS = frozenset({SseEvent.DONE, SseEvent.FAILED, SseEvent.APPROVAL_REQUIRED})

# TODO(agent): 그래프 실행(astream_events) → SseEvent 변환기
#   on_chat_model_stream → TOKEN, on_tool_start/end → TOOL_START/END(label 은 사용자 locale),
#   노드 결과(conditions·candidates·trip_plans·memory_proposal) → CONDITIONS/RESULT_CARDS/TRIP_PLAN/MEMORY_PROPOSAL,
#   __interrupt__ → APPROVAL_REQUIRED, 정상 종료 → DONE {answer, sources}
# TODO(agent): seq 는 작업별 1부터 증가 (backend 가 SSE id 로 사용, Last-Event-ID 재전송)
