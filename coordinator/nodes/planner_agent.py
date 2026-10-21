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
    first = True

    async def main(state):
        nonlocal first
        # This also allows standalone graph callers to supply the initial State.
        source.update(state)
        context = {"locale": (state.get("user") or {}).get("locale") or "en",
                   "action": source.get("action"),
                   "conditions": results.get("conditions", state.get("conditions", {})),
                   "optional_conditions_asked": source.get("optional_conditions_asked", False),
                   "today": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
                   "candidates": results.get("hospitals", state.get("candidates", []))}
        messages = [
            SystemMessage(content=prompt),
            SystemMessage(content=json.dumps(context, ensure_ascii=False)), *state.get("messages", [])]
        if (results.get("failed") or results.get("ambiguity")) and "conditions" in results:
            return {"messages": [AIMessage(content="")]}
        if results.get("evidence") == "search":
            return {"messages": [AIMessage(content="")]}
        if (results.get("conditions") and not results.get("missing") and not results.get("evidence")
                and results["conditions"] != (state.get("conditions") or {})):
            return {"messages": [AIMessage(content="", tool_calls=[{"name": "hospital_lookup",
                "args": {"operation": "search", "arguments": {}}, "id": "required-search"}])]}
        if first:
            first = False
            intake = model.bind_tools([tool_map["collect_conditions"]], parallel_tool_calls=False, tool_choice="collect_conditions")
            reply = await intake.ainvoke([SystemMessage(content=
                "First save all explicit conditions from the user, including a newly mentioned procedure. "
                "procedure_code may be the user's exact phrase: the tool normalizes it. "
                "Omit unchanged and unmentioned fields; never replace prior filters with null. "
                "Consultation language is ONLY an explicitly requested language, never the message language or locale. "
                "Convert areas to the tool enums and relative dates using today. Keep both arrival and departure. "
                "Only user-selected sort; no default. Null only for explicit no preference."), *messages[1:]])
        else:
            reply = await bound.ainvoke(messages)
        if not reply.tool_calls and "conditions" not in results and not results.get("evidence"):
            # One bounded recovery: prose is not proof that intake happened.
            collector = model.bind_tools(tools, parallel_tool_calls=False, tool_choice="collect_conditions")
            reply = await collector.ainvoke(messages + [SystemMessage(content=
                "Save all explicit user conditions now with collect_conditions, even if incomplete. "
                "Use the user's procedure phrase when no verified code exists. Do not answer in prose.")])
        if (not reply.tool_calls and "conditions" in results and not results.get("missing")
                and not results.get("evidence") and not results.get("failed")):
            reply = AIMessage(content="", tool_calls=[{"name": "hospital_lookup",
                "args": {"operation": "search", "arguments": {}}, "id": "required-search"}])
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
            if result.get("status") not in (None, "ready", "needs_input", "summary_ready"):
                results["failed"] = True
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
    # Only the outer conversation graph persists state between user turns.
    return graph.compile(checkpointer=False), results


def unavailable(state, reason):
    locale = (state.get("user") or {}).get("locale", "en")
    text = {"en": "Unable to complete this request. Please try again later.",
            "zh": "暂时无法完成请求，请稍后重试。", "ja": "処理できませんでした。後ほど再度お試しください。",
            "ko": "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."}
    return {"draft": text.get(locale, text["en"]),
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
        model = ChatOpenAI(model=settings.llm_primary_model, api_key=key, timeout=30, max_retries=1)
    # Copy State so internal ToolMessages never leak into caller-owned history.
    graph, results = build_coordinator(model, business_loader=business_loader, initial_state=dict(state))
    try:
        output = await asyncio.wait_for(graph.ainvoke(state, {"recursion_limit": 20}), 120)
    except Exception:
        results["failed"] = True
        output = {"messages": [AIMessage(content="")]}
    update = unavailable(state, "NO_EVIDENCE")
    if results.get("evidence") and not results.get("failed"):
        update = {"draft": output["messages"][-1].content}
    if results.get("evidence") == "search" and not results.get("failed"):
        update["draft"] = search_reply(state, results)
    if results.get("summary") and not results.get("failed"):
        update["draft"] = results["summary"]
    if action.get("type") == "SET_SORT":
        update.update({k: state[k] for k in ("conditions", "candidates", "summary", "selected_hospital_id")})
    if "hospitals" in results:
        update["candidates"] = results["hospitals"]
    for field in ("conditions", "missing", "optional_conditions_asked", "summary", "selected_hospital_id"):
        if field in results:
            update[field] = results[field]
    if update.get("missing") and not results.get("failed"):
        from coordinator.nodes.ask_clarify import ask_clarify
        update.update(ask_clarify({**state, **update}))
        if "procedure_code" in update["missing"]:
            choices = results.get("ambiguity") or results.get("normalization", {}).get("candidates", [])
            names = [c["name"] for c in choices if c.get("name")]
            if names:
                update["draft"] += "\n" + " / ".join(names)
    if results.get("failed"):
        update.update(unavailable(state, "LOOKUP_FAILED"))
    return update


def search_reply(state, results):
    """Render only returned search facts; model prose cannot add medical claims."""
    locale = (state.get("user") or {}).get("locale", "en")
    labels = {
        "en": ("Matching hospitals", "Starting at", "reviews", "Please select hospitals to compare.",
               "No matches. Which filter would you like to change?", "Needs confirmation",
               ("review count", "rating", "price", "distance")),
        "zh": ("符合条件的医院", "起价", "条评论", "请选择要比较的医院。",
               "没有符合条件的医院。您想调整哪个条件？", "待确认", ("评论数", "评分", "价格", "距离")),
        "ja": ("条件に合う病院", "料金", "件の口コミ", "比較する病院を選んでください。",
               "条件に合う病院はありません。どの条件を変更しますか？", "要確認", ("口コミ数", "評価", "価格", "距離")),
        "ko": ("조건에 맞는 병원", "시작 가격", "개 리뷰", "비교할 병원을 선택해 주세요.",
               "조건에 맞는 병원이 없습니다. 어떤 조건을 바꾸시겠어요?", "확인 필요", ("리뷰 수", "평점", "가격", "거리")),
    }
    title, price, reviews, ending, empty, unknown, sorts = labels.get(locale, labels["en"])
    hospitals = results.get("hospitals", [])
    if not hospitals:
        return empty
    sort = dict(zip(("REVIEW_COUNT", "RATING", "PRICE", "DISTANCE"), sorts))
    lines = [f"{title} · {sort.get(results['conditions'].get('sort_by'), unknown)}"]
    for index, hospital in enumerate(hospitals, 1):
        amount = hospital.get("min_price_krw")
        amount = f"{amount:,} KRW" if type(amount) is int else unknown
        lines.append(f"{index}. {hospital.get('name') or unknown} · {price} {amount} · "
                     f"{hospital.get('review_count', unknown)} {reviews}")
    return "\n".join([*lines, ending])


async def planner_agent(state: AgentState) -> dict:
    """Reuse the worker loop for model clients and graph execution."""
    return await run_coordinator(state)


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
