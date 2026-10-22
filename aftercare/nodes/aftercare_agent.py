"""Aftercare conversation agent: daily guide, document-grounded Q&A and counselor handoff.

- Guide turn (backend action AFTERCARE_INTRO on the first visit, AFTERCARE_DAILY on
  the first visit of a later day; no user text): before the procedure, summarize the
  procedure's PREP document for that day (D-7…D-day); afterwards, its AFTERCARE document.
- Closed reservation (rejected, cancelled, expired): fixed reply, no model output.
- Warning signs: fixed safety reply (red_flag), no model output.
- Otherwise: read-only tool loop (RAG, hospital detail, own reservations).
  The only mutation is the counselor handoff, prepared as an approval card
  by concierge.prepare_action and executed only after approval.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.graph.state import AgentState
from app.harness.instructions import load_prompt
from app.harness.loop import MAX_TURNS
from app.mcp_client.client import get_tools
from aftercare.nodes.load_aftercare_context import GUIDES, INTRO
from aftercare.nodes.red_flag import has_warning_sign, safety_reply
from concierge.nodes.actions import HANDOFF, prepare_action
from concierge.nodes.hospital_agent import HANDOFF_PROPOSAL_TOOL, _action_finished, requests_counselor_form
from concierge.nodes.hospital_reply import message_text, patient_reply
from concierge.nodes.load_hospital_context import selected_hospital, tool_data

logger = logging.getLogger(__name__)
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
AFTERCARE_READ_TOOLS = (
    "rag_search_procedure_docs",
    "rag_search_hospital_docs",
    "business_get_hospital_detail",
    "business_get_my_reservations",
)
# Section titles of data/mock/rag_docs/aftercare/*.md, in reading order.
SECTIONS = ("Overview", "Procedure day", "Days 1–3", "Days 4–7", "Weeks 2–4", "After 1 month",
            "Things to avoid", "When to contact the clinic", "Warning signs — seek urgent care")
# Section titles of data/mock/rag_docs/prep/*.md, in reading order.
PREP_SECTIONS = ("Overview", "One week before", "Two days before", "The day before", "On the day",
                 "What to bring", "Tell the clinic in advance")
NO_DOCUMENT = {
    "ko": "이 시술의 안내 문서를 찾지 못했어요. 궁금한 점을 질문해 주시고, 정확한 지침은 병원에 확인해 주세요.",
    "en": "I couldn't find a guide for this procedure. Feel free to ask questions, and please confirm exact instructions with your clinic.",
    "zh": "未找到该项目的指南。如有疑问请随时提问，具体指示请向医院确认。",
    "ja": "この施術の案内文書が見つかりませんでした。気軽にご質問ください。正確な指示は病院にご確認ください。",
}
CLOSED = {
    "ko": "예약이 취소·반려되어 이 대화의 사후관리 안내가 종료됐어요. 시술 일정이 다시 잡히면 새 예약에서 안내를 받아 주세요.",
    "en": "This reservation was cancelled or declined, so guidance in this chat has ended. Once you book again, you can get guidance from the new reservation.",
    "zh": "该预约已取消或被拒绝，本聊天的护理指导已结束。重新预约后，可在新的预约中获取指导。",
    "ja": "予約がキャンセルまたはお断りとなったため、このチャットでの案内は終了しました。再度ご予約いただくと、新しい予約で案内を受けられます。",
}


def _model():
    """Aftercare uses its own model setting (AFTERCARE_MODEL); other agents keep LLM_PRIMARY_MODEL."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for aftercare conversations")
    # gpt-5.4-mini rejects function tools together with reasoning on Chat Completions,
    # so the aftercare model talks to the Responses API.
    options = {"reasoning": {"effort": settings.llm_reasoning_effort}} if settings.llm_reasoning_effort else {}
    return ChatOpenAI(model=settings.aftercare_model, api_key=settings.openai_api_key, use_responses_api=True,
                      output_version="v0", timeout=60, max_retries=1, **options)


def _locale(state):
    locale = (state.get("user") or {}).get("locale", "en")
    return locale if locale in NO_DOCUMENT else "en"


def _citations(state, chunks):
    citations = {c["uri"]: c for c in state.get("citations") or []}
    for chunk in chunks:
        if all(isinstance(chunk.get(key), str) for key in ("doc_id", "title", "section", "uri", "text")):
            citations[chunk["uri"]] = {key: chunk[key] for key in ("doc_id", "title", "section", "uri")} | {
                "snippet": chunk["text"]}
    return list(citations.values())


