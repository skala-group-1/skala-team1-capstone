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
from coordinator.nodes.suggest_choices import clean_choices, suggest_choices, suggest_client

# Marks LLM runs whose tokens are safe to stream to the user as they generate.
USER_ANSWER_TAG = "user-facing-answer"


def build_coordinator(model, *, business_loader=None, initial_state=None):
    """Create a request-local Main → Tool A/B → Main loop."""
    source = initial_state if initial_state is not None else {}
    tools, results = make_coordinator_tools(business_loader, initial_state=source)
    bound = model.bind_tools(tools, parallel_tool_calls=True)
    tool_map = {t.name: t for t in tools}
    prompt = load_prompt("coordinator", directory=Path(__file__).resolve().parents[1] / "prompts")
    seen = set()
    calls = 0

    async def main(state):
        # This also allows standalone graph callers to supply the initial State.
        source.update(state)
        context = {"locale": (state.get("user") or {}).get("locale") or "en",
                   "action": source.get("action"),
                   "topic": results.get("topic", source.get("topic")),
                   "conditions": results.get("conditions", state.get("conditions", {})),
                   "today": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
                   "candidates": results.get("hospitals", state.get("candidates", []))}
        messages = [
            SystemMessage(content=prompt),
            SystemMessage(content=json.dumps(context, ensure_ascii=False)), *state.get("messages", [])]
        if results.get("consultation_unavailable") or results.get("procedure_answer"):
            return {"messages": [AIMessage(content="")]}
        if results.get("failed") or results.get("ambiguity"):
            return {"messages": [AIMessage(content="")]}
        if results.get("evidence") == "search":
            return {"messages": [AIMessage(content="")]}
        if (results.get("topic", source.get("topic")) not in ("SKIN_CONCERN", "PROCEDURE_INFO", "RECOVERY")
                and results.get("conditions") and not results.get("missing") and not results.get("evidence")
                and results["conditions"] != (state.get("conditions") or {})):
            return {"messages": [AIMessage(content="", tool_calls=[{"name": "hospital_lookup",
                "args": {"operation": "search", "arguments": {}}, "id": "required-search"}])]}
        reply = await bound.ainvoke(messages)
        if (results.get("topic", source.get("topic")) not in ("SKIN_CONCERN", "PROCEDURE_INFO", "RECOVERY")
                and not reply.tool_calls and "conditions" in results and not results.get("missing")
                and not results.get("evidence") and not results.get("failed")):
            reply = AIMessage(content="", tool_calls=[{"name": "hospital_lookup",
                "args": {"operation": "search", "arguments": {}}, "id": "required-search"}])
        return {"messages": [reply]}

    async def execute(state):
        nonlocal calls

        async def run(call):
            try:
                target = tool_map.get(call["name"])
                if call["name"] == "procedure_consultation" and target:
                    return await target.ainvoke(call["args"])
                return await asyncio.wait_for(target.ainvoke(call["args"]), 20) if target else {"status": "unsupported"}
            except Exception as error:
                # Never stringify provider errors: they can contain credentials.
                return {"status": "unavailable", "error_type": type(error).__name__,
                        "message": "Lookup failed; do not invent results."}

        tool_calls = state["messages"][-1].tool_calls
        pending = []
        for call in tool_calls:
            key = (call["name"], json.dumps(call["args"], sort_keys=True))
            if calls >= 8 or key in seen:
                pending.append(None)
            else:
                seen.add(key)
                calls += 1
                pending.append(run(call))
        # Same-turn lookups run concurrently; replies keep the original call order.
        completed = iter(await asyncio.gather(*(p for p in pending if p is not None)))
        messages = []
        for call, scheduled in zip(tool_calls, pending):
            if scheduled is None:
                result = {"status": "stopped", "message": "Do not retry. Report the limitation."}
            else:
                result = next(completed)
            if result.get("status") == "external_search_unavailable":
                results["consultation_unavailable"] = True
            elif result.get("status") not in (None, "ready", "needs_input", "summary_ready"):
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


