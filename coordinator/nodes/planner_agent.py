"""Hospital discovery coordinator and manual demo.

From agent/: PYTHONPATH=.. uv run python -m coordinator.nodes.planner_agent --locale en
Real LLM + existing mock Business MCP; no RAG, bookings or hospital connection.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from app.graph.state import AgentState
from app.harness.instructions import load_prompt
from coordinator.nodes.coordinator_tools import make_coordinator_tools


def build_coordinator(model, *, business_loader=None, initial_state=None):
    """Create a request-local Main → Tool A/B → Main loop."""
    source = initial_state if initial_state is not None else {}
    tools, results = make_coordinator_tools(business_loader, initial_state=source)
    bound = model.bind_tools(tools, parallel_tool_calls=False)
    tool_map = {t.name: t for t in tools}
    prompt = load_prompt("coordinator", directory=Path(__file__).resolve().parents[1] / "prompts")
    seen = set()
    calls = 0

    async def main(state):
        # This also allows standalone graph callers to supply the initial State.
        source.update(state)
        context = {"locale": (state.get("user") or {}).get("locale") or "en",
                   "action": source.get("action"),
                   "conditions": results.get("conditions", state.get("conditions", {})),
                   "optional_conditions_asked": source.get("optional_conditions_asked", False),
                   "today": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
                   "candidates": results.get("hospitals", state.get("candidates", []))}
        reply = await bound.ainvoke([
            SystemMessage(content=prompt),
            SystemMessage(content=json.dumps(context, ensure_ascii=False)), *state.get("messages", [])])
        return {"messages": [reply]}

    async def execute(state):
        nonlocal calls
        messages = []
        for call in state["messages"][-1].tool_calls:
            key = (call["name"], json.dumps(call["args"], sort_keys=True))
            if calls >= 8 or key in seen:
                result = {"status": "stopped", "message": "Do not retry. Report the limitation."}
            else:
                seen.add(key)
                calls += 1
                try:
                    target = tool_map.get(call["name"])
                    result = await asyncio.wait_for(target.ainvoke(call["args"]), 20) if target else {"status": "unsupported"}
                except Exception as error:
                    # Never stringify provider errors: they can contain credentials.
                    result = {"status": "unavailable", "error_type": type(error).__name__,
                              "message": "Lookup failed; do not invent results."}
            messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"]))
        return {"messages": messages}

    def route(state):
        return "tools" if state["messages"][-1].tool_calls else END

    graph = StateGraph(AgentState)
    graph.add_node("main", main)
    graph.add_node("tools", execute)
    graph.add_edge(START, "main")
    graph.add_conditional_edges("main", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "main")
    return graph.compile(), results


def unavailable(state, reason):
    locale = (state.get("user") or {}).get("locale", "en")
    text = {"en": "Unable to complete this request. Please try again later.",
            "zh": "暂时无法完成请求，请稍后重试。", "ja": "処理できませんでした。後ほど再度お試しください。",
            "ko": "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."}
    return {"draft": f"[planner_agent: {reason}] " + text.get(locale, text["en"]),
            "candidates": [], "summary": None, "selected_hospital_id": None}


async def run_coordinator(state, model=None, *, business_loader=None):
    """Return a State update. Caller owns message history and merges updates."""
    state = dict(state)
    action = state.get("action") or {}
    if action.get("type") == "SET_SORT":
        from coordinator.nodes.coordinator_tools import ConditionPatch
        try:
            patch = ConditionPatch(sort_by=action.get("sortBy"))
            if patch.sort_by is None:
                raise ValueError("Missing sort")
        except ValueError:
            return unavailable(state, "INVALID_SORT")
        state["conditions"] = {**(state.get("conditions") or {}), "sort_by": patch.sort_by}
        state.update({"candidates": [], "summary": None, "selected_hospital_id": None})
    if model is None:
        from app.config import get_settings
        from langchain_openai import ChatOpenAI
        settings = get_settings()
        key = settings.openai_api_key
        if not key:
            return unavailable(state, "API_KEY_MISSING")
        if any(c.isspace() for c in key):
            return unavailable(state, "API_KEY_WHITESPACE")
        options = {}
        if settings.llm_reasoning_effort:
            options["reasoning_effort"] = settings.llm_reasoning_effort
        model = ChatOpenAI(model=settings.llm_primary_model, api_key=key, timeout=30, max_retries=1, **options)
    # Copy State so internal ToolMessages never leak into caller-owned history.
    graph, results = build_coordinator(model, business_loader=business_loader, initial_state=dict(state))
    try:
        output = await asyncio.wait_for(graph.ainvoke(state, {"recursion_limit": 20}), 120)
    except Exception as error:
        return unavailable(state, type(error).__name__)
    update = {"draft": output["messages"][-1].content}
    if action.get("type") == "SET_SORT":
        update.update({k: state[k] for k in ("conditions", "candidates", "summary", "selected_hospital_id")})
    if "hospitals" in results:
        update["candidates"] = results["hospitals"]
    for field in ("conditions", "missing", "optional_conditions_asked", "summary", "selected_hospital_id"):
        if field in results:
            update[field] = results[field]
    if update.get("missing"):
        from coordinator.nodes.ask_clarify import ask_clarify
        update.update(ask_clarify({**state, **update}))
    return update


def planner_agent(state: AgentState) -> dict:
    """Keep existing sync node API; async LangGraph executes it in a worker."""
    return asyncio.run(run_coordinator(state))


async def chat_with_mock_hospitals(locale="en", *, read=input, write=print, runner=None):
    """Interactive real-model demo with existing mock JSON over stdio MCP."""
    from app.config import get_settings
    from langchain_mcp_adapters.client import MultiServerMCPClient

    root = Path(__file__).resolve().parents[2]
    interpreter = root / "mcp/.venv/bin/python"
    if runner is None and not get_settings().openai_api_key:
        write("OPENAI_API_KEY가 없습니다. 저장소 루트 .env를 확인하세요.")
        return
    if runner is None and not interpreter.exists():
        write("먼저 저장소 루트에서 실행: uv sync --project mcp --frozen")
        return
    client = MultiServerMCPClient({"business": {
        "transport": "stdio", "command": str(interpreter),
        "args": ["-m", "business_mcp.server"], "cwd": str(root / "mcp"),
        "env": {"MCP_TRANSPORT": "stdio", "USE_STUB": "true",
                "DEFAULT_ACTING_USER_ID": {"en": "1", "zh": "3", "ja": "5", "ko": "1"}[locale]},
    }}, tool_name_prefix=True)
    cached = None

    async def loader():
        nonlocal cached
        if cached is None:
            cached = await client.get_tools(server_name="business")
        return cached

    execute = runner or run_coordinator
    state = {"messages": [], "user": {"locale": locale}}
    write(f"실시간 상담 | 로그인 언어: {locale} | 실제 LLM + 기존 mock 병원")
    write("LLM API 비용 발생. 웹 검색·실제 예약·병원 Agent 연결 없음. 종료: /exit")
    previous_summary = None
    while True:
        try:
            text = read("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("/exit", "/quit"):
            break
        if not text:
            continue
        state["messages"].append(HumanMessage(content=text))
        update = await execute(state, business_loader=loader)
        state.update(update)
        answer = update.get("draft", "")
        state["messages"].append(AIMessage(content=answer))
        write("Agent > " + str(answer))
        brief = state.get("summary")
        if brief and brief != previous_summary:
            write("\n--- 미전송 인계 요약 ---\n" + brief)
        previous_summary = brief


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Live coordinator with existing mock hospitals")
    parser.add_argument("--locale", choices=("en", "zh", "ja", "ko"), default="en",
                        help="Saved login language (ko: developer testing)")
    asyncio.run(chat_with_mock_hospitals(parser.parse_args().locale))
