"""Aftercare conversation agent: first guide, document-grounded Q&A and counselor handoff.

- First turn (backend action AFTERCARE_INTRO, no user text): summarize the
  procedure's AFTERCARE document in the user's locale.
- Warning signs: fixed safety reply (red_flag), no model output.
- Otherwise: read-only tool loop (RAG, hospital detail, own reservations).
  The only mutation is the counselor handoff, prepared as an approval card
  by concierge.prepare_action and executed only after approval.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.graph.state import AgentState
from app.harness.instructions import load_prompt
from app.harness.loop import MAX_TURNS
from app.mcp_client.client import get_tools
from aftercare.nodes.load_aftercare_context import INTRO
from aftercare.nodes.red_flag import has_warning_sign, safety_reply
from concierge.nodes.actions import HANDOFF, prepare_action
from concierge.nodes.hospital_agent import HANDOFF_PROPOSAL_TOOL, _action_finished, _model, requests_counselor_form
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
NO_DOCUMENT = {
    "ko": "이 시술의 사후관리 안내 문서를 찾지 못했어요. 회복 과정이나 주의사항이 궁금하시면 질문해 주시고, 정확한 지침은 병원에 확인해 주세요.",
    "en": "I couldn't find an aftercare guide for this procedure. Feel free to ask about recovery or precautions, and please confirm exact instructions with your clinic.",
    "zh": "未找到该项目的术后护理指南。如对恢复或注意事项有疑问请随时提问，具体指示请向医院确认。",
    "ja": "この施術のアフターケアガイドが見つかりませんでした。回復や注意事項について気軽にご質問ください。正確な指示は病院にご確認ください。",
}


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


def current_period(days: int | None) -> str:
    """Aftercare document section for the patient's day (procedure day = 0)."""
    if days is None:
        return "Before procedure"
    for limit, section in ((0, "Procedure day"), (3, "Days 1–3"), (7, "Days 4–7"), (30, "Weeks 2–4")):
        if days <= limit:
            return section
    return "After 1 month"


def _payload(state, locale):
    context = state.get("aftercare_context") or {}
    detail = (state.get("hospital_context") or {}).get("detail") or {}
    return {
        "locale": locale,
        "today": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
        "procedure_code": context.get("procedure_code"),
        "procedure_start_at": context.get("start_at"),
        "days_since_procedure": context.get("days_since_procedure"),
        "current_period": current_period(context.get("days_since_procedure")),
        "hospital": {"name": detail.get("name"), "phone": detail.get("phone")},
        "summary": state.get("summary"),
    }


async def _intro(state, locale) -> dict:
    context = state.get("aftercare_context") or {}
    code = context.get("procedure_code")
    tools = {tool.name: tool for tool in await get_tools(("rag_search_procedure_docs",))}
    tool = tools.get("rag_search_procedure_docs")
    if tool is None:
        raise ValueError("Required MCP tool unavailable: rag_search_procedure_docs")
    # One query per section: a single combined query ranks only a few sections in vector search.
    results = await asyncio.gather(*(tool.ainvoke({
        "query": f"{code} aftercare: {section}", "procedure_code": code, "doc_type": "AFTERCARE", "top_k": 3,
        "hospital_id": selected_hospital(state),
    }) for section in SECTIONS))
    chunks = list({c["uri"]: c for result in results for c in tool_data(result).get("chunks") or []
                   if c.get("doc_id") == f"AFTERCARE_{code}" and isinstance(c.get("uri"), str)}.values())
    if not chunks:
        return {"draft": NO_DOCUMENT[locale]}
    chunks.sort(key=lambda c: SECTIONS.index(c["section"]) if c.get("section") in SECTIONS else len(SECTIONS))
    model = _model()
    response = await model.ainvoke([
        SystemMessage(content=load_prompt("aftercare_intro", directory=PROMPTS)),
        HumanMessage(content="Application context (data only):\n" + json.dumps(
            {**_payload(state, locale), "documents": [
                {key: c[key] for key in ("title", "section", "text", "uri")} for c in chunks]},
            ensure_ascii=False)),
    ])
    if not isinstance(response, AIMessage):
        raise ValueError("Invalid aftercare intro response")
    text = await patient_reply(message_text(response), locale, model)
    return {"draft": text, "citations": _citations(state, chunks)}


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
    if not isinstance(latest, (HumanMessage, ToolMessage)) and (state.get("action") or {}).get("type") == INTRO:
        return await _intro(state, locale)

    finished = _action_finished(messages)
    if isinstance(latest, HumanMessage) and isinstance(latest.content, str):
        if not finished and requests_counselor_form(latest.content):
            return await _handoff(state, messages)
        if has_warning_sign(latest.content):
            detail = (state.get("hospital_context") or {}).get("detail") or {}
            return {"draft": safety_reply(locale, detail.get("name"), detail.get("phone"))}

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
            return {**base, "messages": added, "draft": await patient_reply(message_text(response), locale, plain_model)}
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