async def run_coordinator(state, model=None, *, business_loader=None, suggest_model=None):
    """Return a State update. Caller owns message history and merges updates."""
    state = dict(state)
    action = state.get("action") or {}
    if action.get("type") == "SELECT_TOPIC":
        state["topic"] = action.get("topic")
        if state["topic"] == "SKIN_CONCERN":
            greetings = {
                "ko": "어떤 피부 고민이 가장 신경 쓰이세요? 색소·잡티, 모공, 여드름 흉터처럼 고민되는 부분을 알려주세요.",
                "en": "What skin concern bothers you most—for example, dark spots, pores, or acne scars?",
                "zh": "您最在意哪方面的皮肤问题？例如色斑、毛孔或痘疤。",
                "ja": "どのようなお肌の悩みが気になりますか？シミ、毛穴、ニキビ跡など、気になることを教えてください。",
            }
            locale = (state.get("user") or {}).get("locale") or "en"
            return {"topic": state["topic"], "draft": greetings.get(locale, greetings["en"]), "missing": []}
    elif action.get("type") == "FIND_BY_CONCERNS":
        state["topic"] = "SKIN_CONCERN"
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
        # Same light-thinking mode as the hospital agent; empty env value omits it.
        if settings.llm_reasoning_effort:
            options["reasoning_effort"] = settings.llm_reasoning_effort
        model = ChatOpenAI(model=settings.llm_primary_model, api_key=key, timeout=30,
                           max_retries=1, tags=[USER_ANSWER_TAG], **options)
        if suggest_model is None:
            suggest_model = suggest_client()
    # Copy State so internal ToolMessages never leak into caller-owned history.
    graph, results = build_coordinator(model, business_loader=business_loader, initial_state=dict(state))
    try:
        output = await asyncio.wait_for(graph.ainvoke(state, {"recursion_limit": 20}), 120)
    except Exception:
        results["failed"] = True
        output = {"messages": [AIMessage(content="")]}
    update = unavailable(state, "NO_EVIDENCE")
    # Listening and clarification need no lookup; factual claims still require tools.
    if not results.get("failed") and output["messages"][-1].content:
        update = {"draft": output["messages"][-1].content}
    if results.get("evidence") == "search" and not results.get("failed"):
        update["draft"] = search_reply(state, results)
    if results.get("summary") and not results.get("failed"):
        update["draft"] = results["summary"]
    if results.get("procedure_answer") and not results.get("failed"):
        update = {"draft": results["procedure_answer"]}
    if results.get("consultation_unavailable") and not results.get("failed"):
        locale = (state.get("user") or {}).get("locale", "en")
        messages = {
            "ko": "현재 확인된 자료가 없어 시술의 효과·위험을 설명하기 어렵습니다. 의료진에게 물어볼 질문을 함께 정리해 드릴까요?",
            "en": "I don't have verified sources to explain procedure benefits or risks right now. Would you like help preparing questions for a clinician?",
            "zh": "目前没有经过核实的资料，无法说明项目的效果或风险。需要一起整理向医生咨询的问题吗？",
            "ja": "現在、確認済みの資料がないため施術の効果やリスクをご説明できません。医師に相談する質問を一緒に整理しましょうか？",
        }
        update = {"draft": messages.get(locale, messages["en"])}
    if action.get("type") == "SET_SORT":
        update.update({k: state[k] for k in ("conditions", "candidates", "summary", "selected_hospital_id")})
    if "hospitals" in results:
        update["candidates"] = results["hospitals"]
    for field in ("conditions", "missing", "summary", "selected_hospital_id"):
        if field in results:
            update[field] = results[field]
    if results.get("ambiguity") and not results.get("failed"):
        locale = (state.get("user") or {}).get("locale", "en")
        names = list(dict.fromkeys(c["name"] for c in results["ambiguity"] if c.get("name")))
        introductions = {
            "ko": "입력하신 이름과 관련된 등록 시술을 찾았어요. 이름이 비슷해도 같은 시술이나 효과를 뜻하지는 않아요.",
            "en": "I found these registered procedures related to the name you entered. Similar names do not mean the same treatment or effects.",
            "zh": "找到了与您输入的名称相关的已登记项目。名称相似不代表项目或效果相同。",
            "ja": "入力された名前に関連する登録済みの施術が見つかりました。名前が似ていても同じ施術や効果を意味するわけではありません。",
        }
        questions = {
            "ko": "어떤 시술로 병원을 찾아볼까요? 번호나 이름으로 선택해 주세요.",
            "en": "Which procedure should I use to find hospitals? Please choose a number or name.",
            "zh": "您想按哪个项目查找医院？请选择编号或名称。",
            "ja": "どの施術で病院を探しましょうか？番号か名前で選んでください。",
        }
        update["draft"] = (introductions.get(locale, introductions["en"]) + "\n\n"
            + "\n".join(f"{index}. {name}" for index, name in enumerate(names, 1))
            + "\n\n" + questions.get(locale, questions["en"]))
        update["suggestions"] = clean_choices(names)
    elif (update.get("missing") and not results.get("failed")
            and not results.get("consultation_unavailable")
            and not output["messages"][-1].content):
        from coordinator.nodes.ask_clarify import ask_clarify
        update.update(ask_clarify({**state, **update}))
        if "procedure_code" in update["missing"]:
            choices = results.get("ambiguity") or results.get("normalization", {}).get("candidates", [])
            names = [c["name"] for c in choices if c.get("name")]
            if names:
                update["draft"] += "\n" + " / ".join(names)
                update["suggestions"] = clean_choices(names)
    if results.get("failed"):
        update.update(unavailable(state, "LOOKUP_FAILED"))
        update["suggestions"] = []
    elif not update.get("suggestions") and suggest_model is not None:
        locale = (state.get("user") or {}).get("locale", "en")
        update["suggestions"] = await suggest_choices(update.get("draft"), locale, suggest_model)
    update.setdefault("suggestions", [])
    if "topic" in state:
        update["topic"] = state["topic"]
    if "topic" in results:
        update["topic"] = results["topic"]
    return update


