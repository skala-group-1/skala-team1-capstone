"""조건부 엣지 함수 모음. 실제 state 값으로 분기한다 (「AI Agent 설계」 9-1, 4장)."""

from langchain_core.messages import AIMessage

from app.graph.state import GUARD_FLAGS, AgentState
from app.mcp_client.tools import DESTRUCTIVE_TOOLS


def _last_tool_calls(state: AgentState) -> list[dict]:
    messages = state.get("messages") or []
    if messages and isinstance(messages[-1], AIMessage):
        return messages[-1].tool_calls or []
    return []


def route_after_guard(state: AgentState) -> str:
    mode = state.get("mode", "MAIN")
    if mode == "HUMAN":
        # D-09: 상담사 연결 중에는 AI 자동응답 정지
        return "end"
    if mode == "HOSPITAL":
        # D-20: 병원 대화창(새 thread)은 처음부터 HOSPITAL 모드
        return "hospital_subgraph"
    if mode == "AFTERCARE":
        return "aftercare_subgraph"
    if any(f in GUARD_FLAGS for f in state.get("guard_flags") or []):
        return "guard_reply"
    if state.get("intent") == "SELECT":
        return "open_hospital_conversation"
    return "extract_conditions"


def route_after_extract(state: AgentState) -> str:
    return "ask_clarify" if state.get("missing") else "planner_agent"


def route_after_planner(state: AgentState) -> str:
    return "tools" if _last_tool_calls(state) else "memory_propose"


def route_after_hospital_agent(state: AgentState) -> str:
    calls = _last_tool_calls(state)
    if not calls:
        return "end"
    if any(c["name"] in DESTRUCTIVE_TOOLS for c in calls):
        return "approval"
    return "hospital_tools"


def route_after_approval(state: AgentState) -> str:
    # approval 노드가 승인 결과를 pending_action["approved"] 에 기록
    action = state.get("pending_action") or {}
    return "execute_action" if action.get("approved") else "hospital_agent"


def route_after_execute(state: AgentState) -> str:
    return "end" if state.get("mode") == "HUMAN" else "hospital_agent"
