"""Deterministic warning-sign check for aftercare messages.

This is a safety net, not a diagnosis: when a patient mentions a possible
warning sign, the reply is a fixed message that points to the clinic and
emergency services and offers a counselor connection. No model output is used.
"""

import re

# Common warning signs from the aftercare documents, in ko/en/zh/ja.
_PATTERNS = [
    # heavy bleeding
    r"피가?\s*(?:계속|많이|안\s*멈|멈추지)|출혈이?\s*(?:심|계속|많|안\s*멈)",
    r"\b(?:heavy|a lot of|won'?t stop|not stopping|keeps?)\b[^.!?]{0,20}\bbleed|\bbleeding\b[^.!?]{0,20}\b(?:heavy|won'?t stop|not stop|a lot)",
    r"出血(?:不止|很多|严重|止不住)|大出血|血(?:止不住|流不止)",
    r"出血が(?:止まらない|多い|ひどい)|血が止まらない",
    # fever
    r"열이\s*(?:나|있|높)|고열|발열|오한",
    r"\bfever\b|\bchills\b|\bhigh temperature\b",
    r"发烧|发热|高烧|发冷",
    r"熱が(?:あ|出|高)|発熱|高熱|悪寒",
    # breathing / chest
    r"숨\s*(?:쉬기|이)\s*(?:힘들|어렵|차)|호흡\s*곤란|가슴\s*(?:이\s*)?(?:통증|아프|답답)",
    r"\b(?:can'?t|cannot|hard to|difficulty|trouble)\s+breath|\bshort(?:ness)? of breath\b|\bchest pain\b",
    r"呼吸困难|喘不过气|胸痛|胸口疼",
    r"息(?:が)?(?:苦しい|できない)|呼吸困難|胸(?:が|の)?痛",
    # vision
    r"(?:눈이|앞이)\s*(?:안\s*보|흐릿|침침)|시야|시력",
    r"\b(?:blurr(?:y|ed) vision|vision (?:loss|change|problem)|can'?t see|double vision)\b",
    r"视力|看不清|视线模糊|重影",
    r"視力|見えにくい|目がかすむ|ものが二重",
    # skin colour change after fillers, severe or worsening pain
    r"(?:피부|입술|코)[^.!?\n]{0,10}(?:하얗|창백|파랗|보라|검게|얼룩)|극심한\s*통증|통증이\s*(?:점점|계속)\s*(?:심|더)",
    r"\b(?:pale|white|grey|gray|blue|purple|mottled)\s+(?:skin|patch|lips?)\b|\b(?:severe|unbearable|worsening|extreme) pain\b",
    r"皮肤(?:发白|发紫|发青|变色)|剧痛|疼得厉害|越来越疼",
    r"皮膚が(?:白|紫|青)|激痛|痛みがひどい|どんどん痛",
    # severe allergy / one-sided swelling
    r"목이\s*(?:붓|부어)|얼굴이\s*갑자기\s*(?:붓|부어)|한쪽만\s*(?:갑자기\s*)?(?:많이\s*)?(?:붓|부어)",
    r"\b(?:throat|tongue) (?:swelling|is swelling|swollen)\b|\bsudden(?:ly)? swollen\b",
    r"喉咙肿|嗓子肿|突然肿",
    r"喉が腫れ|急に腫れ",
]
_WARNING = re.compile("|".join(f"(?:{p})" for p in _PATTERNS), re.IGNORECASE)
_NEGATION = re.compile(
    r"\b(?:no|not|without|don'?t have)\s+(?:a\s+)?(?:fever|bleeding|pain)\b|열은?\s*없|출혈은?\s*없|没有(?:发烧|出血)|熱はない|出血はない",
    re.IGNORECASE,
)

SAFETY_REPLY = {
    "ko": ("말씀하신 증상은 바로 확인이 필요한 신호일 수 있어요. 저는 의학적 판단을 할 수 없으니 "
           "{hospital}{phone}에 바로 연락해 주세요. 숨쉬기 힘들거나 출혈이 멈추지 않거나 시야에 변화가 있으면 "
           "즉시 119에 전화하거나 가까운 응급실로 가세요.\n\n"
           "원하시면 병원 상담사를 연결해 드릴게요. \"상담사 연결해 주세요\"라고 말씀해 주세요."),
    "en": ("The symptom you described may need to be checked right away. I can't make a medical judgment, "
           "so please contact {hospital}{phone} now. If you have trouble breathing, bleeding that won't stop, "
           "or any change in vision, call 119 or go to the nearest emergency room immediately.\n\n"
           "If you'd like, I can connect you with a counselor at the hospital. Just say \"Connect me to a counselor.\""),
    "zh": ("您描述的症状可能需要立即检查。我无法做出医疗判断，请立即联系{hospital}{phone}。"
           "如果出现呼吸困难、出血不止或视力变化，请立即拨打119或前往最近的急诊室。\n\n"
           "如有需要，我可以为您联系医院的咨询师。请说“请帮我联系咨询师”。"),
    "ja": ("お伝えいただいた症状はすぐに確認が必要なサインかもしれません。医学的な判断はできませんので、"
           "すぐに{hospital}{phone}へご連絡ください。呼吸が苦しい、出血が止まらない、視力に変化がある場合は、"
           "すぐに119番に電話するか、最寄りの救急外来を受診してください。\n\n"
           "ご希望であれば病院の相談員におつなぎします。「相談員につないでください」とお伝えください。"),
}
_PHONE = {"ko": " ({phone})", "en": " ({phone})", "zh": "（{phone}）", "ja": "（{phone}）"}
_CLINIC = {"ko": "시술받은 병원", "en": "your clinic", "zh": "您做手术的医院", "ja": "施術を受けた病院"}


def has_warning_sign(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    if _NEGATION.search(text) and not _WARNING.search(_NEGATION.sub(" ", text)):
        return False
    return bool(_WARNING.search(text))


def safety_reply(locale: str, hospital_name: str | None, phone: str | None) -> str:
    locale = locale if locale in SAFETY_REPLY else "en"
    phone_text = _PHONE[locale].format(phone=phone) if phone else ""
    return SAFETY_REPLY[locale].format(hospital=hospital_name or _CLINIC[locale], phone=phone_text)