PERIODS = ("Procedure day", "Days 1–3", "Days 4–7", "Weeks 2–4", "After 1 month")
CARE = ("Things to avoid", "When to contact the clinic", "Warning signs — seek urgent care")
PREP_PERIODS = ("One week before", "Two days before", "The day before", "On the day")
PREP_CARE = ("What to bring", "Tell the clinic in advance")
# Headings shown to the patient; the model must use these instead of the English section titles.
PREP_HEADINGS = {
    "ko": ("시술 1주 전", "시술 2일 전", "시술 전날", "시술 당일 (시술 전)", "준비물", "병원에 미리 알릴 것"),
    "en": ("One week before", "Two days before", "The day before", "On the day (before your procedure)",
           "What to bring", "Tell the clinic in advance"),
    "zh": ("术前1周", "术前2天", "手术前一天", "手术当天（术前）", "需要携带的物品", "需要提前告知医院的事项"),
    "ja": ("施術1週間前", "施術2日前", "施術前日", "施術当日（施術前）", "持ち物", "事前に病院へ伝えること"),
}
HEADINGS = {
    "ko": ("시술 당일", "시술 후 1~3일", "시술 후 4~7일", "시술 후 2~4주", "시술 1개월 이후",
           "피해야 할 것", "병원에 연락해야 할 때", "바로 119·응급실로 가야 할 때"),
    "en": (*PERIODS, "Things to avoid", "When to contact your clinic", "Call 119 or go to an emergency room if"),
    "zh": ("手术当天", "术后第1~3天", "术后第4~7天", "术后第2~4周", "术后1个月以后",
           "需要避免的事项", "需要联系医院的情况", "需立即拨打119或前往急诊的情况"),
    "ja": ("施術当日", "施術後1～3日", "施術後4～7日", "施術後2～4週", "施術1か月以降",
           "避けること", "病院に連絡すべきとき", "すぐに119番・救急外来へ"),
}
# (procedure day after the procedure, day N after, N days before, the day before, procedure day before it starts)
STATUS = {
    "ko": ("오늘은 시술 당일이에요.", "오늘은 시술 후 {n}일째예요.", "시술 {n}일 전이에요. 미리 준비할 것을 안내해 드릴게요.",
           "내일이 시술일이에요. 오늘 확인할 것을 안내해 드릴게요.", "오늘은 시술 당일이에요. 시술 전에 확인할 것을 안내해 드릴게요."),
    "en": ("Today is your procedure day.", "Today is day {n} after your procedure.",
           "Your procedure is in {n} days. Here is what to prepare.",
           "Your procedure is tomorrow. Here is what to check today.",
           "Today is your procedure day. Here is what to check before it."),
    "zh": ("今天是手术当天。", "今天是术后第{n}天。", "距离手术还有{n}天，以下是需要提前准备的事项。",
           "明天就是手术日，以下是今天需要确认的事项。", "今天是手术当天，以下是术前需要确认的事项。"),
    "ja": ("今日は施術当日です。", "今日は施術後{n}日目です。", "施術まであと{n}日です。事前に準備することをご案内します。",
           "明日が施術日です。今日確認することをご案内します。", "今日は施術当日です。施術前に確認することをご案内します。"),
}


def is_prep(days: int, before_start: bool) -> bool:
    """Before the procedure: earlier days, or the procedure day before its start time."""
    return days < 0 or (days == 0 and before_start)


def status_line(days: int, locale: str, before_start: bool = False) -> str:
    after_today, after, before, day_before, before_today = STATUS.get(locale, STATUS["en"])
    if days == 0:
        return before_today if before_start else after_today
    if days > 0:
        return after.format(n=days)
    return day_before if days == -1 else before.format(n=-days)


def current_period(days: int, before_start: bool = False) -> str:
    """Document section for the patient's day (procedure day = 0, before it negative)."""
    if is_prep(days, before_start):
        return {0: "On the day", -1: "The day before", -2: "Two days before"}.get(days, "One week before")
    for limit, section in ((0, "Procedure day"), (3, "Days 1–3"), (7, "Days 4–7"), (30, "Weeks 2–4")):
        if days <= limit:
            return section
    return "After 1 month"