def search_reply(state, results):
    """Summarize results; structured cards carry hospital names and prices."""
    locale = (state.get("user") or {}).get("locale", "en")
    labels = {
        "en": ("Found {count} matching hospitals, sorted by {sort}. Browse the cards below.",
               "No hospitals matched your current conditions. Would you like to change the dates or area, or explore information about other procedures for the same concern?", "Needs confirmation",
               ("review count", "rating", "price", "distance")),
        "zh": ("找到了{count}家符合条件的医院，按{sort}排序。请浏览下方卡片。",
               "目前没有找到符合这些条件的医院。您想调整日期或地区，还是了解针对同一困扰的其他项目？", "待确认", ("评论数", "评分", "价格", "距离")),
        "ja": ("条件に合う病院が{count}件見つかりました。{sort}順に表示します。下のカードをご覧ください。",
               "現在の条件に合う病院は見つかりませんでした。日程や地域を変更しますか？それとも、同じお悩みに関する別の施術の情報を調べますか？", "要確認", ("口コミ数", "評価", "価格", "距離")),
        "ko": ("조건에 맞는 병원 {count}곳을 찾았어요. {sort} 기준으로 보여드릴게요. 아래 카드를 확인해 주세요.",
               "현재 조건에 맞는 병원을 찾지 못했어요. 날짜·지역을 바꿔볼까요, 아니면 같은 고민에 대해 알아볼 수 있는 다른 시술 정보도 비교해 드릴까요?", "확인 필요", ("리뷰 수", "평점", "가격", "거리")),
    }
    template, empty, unknown, sorts = labels.get(locale, labels["en"])
    hospitals = results.get("hospitals", [])
    if not hospitals:
        return empty
    sort = dict(zip(("REVIEW_COUNT", "RATING", "PRICE", "DISTANCE"), sorts))
    return template.format(count=len(hospitals), sort=sort.get(results["conditions"].get("sort_by"), unknown))


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
                "DEFAULT_ACTING_USER_ID": {"en": "1", "zh": "3", "ja": "5", "ko": "14"}[locale]},
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
        for hospital in update.get("candidates", []):
            write(json.dumps(hospital, ensure_ascii=False))
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
