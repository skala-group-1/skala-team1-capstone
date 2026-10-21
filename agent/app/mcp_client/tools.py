"""도구 이름 상수 (「MCP 설계」). agent 는 두 서버를 한 Client 로 묶고 접두어 business_ / rag_ 를 붙인다."""

# 「AI Agent 설계」 9-1: planner_agent 도구 화이트리스트 (변경 도구 없음 → 메인에서는 승인 불필요)
PLANNER_TOOLS = (
    "business_search_hospitals",
    "business_get_available_slots",
    "business_get_price_options",
    "business_compare_hospitals",
    "business_plan_trip",
    "business_list_doctors",
    "rag_search_procedure_docs",
)

# 「AI Agent 설계」 4장: 병원 서브그래프 조회 도구 (hospital_id 는 state 에서 강제 주입)
HOSPITAL_READ_TOOLS = (
    "business_get_hospital_detail",
    "business_get_hospital_reviews",
    "business_list_doctors",
    "business_get_price_options",
    "business_get_available_slots",
    "business_get_my_reservations",
    "rag_search_hospital_docs",
    "rag_search_procedure_docs",
)

# 「MCP 설계」 2장: 변경 도구 (destructiveHint) → 반드시 approval interrupt
DESTRUCTIVE_TOOLS = (
    "business_create_reservation_request",
    "business_cancel_reservation",
    "business_request_consultation",
)

# 「공통 계약서」 5장 PendingAction.action 값과의 매핑
PENDING_ACTION_BY_TOOL = {
    "business_create_reservation_request": "CREATE_RESERVATION",
    "business_cancel_reservation": "CANCEL_RESERVATION",
    "business_request_consultation": "REQUEST_CONSULTATION",
}
