"""Localized approval labels; only tool/service facts become displayed values."""

import re

# Display vocabulary only; these labels do not assert a hospital offers a procedure.
PROCEDURES = {
    "JAW_BOTOX": ("jaw Botox", "사각턱 보톡스", "瘦脸针", "エラボトックス"),
    "FOREHEAD_BOTOX": ("forehead Botox", "이마 보톡스", "额头肉毒素", "額ボトックス"),
    "LIP_FILLER": ("lip filler", "입술 필러", "唇部填充", "唇フィラー"),
    "NOSE_FILLER": ("nose filler", "코 필러", "鼻部填充", "鼻フィラー"),
    "REJURAN": ("Rejuran", "리쥬란", "丽珠兰", "リジュラン"),
    "ULTHERAPY": ("Ultherapy", "울쎄라", "Ultherapy", "ウルセラ"),
    "SHURINK": ("Shurink", "슈링크", "Shurink", "シュリンク"),
    "DOUBLE_EYELID_NONINCISION": ("non-incisional double eyelid", "비절개 쌍꺼풀", "埋线双眼皮", "二重埋没法"),
    "DOUBLE_EYELID_INCISION": ("incisional double eyelid", "절개 쌍꺼풀", "切开双眼皮", "二重切開法"),
    "PTOSIS_CORRECTION": ("ptosis correction", "눈매교정", "上睑下垂矫正", "眼瞼下垂手術"),
    "RHINOPLASTY": ("rhinoplasty", "코 성형", "鼻整形", "鼻整形"),
}
TEXT = {
    "hospital": ("Hospital", "병원", "医院", "病院"),
    "procedure": ("Procedure", "시술", "项目", "施術"),
    "doctor": ("Doctor", "의사", "医生", "医師"),
    "time": ("Time (Korea)", "일시 (한국)", "时间（韩国）", "日時（韓国）"),
    "price": ("Price", "가격", "价格", "料金"),
    "product": ("Product / dose", "제품 / 용량", "产品 / 剂量", "製品 / 用量"),
    "vat": ("VAT", "부가세", "增值税", "付加価値税"),
    "included": ("Included", "포함", "包含", "込み"),
    "excluded": ("Not included", "별도", "不含", "別途"),
    "conditions": ("Price conditions", "가격 조건", "价格条件", "料金条件"),
    "verified": ("Price verified", "가격 확인일", "价格核实日期", "料金確認日"),
    "unknown": ("Needs confirmation", "확인 필요", "待确认", "要確認"),
    "note": ("Note", "메모", "备注", "メモ"),
    "reason": ("Reason", "취소 사유", "取消原因", "キャンセル理由"),
    "preferred_dates": ("Preferred dates", "희망 일정", "希望日期", "希望日程"),
    "stay_days": ("Stay (days)", "체류일 수", "停留天数", "滞在日数"),
    "budget": ("Budget", "예산", "预算", "予算"),
    "questions": ("Questions", "질문", "问题", "質問"),
    "customer_locale": ("Customer language", "고객 언어", "客户语言", "お客様の言語"),
    "en": ("English", "영어", "英语", "英語"),
    "ko": ("Korean", "한국어", "韩语", "韓国語"),
    "zh": ("Chinese", "중국어", "中文", "中国語"),
    "ja": ("Japanese", "일본어", "日语", "日本語"),
    "book": ("Reservation request", "예약 요청", "预约申请", "予約リクエスト"),
    "cancel": ("Cancel reservation", "예약 취소", "取消预约", "予約キャンセル"),
    "handoff": ("Review summary and consent", "요약 확인 및 공유 동의", "核对摘要并同意分享", "要約の確認と共有への同意"),
    "booking_notice": ("This requests a reservation; hospital approval is still required.",
        "예약 요청이며 병원 승인이 필요합니다.", "这是预约申请，仍需医院批准。", "予約リクエストです。病院の承認が必要です。"),
    "cancel_notice": ("Approve to cancel this reservation.", "승인하면 이 예약을 취소합니다.",
                      "批准后将取消此预约。", "承認するとこの予約をキャンセルします。"),
    "consent_notice": ("Check the summary. Approval consents to sharing it with this hospital and requesting a human counselor.",
        "요약을 확인해 주세요. 승인하면 이 요약을 선택한 병원에 제공하고 상담사 연결을 요청하는 데 동의합니다.",
        "请核对摘要。批准即同意向所选医院分享此摘要并申请人工咨询。",
        "要約を確認してください。承認すると、選択した病院への要約の共有と相談員への接続依頼に同意します。"),
}


def label(key, locale):
    return TEXT[key][("en", "ko", "zh", "ja").index(locale if locale in ("en", "ko", "zh", "ja") else "en")]


def procedure_name(value, locale):
    index = ("en", "ko", "zh", "ja").index(locale if locale in ("en", "ko", "zh", "ja") else "en")
    if value in PROCEDURES:
        return PROCEDURES[value][index]
    # Summarizer appends the code in parentheses to an already localized name.
    value = re.sub(r"\s*\([A-Z]+(?:_[A-Z]+)+\)", "", value or "")
    return label("unknown", locale) if re.search(r"\b[A-Z]+(?:_[A-Z]+)+\b", value) else value


def row(key, value, locale):
    return {"label": label(key, locale), "value": str(value) if value is not None and value != "" else label("unknown", locale)}


def price_rows(price, locale):
    if not price:
        return [row("price", None, locale)]
    return [row("price", f"{price['price_krw']:,} KRW", locale),
            row("product", " / ".join(str(price[k]) for k in ("product", "dose") if price.get(k)), locale),
            row("vat", label("included" if price["vat_included"] else "excluded", locale), locale),
            row("conditions", price.get("conditions"), locale),
            row("verified", price.get("verified_at"), locale)]


def summary_rows(card, locale):
    return [row("procedure", procedure_name(card.get("procedure"), locale), locale),
            *[row(key, card.get(key), locale) for key in ("preferred_dates", "stay_days", "budget")],
            row("customer_locale", label(card["customer_locale"], locale)
                if card.get("customer_locale") in ("en", "ko", "zh", "ja") else None, locale),
            row("questions", "\n".join(card.get("questions") or []), locale)]
