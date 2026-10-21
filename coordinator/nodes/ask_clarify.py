"""One localized question for missing required search fields."""
from app.graph.state import AgentState


def ask_clarify(state: AgentState) -> dict:
    locale = (state.get("user") or {}).get("locale", "en")
    labels = {
        "en": ("procedure", "date", "location (Seoul or a district)"),
        "ko": ("시술", "날짜", "지역(서울 또는 구 단위)"),
        "zh": ("项目", "日期", "地区（首尔或具体区域）"),
        "ja": ("施術", "日付", "地域（ソウルまたは区）"),
    }
    keys = ("procedure_code", "date_from", "areas")
    fields = dict(zip(keys, labels.get(locale, labels["en"])))
    missing = state.get("missing") or []
    text = ", ".join(fields[k] for k in missing if k in fields)
    templates = {"en": "Please specify {fields}.", "ko": "{fields}을 알려주세요.",
                 "zh": "请提供{fields}。", "ja": "{fields}を教えてください。"}
    draft = templates.get(locale, templates["en"]).format(fields=text)
    return {"draft": draft}
