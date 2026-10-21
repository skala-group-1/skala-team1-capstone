"""One localized question for all missing fields; optional filters permit no preference."""
from app.graph.state import AgentState


def ask_clarify(state: AgentState) -> dict:
    locale = (state.get("user") or {}).get("locale", "en")
    labels = {
        "en": ("procedure", "arrival date", "list sort (review count, rating, price or distance)", "maximum budget", "consultation language"),
        "ko": ("시술", "입국일", "정렬 기준(리뷰 수·평점·가격·거리)", "최대 예산", "상담 언어"),
        "zh": ("项目", "入境日期", "排序方式（评论数、评分、价格或距离）", "最高预算", "咨询语言"),
        "ja": ("施術", "入国日", "並び順（口コミ数・評価・価格・距離）", "予算上限", "相談言語"),
    }
    keys = ("procedure_code", "date_from", "sort_by", "budget_max_krw", "consult_language")
    fields = dict(zip(keys, labels.get(locale, labels["en"])))
    missing = state.get("missing") or []
    text = ", ".join(fields[k] for k in missing if k in fields)
    templates = {"en": "Please specify {fields}.", "ko": "{fields}을 알려주세요.",
                 "zh": "请提供{fields}。", "ja": "{fields}を教えてください。"}
    draft = templates.get(locale, templates["en"]).format(fields=text)
    if any(k in missing for k in ("budget_max_krw", "consult_language")):
        optional = {"en": " Budget and consultation language can be ‘no preference’.",
                    "ko": " 예산·상담 언어는 ‘상관없음’도 가능합니다.",
                    "zh": "预算和咨询语言可以选择‘不限’。", "ja": "予算・相談言語は「希望なし」でも構いません。"}
        draft += optional.get(locale, optional["en"])
    return {"draft": draft}