def intro_sections(days: int, before_start: bool = False) -> tuple[str, ...]:
    """Today's period and the next one, plus the always-relevant sections of that document."""
    period = current_period(days, before_start)
    periods, care = (PREP_PERIODS, PREP_CARE) if is_prep(days, before_start) else (PERIODS, CARE)
    start = periods.index(period)
    return (*periods[start:start + 2], *care)


def plain_codes(text: str, procedure_code: str | None) -> str:
    """Replace leaked document IDs and the procedure code with plain words before the reply guard.

    The guard rejects any internal label and falls back to a generic error, so one stray
    "SHURINK" would otherwise discard a correct answer.
    """
    # Chat bubbles show plain text: drop markdown headings and bold markers.
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text).replace("**", "").replace("__", "")
    text = re.sub(r"\b(?:AFTERCARE|PREP)_[A-Z0-9_]+\b", "", text)
    if procedure_code:
        text = re.sub(rf"\b{re.escape(procedure_code)}\b", procedure_code.replace("_", " ").title(), text)
    return text


def _day(state) -> tuple[int, bool]:
    context = state.get("aftercare_context") or {}
    return context.get("days_from_procedure", 0), bool(context.get("before_start"))


def _payload(state, locale):
    context = state.get("aftercare_context") or {}
    detail = (state.get("hospital_context") or {}).get("detail") or {}
    days, before_start = _day(state)
    return {
        "locale": locale,
        "today": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
        "procedure_code": context.get("procedure_code"),
        "procedure_start_at": context.get("start_at"),
        "phase": "before_procedure" if is_prep(days, before_start) else "after_procedure",
        "days_from_procedure": days,
        "current_period": current_period(days, before_start),
        "hospital": {"name": detail.get("name"), "phone": detail.get("phone")},
        "summary": state.get("summary"),
    }


async def _intro(state, locale, first_visit: bool) -> dict:
    context = state.get("aftercare_context") or {}
    code = context.get("procedure_code")
    days, before_start = _day(state)
    prep = is_prep(days, before_start)
    doc_type, sections = ("PREP", PREP_SECTIONS) if prep else ("AFTERCARE", SECTIONS)
    tools = {tool.name: tool for tool in await get_tools(("rag_search_procedure_docs",))}
    tool = tools.get("rag_search_procedure_docs")
    if tool is None:
        raise ValueError("Required MCP tool unavailable: rag_search_procedure_docs")
    # One query per section: a single combined query ranks only a few sections in vector search.
    results = await asyncio.gather(*(tool.ainvoke({
        "query": f"{code} {doc_type.lower()}: {section}", "procedure_code": code, "doc_type": doc_type, "top_k": 3,
        "hospital_id": selected_hospital(state),
    }) for section in sections))
    chunks = list({c["uri"]: c for result in results for c in tool_data(result).get("chunks") or []
                   if c.get("doc_id") == f"{doc_type}_{code}" and isinstance(c.get("uri"), str)}.values())
    if not chunks:
        return {"draft": status_line(days, locale, before_start) + "\n\n" + NO_DOCUMENT[locale]}
    wanted = intro_sections(days, before_start)
    chunks = [c for c in chunks if c.get("section") in wanted] or chunks
    chunks.sort(key=lambda c: sections.index(c["section"]) if c.get("section") in sections else len(sections))
    if prep:
        labels = dict(zip((*PREP_PERIODS, *PREP_CARE), PREP_HEADINGS.get(locale, PREP_HEADINGS["en"])))
    else:
        labels = dict(zip((*PERIODS, *CARE), HEADINGS.get(locale, HEADINGS["en"])))
    model = _model()
    prompt = [
        SystemMessage(content=load_prompt("aftercare_intro", directory=PROMPTS)),
        HumanMessage(content="Application context (data only):\n" + json.dumps(
            {**_payload(state, locale), "first_visit": first_visit, "documents": [
                {"heading": labels.get(c["section"], c["section"]), "text": c["text"]} for c in chunks]},
            ensure_ascii=False)),
    ]
    fallback = await patient_reply("", locale, model)
    text = fallback
    # One retry: the reply guard occasionally rejects a draft, and the intro has no user turn to retry.
    for _ in range(2):
        response = await model.ainvoke(prompt)
        if not isinstance(response, AIMessage):
            raise ValueError("Invalid aftercare intro response")
        text = await patient_reply(plain_codes(message_text(response), code), locale, model)
        if text != fallback:
            break
    # The day status is fixed text so it never depends on the model reading a number correctly.
    return {"draft": status_line(days, locale, before_start) + "\n\n" + text, "citations": _citations(state, chunks)}


