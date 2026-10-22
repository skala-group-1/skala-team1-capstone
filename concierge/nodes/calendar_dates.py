"""Calendar hints for Korean relative dates; ambiguous month weeks need confirmation."""
import calendar
import re
from datetime import date, timedelta


def request_calendar(text: str, today: date) -> dict:
    """Never derive dates from an AI answer or an older user turn."""
    if re.search(r"말고|아니|제외", text):
        return {}
    iso = re.findall(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)", text)
    korean = re.search(r"(?:(\d{4})년\s*)?(\d{1,2})월\s*(\d{1,2})일(?:\s*(?:부터|~|∼|–|에서)\s*(?:(\d{1,2})월\s*)?(\d{1,2})일?\s*까지)?", text)
    try:
        if iso and len(iso) <= 2:
            start, end = date.fromisoformat(iso[0]), date.fromisoformat(iso[-1])
        elif korean:
            year, month = int(korean[1] or today.year), int(korean[2])
            if korean[1] is None and month < today.month:
                return {"clarify": True, "ranges": []}
            start = date(year, month, int(korean[3]))
            end = date(year, int(korean[4] or month), int(korean[5] or korean[3]))
            # Multiple separately specified dates need a confirmed range/list.
            if re.search(r"\d{1,2}월\s*\d{1,2}일", text[korean.end():]):
                return {}
        else:
            start = end = None
        if start:
            if start > end:
                return {"clarify": True, "ranges": []}
            return {"date_from": start.isoformat(), "date_to": end.isoformat()}
    except ValueError:
        return {"clarify": True, "ranges": []}
    week = re.search(r"(?:(\d{4})년\s*)?(\d{1,2})월\s*(첫째|첫|둘째|두\s*번째|셋째|세\s*번째|넷째|네\s*번째|다섯째|[1-5])\s*주", text)
    if week:
        year, month = int(week[1] or today.year), int(week[2])
        order = re.sub(r"\s", "", week[3])
        number = {"첫": 1, "첫째": 1, "둘째": 2, "두번째": 2, "셋째": 3,
                  "세번째": 3, "넷째": 4, "네번째": 4, "다섯째": 5}.get(order)
        number = number or int(order)
        if not 1 <= month <= 12 or not 1 <= year <= 9998:
            return {"clarify": True, "ranges": []}
        # A missing year in a past month is not silently changed to next year.
        if week[1] is None and month < today.month:
            return {"clarify": True, "ranges": []}
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        starts = [first - timedelta(days=first.weekday()) + timedelta(weeks=number - 1),
                  first + timedelta(days=(-first.weekday()) % 7, weeks=number - 1),
                  first + timedelta(days=7 * (number - 1))]
        ranges = sorted({(max(start, first).isoformat(), min(start + timedelta(days=6), last).isoformat())
                         for start in starts if start <= last and start + timedelta(days=6) >= first})
        return {"clarify": True, "ranges": ranges}
    # Compound/negated expressions need model clarification instead of a guessed override.
    if re.search(r"말고|아니|제외|또는|이나|부터|까지|[월화수목금토일]요일|주말", text):
        return {}
    matches = list(re.finditer(r"다다음\s*주|다음\s*주|이번\s*주|모레|내일|오늘", text))
    if len(matches) != 1:
        return {}
    phrase = re.sub(r"\s", "", matches[0].group())
    if phrase in ("오늘", "내일", "모레"):
        start = end = today + timedelta(days={"오늘": 0, "내일": 1, "모레": 2}[phrase])
    else:
        start = today - timedelta(days=today.weekday()) + timedelta(weeks={"이번주": 0, "다음주": 1, "다다음주": 2}[phrase])
        end = start + timedelta(days=6)
    return {"date_from": start.isoformat(), "date_to": end.isoformat()}


