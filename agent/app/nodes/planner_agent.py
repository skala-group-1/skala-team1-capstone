"""planner_agent — 검색·비교·일정계획을 LLM 이 스스로 도구를 골라 반복 (Agentic v2)

- 입력 → 출력: conditions, profile, messages → (tool_calls 가 있는 AIMessage) 또는 draft
- LLM/도구: LLM_PRIMARY_MODEL tool-calling, 도구는 mcp_client.tools.PLANNER_TOOLS 만 bind
- 프롬프트: prompts/system_base.md (+ planner 전용 프롬프트 필요 시 추가)
- 근거: 03 문서 9-1, 9-2(일정 적합성 플래너), D-22·D-23, 05 문서 Agent Loop
"""

from app.graph.state import AgentState


def planner_agent(state: AgentState) -> dict:
    # TODO(agent): ChatOpenAI(model=settings.llm_primary_model).bind_tools(PLANNER_TOOLS 도구들)
    # TODO(agent): 0건이면 스스로 조건 완화 재검색 + "완화했다" 설명, relaxOptions 카드 (03 문서 9-1)
    # TODO(agent): 체류 기간이 있으면 상위 5곳 business_plan_trip → 불가 시 대체 시술 탐색 (03 문서 9-2)
    # TODO(agent): verify 가 불일치 피드백을 넣었으면 그 피드백을 반영해 재생성
    # TODO(agent): harness.loop.check_limits 로 한도 확인, loop.turn 증가
    # TODO(agent): RESULT_CARDS / TRIP_PLAN SSE 이벤트용 구조화 데이터를 state(candidates, trip_plans)에 저장
    loop = dict(state.get("loop") or {})
    loop["turn"] = loop.get("turn", 0) + 1
    return {"draft": f"[planner_agent 골격] conditions={state.get('conditions')}", "loop": loop}
