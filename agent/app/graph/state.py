"""에이전트 State 정의.

「AI Agent 설계」 2장(State) + 9-5(Agentic v2 추가 필드) 그대로 옮긴 것.
필드명·의미를 바꾸면 「AI Agent 설계」를 먼저 고치고 팀에 공지한다.
DTO(camelCase) ↔ state(snake_case) 변환은 workers/ 와 mcp_client/ 경계에서 한다.
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

Mode = Literal["MAIN", "HOSPITAL", "HUMAN", "AFTERCARE"]

# 「공통 계약서」 2장 Intent (agent 내부). PLAN 은 「AI Agent 설계」 9-1 v2 분기에 등장
INTENTS = ("SEARCH", "INFO", "PLAN", "SELECT", "HOSPITAL_QA", "BOOK", "HANDOFF", "OTHER")

# 「공통 계약서」 2장 GuardFlag (agent 내부). 이 중 하나라도 있으면 guard_reply 로 분기
GUARD_FLAGS = ("RECOMMEND_REQUEST", "MEDICAL_JUDGMENT", "GUARANTEE", "OFF_TOPIC", "INJECTION")

# 「AI Agent 설계」 3장: 필수 조건. 예산·상담언어는 한 번만 묻고 "상관없음" 허용
# TODO(agent): 9-2 일정 플래너는 date_to(출국일)도 필요 → PLAN intent 일 때 필수 조건에 추가할지 결정
REQUIRED_CONDITIONS = ("procedure_code", "date_from")


class Conditions(TypedDict, total=False):
    procedure_code: str | None        # 표준 코드 (DOUBLE_EYELID_NONINCISION ...)
    areas: list[str]                  # GANGNAM, SINSA, MYEONGDONG ...
    date_from: str | None             # YYYY-MM-DD, 입국일 (「공통 계약서」 Agentic v2)
    date_to: str | None               # YYYY-MM-DD, 출국일
    budget_max_krw: int | None
    consult_language: str | None      # en / zh / ja
    sort_by: str                      # REVIEW_COUNT | RATING | PRICE | DISTANCE


class AgentState(TypedDict, total=False):
    # --- 「AI Agent 설계」 2장 ---
    messages: Annotated[list[AnyMessage], add_messages]
    user: dict                        # user_id, role, locale (개인정보 X)
    mode: Mode
    topic: str | None                 # Existing SELECT_TOPIC value, retained across turns.
    intent: str | None                # INTENTS 중 하나
    conditions: Conditions
    missing: list[str]                # 비어 있는 필수 조건
    candidates: list[dict]            # 검색 결과 요약 (id, 이름, 가격, 리뷰, 최초 슬롯)
    selected_hospital_id: int | None
    pending_action: dict | None       # 승인 대기 중인 변경 도구 {tool, args, display}
    citations: list[dict]             # {doc_id, section, title, uri}
    guard_flags: list[str]            # GUARD_FLAGS 중
    summary: str | None               # 토큰 예산 초과 시 오래된 대화 요약
    loop: dict                        # turn, tool_counts, started_at (Harness)

    # --- 「AI Agent 설계」 9-5 (Agentic v2) ---
    profile: dict | None              # 장기 기억에서 로드
    trip_plans: list[dict]            # business_plan_trip 결과
    tool_ledger: dict                 # verify 대조용 사실 저장소
    draft: str | None                 # planner 초안 (골격에서는 모든 분기 노드의 "보낼 답변" 버퍼로 사용 → respond 가 메시지로 변환)
    verify_attempts: int
    memory_proposal: dict | None

    # --- 골격에서 추가 (「AI Agent 설계」에 없음, 확정 시 문서 반영) ---
    verify_passed: bool | None        # verify 노드 결과. 라우팅용
    parent_conversation_id: str | None  # D-20 병원 대화창의 부모 대화

    # 병원 서브에이전트 내부 상태. 외부 DTO/큐 계약에는 포함하지 않는다.
    hospital_context: dict             # hospital_id 및 MCP에서 읽은 기본정보·의사·가격
    hospital_booking: dict             # 사용자가 선택한 procedure_code, date, time
    aftercare_context: dict            # 사후관리 대화의 예약·시술·시술일 (aftercare/)

    # Queue/task context and UI event outputs (internal only).
    task_id: str
    conversation_id: str
    action: dict | None
    opened_conversation: dict | None   # child id/hospital, mode, parent, consultation_id, conditions
    consultation_id: int | None
    relax_options: list[dict]
    trip_summary: str
    optional_conditions_asked: bool
