"""Main-only wrappers over existing Business MCP. No RAG or business writes."""
import json
from datetime import date
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConditionPatch(BaseModel):
    """Only supplied fields replace saved conditions; explicit null clears a filter."""
    model_config = ConfigDict(extra="forbid")
    procedure_code: str | None = Field(default=None, description="User-chosen procedure name or code; verified via normalization before saving. Omit if unchanged.")
    areas: list[Literal["GANGNAM", "SINSA", "APGUJEONG", "CHEONGDAM", "MYEONGDONG", "HONGDAE", "JAMSIL"]] | None = Field(default=None, description="Explicit Seoul districts. Use [] for explicitly requested Seoul-wide search. Omit if no location was given; null clears the location. Never map unsupported places to Seoul.")
    date_from: date | None = None
    date_to: date | None = None
    budget_max_krw: int | None = Field(default=None, ge=0, strict=True, description="Explicit maximum budget in KRW. Omit when unmentioned; null only for explicit no preference.")
    consult_language: Literal["en", "zh", "ja", "ko"] | None = Field(default=None, description="Explicitly requested consultation language: Chinese/중국어=zh, Japanese/일본어=ja, English/영어=en, Korean/한국어=ko. NEVER infer from the language of the message or login locale; omit unless requested.")
    sort_by: Literal["REVIEW_COUNT", "RATING", "PRICE", "DISTANCE"] | None = None

    @model_validator(mode="after")
    def ordered_dates(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("Departure must not precede arrival")
        return self


class LookupArguments(ConditionPatch):
    """Existing Business MCP arguments, visible to the model instead of an opaque dict."""
    text: str | None = None
    language: Literal["en", "zh", "ja", "ko"] | None = None
    hospital_id: int | None = None
    hospital_ids: list[int] | None = None
    status: str | None = None


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

    async def collect(fields):
        action = source.get("action") or {}
        if action.get("type") == "SET_SORT":
            fields = {**fields, "sort_by": action.get("sortBy")}
        saved = results.get("conditions", source.get("conditions") or {})
        procedure = fields.pop("procedure_code", saved.get("procedure_code"))
        # Persist independent filters even if normalization subsequently fails.
        conditions = ConditionPatch.model_validate({**saved, **fields}).model_dump(mode="json", exclude_unset=True)
        conditions["sort_by"] = conditions.get("sort_by") or "REVIEW_COUNT"
        if conditions != saved:
            results.update({"hospitals": [], "summary": None, "selected_hospital_id": None})
        results["conditions"] = conditions
        if procedure != saved.get("procedure_code"):
            conditions.pop("procedure_code", None)
            if procedure is not None and not results.get("ambiguity"):
                normalized = results.get("normalization", {}).get("candidates", [])
                exact = [c for c in normalized if c.get("score") == 1 and c.get("code") == procedure]
                if len(exact) != 1:
                    normalized = (await hospital_lookup.ainvoke({"operation": "normalize",
                                                               "arguments": {"text": procedure}})).get("candidates", [])
                    exact = [c for c in normalized if c.get("score") == 1]
                if len(exact) == 1 and not results.get("ambiguity"):
                    conditions["procedure_code"] = exact[0]["code"]
            elif procedure is None:
                conditions["procedure_code"] = None
            results.update({"hospitals": [], "summary": None, "selected_hospital_id": None})
        missing = [k for k in ("procedure_code", "date_from") if not conditions.get(k)]
        # [] means explicit Seoul-wide search; missing/null means location unknown.
        if conditions.get("areas") is None:
            missing.append("areas")
        results["missing"] = missing
        response = {"status": "needs_input" if missing else "ready", "conditions": conditions, "missing": missing}
        if procedure and not conditions.get("procedure_code"):
            response["normalization"] = {"candidates": results["ambiguity"]} if results.get("ambiguity") else results.get("normalization", {})
            response["message"] = ("Procedure not resolved. If no candidates matched the phrase, call "
                "hospital_lookup normalize with a concise synonym or translated name, then collect its verified code. "
                "If multiple candidates match, ask the user; never choose for them.")
        return response

    @tool
    async def collect_conditions(fields: ConditionPatch):
        """Save only explicitly supplied Conditions, before asking or searching.

        Supply the user's procedure phrase or a normalized code; it is verified
        through Business MCP before saving. Omitted fields retain previous values;
        explicit null clears a filter. Ask only returned missing required fields.
        Location, procedure and date are required. Budget, consultation language
        and sorting are optional; search immediately when required fields are ready.
        """
        return await collect(fields.model_dump(mode="json", exclude_unset=True))

    @tool
    async def procedure_consultation(question: str):
        """Tool A: general procedure information requires external evidence.

        No external provider is connected. Do not replace evidence with model memory.
        """
        return {"status": "external_search_unavailable", "message":
                "External evidence search is not connected. Do not provide medical facts or benefit examples."}

    @tool
    async def hospital_lookup(operation: Literal["normalize", "search", "reservations", "hours", "slots", "compare", "prepare_handoff"], arguments: LookupArguments):
        """Tool B: reuse Business MCP. Use existing snake_case schemas only.

        normalize takes text. search requires procedure_code, date_from and areas
        ([] for explicit Seoul-wide search). Optional date_to, budget_max_krw,
        language and sort_by; omitted sort defaults to REVIEW_COUNT. Maximum five.
        No pagination. Never relax explicitly supplied filters.
        hours takes hospital_id. slots takes hospital_id, procedure_code, date_from,
        date_to. reservations takes optional status. prepare_handoff takes only
        hospital_id explicitly chosen from the displayed list; it creates an unsent
        brief only. compare takes hospital_ids (1–3 displayed IDs) and uses the saved procedure.
        No booking or hospital conversation is created.
        """
        nonlocal loaded
        args = arguments.model_dump(mode="json", exclude_unset=True)
        if operation == "normalize":
            # Both intake and normalization accept a procedure phrase; MCP calls it text.
            args = {"text": args.get("text") or args.get("procedure_code")}
        if operation == "prepare_handoff":
            results.update({"summary": None, "selected_hospital_id": None})
            prepared = prepare_handoff_summary(source, args.get("hospital_id"),
                results.get("hospitals", source.get("candidates", [])),
                results.get("conditions", source.get("conditions", {})))
            if prepared["status"] == "summary_ready":
                results["evidence"] = operation
                results.update({k: prepared[k] for k in ("summary", "selected_hospital_id")})
            return prepared
        if operation == "search":
            results.update({"hospitals": [], "summary": None, "selected_hospital_id": None})
            if "language" in args:
                args["consult_language"] = args.pop("language")
            collected = await collect(args)
            if collected["missing"]:
                return collected
            args = {("language" if k == "consult_language" else k): v
                    for k, v in collected["conditions"].items() if v is not None}
            args["limit"] = 5
        if operation == "compare":
            ids = args.get("hospital_ids", [])
            candidates = results.get("hospitals", source.get("candidates") or [])
            if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or any(
                    type(i) is not int or i not in [h["id"] for h in candidates] for i in ids):
                return {"status": "invalid_selection"}
            procedure = results.get("conditions", source.get("conditions") or {}).get("procedure_code")
            if not procedure:
                return {"status": "needs_input", "missing": ["procedure_code"]}
            args = {"hospital_ids": ids, "procedure_code": procedure}
        if loaded is None:
            loaded = {t.name: t for t in await loader()}
        names = {"normalize": "business_normalize_procedure", "search": "business_search_hospitals",
                 "reservations": "business_get_my_reservations", "hours": "business_get_hospital_detail",
                 "slots": "business_get_available_slots", "compare": "business_compare_hospitals"}
        target = loaded.get(names[operation])
        if target is None:
            raise ValueError("Required Business MCP tool unavailable")
        result = decode_result(await target.ainvoke(args))
        if result.get("status") in ("unavailable", "error") or result.get("isError"):
            raise ValueError("Business lookup failed")
        if operation == "normalize":
            results["normalization"] = result
            candidates = result.get("candidates", [])
            if len(candidates) > 1 and len([c for c in candidates if c.get("score") == 1]) != 1:
                # Only a new user turn may resolve an ambiguous procedure choice.
                results["ambiguity"] = candidates
        else:
            results["evidence"] = operation
        if operation == "hours":
            return {k: result[k] for k in ("id", "name", "open_hours", "verified_at") if k in result}
        if operation == "search":
            result["hospitals"] = result.get("hospitals", [])[:5]
            results["hospitals"] = result["hospitals"]
        return result

    return [procedure_consultation, hospital_lookup, collect_conditions], results