def clarification(scope: dict, locale: str) -> str:
    texts = {
        "ko": "날짜 범위를 정확히 확인하고 싶어요. 원하시는 연도와 시작일과 종료일을 알려주세요. 주차 표현은 기준에 따라 날짜가 달라질 수 있어요.",
        "en": "Week-of-month conventions differ. Please confirm the exact start and end dates you want.",
        "ja": "月の週の数え方によって日付が異なります。ご希望の開始日と終了日を確認させてください。",
        "zh": "每月周次的计算方式不同，请确认您希望查询的具体开始和结束日期。",
    }
    ranges = scope.get("ranges") or []
    return texts.get(locale, texts["en"]) + ("\n" + "\n".join(f"- {a} ~ {b}" for a, b in ranges) if ranges else "")


def validate_slot_dates(args: dict, scope: dict) -> None:
    if scope.get("clarify"):
        raise ValueError("Confirm exact start/end dates with the patient before a week-of-month lookup")
    try:
        start, end = (date.fromisoformat(args[key]) for key in ("date_from", "date_to"))
    except (KeyError, TypeError, ValueError):
        raise ValueError("Slot lookup requires valid YYYY-MM-DD date_from and date_to") from None
    if start > end:
        raise ValueError("Slot lookup end date must not precede start date")
    if scope.get("date_from") and (start.isoformat(), end.isoformat()) != (scope["date_from"], scope["date_to"]):
        raise ValueError(f"Use the calendar-resolved date range {scope['date_from']} through {scope['date_to']}; do not substitute another week")


def availability_only(text: str) -> bool:
    if re.search(r"예약해|예약해줘|예약해\s*주|예약\s*접수|승인|예약\s*폼|book\b|reserve\b|approval|予約して|预约", text, re.I):
        return False
    return bool(re.search(r"시간|슬롯|조회|availability|available|空き|空闲", text, re.I))


def slot_reply(args: dict, data: dict, locale: str) -> str:
    """Render verified availability directly so dates cannot drift in copy editing."""
    phrases = {
        "ko": ("조회 기간 (한국 시간)", "조회된 예약 가능 시간", "조회 결과에 표시된 시간이며 전체 예약 가능 시간 목록은 아닐 수 있습니다.",
               "이 기간과 조회 조건에 맞는 예약 가능 시간이 반환되지 않았습니다. 다른 기간을 확인할까요?"),
        "en": ("Search dates (Korea time)", "Available times returned", "These are the returned results and may not include every available appointment.",
               "No available times were returned for these dates and filters. Would you like to check another range?"),
        "ja": ("検索期間（韓国時間）", "取得した予約可能時間", "取得した結果です。すべての予約可能時間を含むとは限りません。",
               "この期間と条件に合う予約可能時間は返されませんでした。別の期間を確認しますか？"),
        "zh": ("查询日期（韩国时间）", "查询到的可预约时间", "以下为返回的查询结果，可能未包含全部可预约时段。",
               "此日期范围和筛选条件下没有返回可预约时段。是否查询其他日期？"),
    }
    title, heading, notice, empty = phrases.get(locale, phrases["en"])
    result = f"{title}: {args['date_from']} ~ {args['date_to']}\n\n"
    slots = data.get("slots") or []
    if not slots:
        return result + empty
    from zoneinfo import ZoneInfo
    from datetime import datetime
    lines = []
    for slot in slots:
        start = datetime.fromisoformat(slot["start_at"]).astimezone(ZoneInfo("Asia/Seoul"))
        end = datetime.fromisoformat(slot["end_at"]).astimezone(ZoneInfo("Asia/Seoul"))
        finish = end.strftime("%H:%M") if end.date() == start.date() else end.strftime("%Y-%m-%d %H:%M")
        doctor = f" ({slot['doctor_name']})" if slot.get("doctor_name") else ""
        lines.append(f"- {start:%Y-%m-%d %H:%M}–{finish}{doctor}")
    return result + heading + ":\n" + "\n".join(lines) + "\n\n" + notice
