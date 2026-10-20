"""Main-only wrappers over existing Business MCP. No RAG or business writes."""
import json
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool


async def load_business_tools():
    from app.mcp_client.client import get_client
    return await get_client().get_tools(server_name="business")


def decode_result(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    for block in value if isinstance(value, list) else []:
        if isinstance(block, dict) and block.get("type") == "text":
            return json.loads(block["text"])
    raise ValueError("Expected structured Business MCP JSON")


def prepare_handoff_summary(state, hospital_id, candidates, conditions):
    """Draft only. User statements remain verbatim, not clinical facts."""
    hospital = next((h for h in candidates if type(hospital_id) is int and h.get("id") == hospital_id), None)
    if hospital is None:
        return {"status": "invalid_selection", "message": "Select from the current displayed hospitals."}
    locale = (state.get("user") or {}).get("locale") or "en"
    labels = {
        "en": ("Handoff draft — not sent", "Selected hospital", "Saved language", "Search conditions",
               "User statements (unverified, original language)", "Not confirmed", "Hours and availability need confirmation. No conversation or booking created."),
        "zh": ("交接摘要草稿——尚未发送", "所选医院", "设置语言", "搜索条件", "用户陈述（未核实，原文）", "未确认", "营业时间和预约时段仍需确认；未创建对话或预约。"),
        "ja": ("引き継ぎ用下書き・未送信", "選択した病院", "設定言語", "検索条件", "利用者の発言（未確認・原文）", "未確認", "営業時間と予約枠は確認が必要です。会話や予約は作成していません。"),
        "ko": ("인계 요약 초안 — 미전송", "선택 병원", "설정 언어", "검색 조건", "사용자 발언 (미검증 원문)", "미확인", "영업시간·예약 가능 여부 추가 확인 필요. 대화·예약 생성 안 함."),
    }
    title, selected, language, filters, statements, unknown, caveat = labels.get(locale, labels["en"])
    quotes = [str(m.content) for m in state.get("messages", []) if isinstance(m, HumanMessage)]
    summary = "\n".join([title, f"{selected}: {hospital.get('name') or unknown} (ID: {hospital_id})",
        f"{language}: {locale}", f"{filters}: {json.dumps(conditions, ensure_ascii=False, sort_keys=True)}",
        f"{statements}:\n" + ("\n".join(f"- {q}" for q in quotes) or unknown), caveat])
    return {"status": "summary_ready", "summary": summary, "selected_hospital_id": hospital_id}


def make_coordinator_tools(business_loader=None, *, initial_state=None):
    loader = business_loader or load_business_tools
    source = initial_state if initial_state is not None else {}
    loaded = None
    results = {}

    @tool
    async def procedure_consultation(question: str):
        """Tool A: general procedure information requires external evidence.

        No external provider is connected. Do not replace evidence with model memory.
        """
        return {"status": "external_search_unavailable", "message":
                "External evidence search is not connected. Do not provide medical facts or benefit examples."}

    @tool
    async def hospital_lookup(operation: Literal["normalize", "search", "reservations", "hours", "slots", "prepare_handoff"], arguments: dict):
        """Tool B: reuse Business MCP. Use existing snake_case schemas only.

        normalize takes text. search requires procedure_code, date_from and user-
        selected sort_by (PRICE/REVIEW_COUNT/RATING/DISTANCE); optional date_to,
        areas, budget_max_krw, language. Maximum five. No pagination. Never relax.
        hours takes hospital_id. slots takes hospital_id, procedure_code, date_from,
        date_to. reservations takes optional status. prepare_handoff takes only
        hospital_id explicitly chosen from the displayed list; it creates an unsent
        brief only. No booking or hospital conversation is created.
        """
        nonlocal loaded
        args = dict(arguments)
        if operation == "prepare_handoff":
            results.update({"summary": None, "selected_hospital_id": None})
            prepared = prepare_handoff_summary(source, args.get("hospital_id"),
                results.get("hospitals", source.get("candidates", [])),
                results.get("conditions", source.get("conditions", {})))
            if prepared["status"] == "summary_ready":
                results.update({k: prepared[k] for k in ("summary", "selected_hospital_id")})
            return prepared
        if operation == "search":
            results.update({"hospitals": [], "summary": None, "selected_hospital_id": None})
            missing = [k for k in ("procedure_code", "date_from", "sort_by") if not args.get(k)]
            if missing:
                return {"status": "needs_input", "missing": missing}
            args["limit"] = 5
        if loaded is None:
            loaded = {t.name: t for t in await loader()}
        names = {"normalize": "business_normalize_procedure", "search": "business_search_hospitals",
                 "reservations": "business_get_my_reservations", "hours": "business_get_hospital_detail",
                 "slots": "business_get_available_slots"}
        target = loaded.get(names[operation])
        if target is None:
            return {"status": "unavailable", "message": "Required Business MCP tool unavailable."}
        result = decode_result(await target.ainvoke(args))
        if operation == "hours":
            return {k: result[k] for k in ("id", "name", "open_hours", "verified_at") if k in result}
        if operation == "search":
            result["hospitals"] = result.get("hospitals", [])[:5]
            results["hospitals"] = result["hospitals"]
            results["conditions"] = {("consult_language" if k == "language" else k): v for k, v in args.items() if k != "limit"}
        return result

    return [procedure_consultation, hospital_lookup], results
