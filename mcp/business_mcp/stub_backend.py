"""StubBackendClient: data/mock/out/*.json 으로 /internal/** 응답을 흉내 낸다 (USE_STUB=true).

⚠️ backend 규칙 복제 금지. 여기 필터·정렬은 개발용 '근사치'다.
   진짜 검색·예약·일정 계산 규칙은 backend 하나에만 있다 (「시스템 아키텍처」 계층별 금지사항, 「AI Agent 설계」 9-2).
   stub 결과와 backend 결과가 달라도 backend 가 정답.

변경 도구(예약·취소·상담)는 프로세스 메모리에서만 상태를 바꾼다 (재기동하면 초기화).
"""

from __future__ import annotations

import itertools
import json
from datetime import date, datetime, timedelta
from functools import cached_property
from pathlib import Path
from typing import Any

from business_mcp import errors
from business_mcp.context import CallContext
from mcp_common.paths import mock_out_dir


class StubBackendClient:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir or mock_out_dir()
        self._reservation_seq = itertools.count(90001)
        self._consultation_seq = itertools.count(9001)
        self._idempotency: dict[str, dict] = {}

    # --- mock 로딩 ----------------------------------------------------------
    def _load(self, name: str) -> list[dict[str, Any]]:
        return json.loads((self._dir / f"{name}.json").read_text(encoding="utf-8"))

    @cached_property
    def hospitals(self) -> dict[int, dict]:
        return {h["id"]: h for h in self._load("hospitals")}

    @cached_property
    def procedures(self) -> dict[str, dict]:
        return {p["code"]: p for p in self._load("procedures")}

    @cached_property
    def doctors(self) -> list[dict]:
        return self._load("doctors")

    @cached_property
    def price_options(self) -> list[dict]:
        return self._load("price_options")

    @cached_property
    def slots(self) -> dict[int, dict]:
        return {s["id"]: s for s in self._load("slots")}

    @cached_property
    def reviews(self) -> list[dict]:
        return self._load("reviews")

    @cached_property
    def users(self) -> dict[int, dict]:
        return {u["id"]: u for u in self._load("users")}

    @cached_property
    def reservations(self) -> dict[int, dict]:
        return {r["id"]: r for r in self._load("reservations")}

    # --- 공통 헬퍼 -----------------------------------------------------------
    def _locale(self, ctx: CallContext) -> str:
        # backend 와 같은 우선순위 흉내: 파라미터(헤더) → acting user locale → en
        if ctx.locale:
            return ctx.locale
        return self.users.get(ctx.acting_user_id, {}).get("locale", "en")

    @staticmethod
    def _pick(row: dict, field: str, locale: str) -> str | None:
        return row.get(f"{field}_{locale}") or row.get(f"{field}_en") or row.get(f"{field}_ko")

    def _hospital(self, hospital_id: int) -> dict:
        h = self.hospitals.get(hospital_id)
        if h is None:
            raise errors.not_found("Hospital", hospital_id, "Use an id from business_search_hospitals results.")
        return h

    def _check_procedure(self, code: str | None) -> None:
        if code and code not in self.procedures:
            raise errors.unknown_procedure(code, sorted(self.procedures))

    def _doctor_name(self, doctor_id: int | None) -> str | None:
        d = next((d for d in self.doctors if d["id"] == doctor_id), None)
        return d["name_en"] if d else None

    def _slot_dto(self, s: dict) -> dict:
        return {
            "id": s["id"], "start_at": s["start_at"], "end_at": s["end_at"],
            "doctor_id": s["doctor_id"], "doctor_name": self._doctor_name(s["doctor_id"]), "status": s["status"],
        }

    def _price_dto(self, p: dict, locale: str) -> dict:
        return {
            "id": p["id"], "procedure_code": p["procedure_code"], "product": p["product"], "dose": p["dose"],
            "price_krw": p["price_krw"], "vat_included": p["vat_included"],
            "conditions": p.get("conditions_en") if locale != "ko" else p.get("conditions_ko"),
            "verified_at": p["verified_at"],
        }

    def _available_slots(self, hospital_id: int, date_from: str | None, date_to: str | None,
                         doctor_id: int | None = None) -> list[dict]:
        # TODO(mcp): mock 슬롯에는 procedure_code 가 없다. 시술별 소요시간·의사 전문분야 반영은 backend 규칙
        out = []
        for s in self.slots.values():
            if s["hospital_id"] != hospital_id or s["status"] != "AVAILABLE":
                continue
            day = s["start_at"][:10]
            if (date_from and day < date_from) or (date_to and day > date_to):
                continue
            if doctor_id and s["doctor_id"] != doctor_id:
                continue
            out.append(s)
        return sorted(out, key=lambda s: s["start_at"])

    def _card(self, h: dict, locale: str, procedure_code: str | None,
              date_from: str | None, date_to: str | None) -> dict:
        prices = [p for p in self.price_options
                  if p["hospital_id"] == h["id"] and (not procedure_code or p["procedure_code"] == procedure_code)]
        cheapest = min(prices, key=lambda p: p["price_krw"], default=None)
        reviews = [r for r in self.reviews if r["hospital_id"] == h["id"]]
        slots = self._available_slots(h["id"], date_from, date_to)
        return {
            "id": h["id"], "name": self._pick(h, "name", locale), "area_code": h["area_code"],
            "category": h["category"],
            "min_price_krw": cheapest["price_krw"] if cheapest else None,
            "price_verified": bool(cheapest and cheapest["verified_at"]) if cheapest else None,
            "review_count": len(reviews),
            "rating": round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else None,
            "languages": h["supported_languages"], "has_interpreter": h["has_interpreter"],
            "earliest_slot_at": slots[0]["start_at"] if slots else None,
            "distance_km": None,  # TODO(mcp): 거리 정렬은 backend 가 mock 좌표로 계산 (D-21). stub 은 미지원
        }

    # --- 조회 ---------------------------------------------------------------
    async def normalize_procedure(self, ctx, text):
        # 단순 부분 문자열 매칭. TODO(mcp): 실제 동의어·유사도 점수는 backend /internal/procedures/normalize
        q = text.strip().lower()
        locale = self._locale(ctx)
        hits = []
        for p in self.procedures.values():
            names = [p["code"], p["name_ko"], p["name_en"], p.get("name_zh") or "", p.get("name_ja") or "",
                     *p.get("synonyms", [])]
            names = [n.lower() for n in names if n]
            if q in names:
                score = 1.0
            elif any(q in n or n in q for n in names):
                score = 0.7
            else:
                continue
            hits.append({"code": p["code"], "name": self._pick(p, "name", locale), "score": score})
        return {"candidates": sorted(hits, key=lambda c: -c["score"])[:3]}

    async def search_hospitals(self, ctx, params):
        locale = self._locale(ctx)
        code = params.get("procedure_code")
        self._check_procedure(code)
        areas = set(params.get("areas") or [])
        lang = params.get("consult_language")
        budget = params.get("budget_max_krw")
        cards = []
        for h in self.hospitals.values():
            if areas and h["area_code"] not in areas:
                continue
            if lang and lang not in h["supported_languages"]:
                continue
            card = self._card(h, locale, code, params.get("date_from"), params.get("date_to"))
            if code and card["min_price_krw"] is None:
                continue  # 해당 시술을 안 하는 병원
            if budget and card["min_price_krw"] and card["min_price_krw"] > budget:
                continue
            cards.append(card)
        sort_by = params.get("sort_by") or "REVIEW_COUNT"
        key = {
            "REVIEW_COUNT": lambda c: -c["review_count"],
            "RATING": lambda c: -(c["rating"] or 0),
            "PRICE": lambda c: c["min_price_krw"] or 10**12,
        }.get(sort_by, lambda c: -c["review_count"])
        cards.sort(key=key)
        limit = params.get("limit") or 10
        return {"items": cards[:limit], "total": len(cards)}

    async def get_hospital_detail(self, ctx, hospital_id):
        h = self._hospital(hospital_id)
        locale = self._locale(ctx)
        return {
            "id": h["id"], "name": self._pick(h, "name", locale), "name_ko": h["name_ko"],
            "category": h["category"], "area_code": h["area_code"],
            "address": h["address_ko"] if locale == "ko" else h["address_en"], "phone": h["phone"],
            "description": self._pick(h, "description", locale), "open_hours": h["open_hours"],
            "languages": h["supported_languages"], "has_interpreter": h["has_interpreter"],
            "verified_at": h["verified_at"],
        }

    async def list_doctors(self, ctx, hospital_id, procedure_code):
        self._hospital(hospital_id)
        out = []
        for d in self.doctors:
            if d["hospital_id"] != hospital_id:
                continue
            if procedure_code and procedure_code not in d["specialties"]:
                continue
            out.append({"id": d["id"], "name": d["name_en"], "title": d["title"], "specialties": d["specialties"],
                        "languages": d["languages"], "career_years": d["career_years"]})
        return out

    async def get_price_options(self, ctx, hospital_id, procedure_code):
        self._hospital(hospital_id)
        self._check_procedure(procedure_code)
        locale = self._locale(ctx)
        return [self._price_dto(p, locale) for p in self.price_options
                if p["hospital_id"] == hospital_id and p["procedure_code"] == procedure_code]

    async def get_available_slots(self, ctx, hospital_id, procedure_code, date_from, date_to, doctor_id):
        self._hospital(hospital_id)
        self._check_procedure(procedure_code)
        return [self._slot_dto(s) for s in self._available_slots(hospital_id, date_from, date_to, doctor_id)[:20]]

    async def compare_hospitals(self, ctx, hospital_ids, procedure_code):
        self._check_procedure(procedure_code)
        locale = self._locale(ctx)
        columns = []
        for hid in hospital_ids[:3]:
            h = self._hospital(hid)
            card = self._card(h, locale, procedure_code, None, None)
            options = [self._price_dto(p, locale) for p in self.price_options
                       if p["hospital_id"] == hid and p["procedure_code"] == procedure_code]
            columns.append({"hospital": card, "options": options,
                            "earliest_slot_at": card["earliest_slot_at"], "verified_at": h["verified_at"]})
        return {"procedure_code": procedure_code, "columns": columns}

    def _reservation_dto(self, r: dict, locale: str) -> dict:
        h = self.hospitals.get(r["hospital_id"], {})
        slot = self.slots.get(r["slot_id"])
        return {
            "id": r["id"], "status": r["status"], "source": r.get("source"),
            "hospital": {"id": r["hospital_id"], "name": self._pick(h, "name", locale)} if h else None,
            "slot": self._slot_dto(slot) if slot else None, "procedure_code": r["procedure_code"],
            "hold_expires_at": r.get("hold_expires_at"), "reject_reason": r.get("reject_reason"),
            "created_at": r.get("created_at"),
        }

    async def get_my_reservations(self, ctx, status):
        locale = self._locale(ctx)
        return [self._reservation_dto(r, locale) for r in self.reservations.values()
                if r["user_id"] == ctx.acting_user_id and (not status or r["status"] == status)]

    async def plan_trip(self, ctx, body):
        # ⚠️ 근사치. 실제 규칙(TRIP_MIN_BUFFER_DAYS 등)은 backend POST /internal/trip-plans (「AI Agent 설계」 9-2)
        code = body["procedure_code"]
        self._check_procedure(code)
        downtime = self.procedures[code]["downtime_days"]
        arrival, departure = body["arrival_date"], body["departure_date"]
        locale = self._locale(ctx)
        plans = []
        for hid in body["hospital_ids"][:5]:
            h = self._hospital(hid)
            slots = self._available_slots(hid, arrival, departure)
            base = {"hospital_id": hid, "hospital_name": self._pick(h, "name", locale),
                    "procedure_code": code, "downtime_days": downtime}
            if not slots:
                plans.append({**base, "slot": None, "recovery_end_date": None, "buffer_days": None,
                              "feasible": False, "reason": "NO_SLOT_BEFORE_DEPARTURE"})
                continue
            slot = slots[0]
            recovery = date.fromisoformat(slot["start_at"][:10]) + timedelta(days=downtime)
            buffer = (date.fromisoformat(departure) - recovery).days
            feasible = buffer >= 1
            plans.append({**base, "slot": self._slot_dto(slot), "recovery_end_date": recovery.isoformat(),
                          "buffer_days": buffer, "feasible": feasible,
                          "reason": "OK" if feasible else "RECOVERY_AFTER_DEPARTURE"})
        return {"plans": plans}

    # --- 변경 (메모리 내에서만) ----------------------------------------------
    async def create_reservation(self, ctx, body, idempotency_key):
        if idempotency_key in self._idempotency:  # 같은 키 → 기존 결과 그대로 (「공통 계약서」 4장)
            return self._idempotency[idempotency_key]
        self._hospital(body["hospital_id"])
        self._check_procedure(body["procedure_code"])
        slot = self.slots.get(body["slot_id"])
        if slot is None or slot["hospital_id"] != body["hospital_id"]:
            raise errors.not_found("Slot", body["slot_id"], "Use an id from business_get_available_slots results.")
        if slot["status"] != "AVAILABLE":
            alts = self._available_slots(body["hospital_id"], slot["start_at"][:10], None)[:3]
            raise errors.slot_unavailable(slot["id"], alts)
        slot["status"] = "HELD"
        now = datetime.now().astimezone()
        r = {"id": next(self._reservation_seq), "user_id": ctx.acting_user_id, "hospital_id": body["hospital_id"],
             "slot_id": slot["id"], "procedure_code": body["procedure_code"], "status": "PENDING", "source": "AI",
             "hold_expires_at": (now + timedelta(minutes=30)).isoformat(timespec="seconds"),
             "reject_reason": None, "created_at": now.isoformat(timespec="seconds")}
        self.reservations[r["id"]] = r
        result = self._reservation_dto(r, self._locale(ctx))
        self._idempotency[idempotency_key] = result
        return result

    async def cancel_reservation(self, ctx, reservation_id, reason):
        r = self.reservations.get(reservation_id)
        if r is None:
            raise errors.not_found("Reservation", reservation_id, "Use an id from business_get_my_reservations.")
        if r["user_id"] != ctx.acting_user_id:
            raise errors.access_denied()
        if r["status"] not in ("PENDING", "CONFIRMED"):
            raise errors.ToolError(f"Reservation {reservation_id} is {r['status']} and cannot be cancelled.")
        r["status"] = "CANCELLED"
        if slot := self.slots.get(r["slot_id"]):
            slot["status"] = "AVAILABLE"
        return self._reservation_dto(r, self._locale(ctx))

    async def request_consultation(self, ctx, body, idempotency_key):
        if idempotency_key in self._idempotency:
            return self._idempotency[idempotency_key]
        if not body.get("consent"):
            raise errors.ToolError("Customer consent is required before sharing the summary. Ask for approval.")
        h = self._hospital(body["hospital_id"])
        result = {"id": next(self._consultation_seq), "status": "WAITING",
                  "hospital": {"id": h["id"], "name": self._pick(h, "name", self._locale(ctx))},
                  "conversation_id": body.get("conversation_id"),
                  "created_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        self._idempotency[idempotency_key] = result
        return result
