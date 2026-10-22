"""Harness — Agent Loop 한도 (「Harness 명세」 Agent Loop, Agentic v2 반영).

기준값은 여기 한 곳에만 둔다. 바꾸면 「Harness 명세」 표와 평가셋 결과를 같이 갱신.
"""

MAX_TURNS = 8                 # planner_agent / hospital_agent 루프 최대 턴
MAX_TASK_SECONDS = 120        # 작업 1개 최대 시간
MAX_SAME_TOOL_CALLS = 3       # 같은 도구 + 같은 인자 반복 허용 횟수 (get_available_slots 는 병원마다 인자가 다름)


def new_loop_state(started_at: float) -> dict:
    return {"turn": 0, "tool_counts": {}, "started_at": started_at}


def check_limits(loop: dict, now: float) -> str | None:
    """한도 초과 사유를 돌려준다. 없으면 None.

    TODO(agent): planner_agent·hospital_agent 진입 시 호출하고, 초과면 부분 답변 + "상담사 연결" 제안으로 종료 (「Harness 명세」)
    TODO(agent): tool_counts 키를 (도구명, 정렬된 인자 JSON) 으로 만들어 같은 인자 반복을 센다
    """
    if loop.get("turn", 0) >= MAX_TURNS:
        return "MAX_TURNS"
    if now - loop.get("started_at", now) > MAX_TASK_SECONDS:
        return "TIMEOUT"
    if any(c >= MAX_SAME_TOOL_CALLS for c in (loop.get("tool_counts") or {}).values()):
        return "SAME_TOOL_REPEATED"
    return None