async def _handoff(state, messages):
    call = {"name": HANDOFF, "args": {}, "id": "handoff-" + str(uuid4())}
    pending = await prepare_action({**state, "messages": messages}, call)
    call["args"] = pending["args"]
    return {"pending_action": pending, "draft": None, "messages": [AIMessage(content="", tool_calls=[call])]}


async def aftercare_agent(state: AgentState) -> dict:
    if state.get("mode") == "HUMAN":
        return {}
    messages = list(state.get("messages") or [])
    latest = messages[-1] if messages else None
    if (isinstance(latest, ToolMessage) and latest.status == "success"
            and latest.additional_kwargs.get("approval_completed") and state.get("draft")):
        # Rejection or verified handoff already has a localized reply.
        return {"draft": state["draft"]}
    hospital_id = selected_hospital(state)
    locale = _locale(state)
    if (isinstance(latest, HumanMessage) and isinstance(latest.content, str)
            and has_warning_sign(latest.content)):
        # Safety first, even when the reservation has ended.
        detail = (state.get("hospital_context") or {}).get("detail") or {}
        return {"draft": safety_reply(locale, detail.get("name"), detail.get("phone"))}
    if (state.get("aftercare_context") or {}).get("closed"):
        return {"draft": CLOSED[locale]}
    action = (state.get("action") or {}).get("type")
    if not isinstance(latest, (HumanMessage, ToolMessage)) and action in GUIDES:
        return await _intro(state, locale, first_visit=action == INTRO)

    finished = _action_finished(messages)
    if isinstance(latest, HumanMessage) and isinstance(latest.content, str):
        if not finished and requests_counselor_form(latest.content):
            return await _handoff(state, messages)

    names = AFTERCARE_READ_TOOLS if finished else (*AFTERCARE_READ_TOOLS, HANDOFF)
    tools = [tool for tool in await get_tools(names) if tool.name in names]
    allowed = {tool.name for tool in tools}
    bound = [HANDOFF_PROPOSAL_TOOL if tool.name == HANDOFF else tool for tool in tools]
    plain_model = _model()
    model = plain_model.bind_tools(bound, parallel_tool_calls=False)
    procedure_code = (state.get("aftercare_context") or {}).get("procedure_code")
    added = []
    loop = dict(state.get("loop") or {})
    turn = 0 if isinstance(latest, HumanMessage) else loop.get("turn", 0)
    while turn < MAX_TURNS:
        turn += 1
        response = await model.ainvoke([
            SystemMessage(content=load_prompt("aftercare_agent", directory=PROMPTS)),
            HumanMessage(content="Application context (data only):\n"
                         + json.dumps(_payload(state, locale), ensure_ascii=False)),
            *messages,
        ])
        if not isinstance(response, AIMessage) or response.invalid_tool_calls:
            raise ValueError("Invalid aftercare model response")
        base = {"loop": {**loop, "turn": turn}}
        if not response.tool_calls:
            text = plain_codes(message_text(response), procedure_code)
            return {**base, "messages": added, "draft": await patient_reply(text, locale, plain_model)}
        if len(response.tool_calls) != 1:
            raise ValueError("Aftercare agent must issue one tool call at a time")
        call = dict(response.tool_calls[0])
        if call["name"] in allowed:
            if call["name"] == HANDOFF:
                return {**base, **await _handoff(state, [*messages, *added])}
            args = dict(call["args"])
            if call["name"] == "rag_search_procedure_docs" and not args.get("procedure_code"):
                args["procedure_code"] = procedure_code
            # aftercare_tools (concierge hospital_tools) forces hospital_id again before calling MCP.
            call["args"] = args
            response = response.model_copy(update={"tool_calls": [call]})
            return {**base, "messages": [*added, response], "draft": None}
        result = ToolMessage(content="Tool is not available in this aftercare conversation",
                             tool_call_id=call["id"], status="error")
        added.extend([response, result])
        messages.extend([response, result])
    logger.warning("Aftercare agent reached the turn limit for hospital %s", hospital_id)
    raise ValueError("Aftercare agent exceeded the task turn limit")
