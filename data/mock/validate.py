#!/usr/bin/env python3
"""Validate the generated mock dataset (stdlib only).

Checks: primary keys, referential integrity, enum values, business rules
(slot/reservation consistency, demo persona availability), RAG doc front matter,
and a light structural parse of schema.sql + V100__seed.sql.

Usage:
    python3 validate.py [--out out/] [--rag rag_docs/] [--psql "postgresql://..."]
--psql additionally loads schema.sql + V100__seed.sql into that (empty) database with psql.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter
from generate import sample_faq_documents
from seed_extras import SLOT_DAYS, validate_review_translations

HERE = os.path.dirname(os.path.abspath(__file__))
errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


def load(out):
    data = {}
    for fn in sorted(os.listdir(out)):
        if fn.endswith(".json") and not fn.startswith("_"):
            with open(os.path.join(out, fn), encoding="utf-8") as f:
                data[fn[:-5]] = json.load(f)
    with open(os.path.join(out, "_meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    return data, meta


def pk(rows, key="id"):
    ids = [r[key] for r in rows]
    return set(ids), len(ids) == len(set(ids))


def validate_data(d, meta):
    base = dt.date.fromisoformat(meta["base_date"])
    expected = {"users": 14, "hospitals": 50, "procedures": 18, "reservations": 20, "consultations": 2,
                "chat_messages": 6}
    for t, n in expected.items():
        check(len(d[t]) == n, "%s: expected %d rows, got %d" % (t, n, len(d[t])))
    for t in ("ai_tasks", "notifications", "audit_logs", "refresh_tokens"):
        check(d[t] == [], "%s should be empty" % t)
    check(55 <= len(d["glossary"]) <= 70, "glossary size %d" % len(d["glossary"]))

    keys = {}
    for t, rows in d.items():
        if rows:
            k = "code" if t == "procedures" else "id"
            keys[t], unique = pk(rows, k)
            check(unique, "%s: duplicate primary keys" % t)
    H, U, P, D, S = keys["hospitals"], keys["users"], keys["procedures"], keys["doctors"], keys["slots"]
    hosp = {h["id"]: h for h in d["hospitals"]}
    slot = {s["id"]: s for s in d["slots"]}
    doc = {x["id"]: x for x in d["doctors"]}
    user = {u["id"]: u for u in d["users"]}
    proc = {p["code"]: p for p in d["procedures"]}

    # hospitals
    areas = Counter(h["area_code"] for h in d["hospitals"])
    check(areas == Counter(GANGNAM=14, SINSA=10, APGUJEONG=7, CHEONGDAM=5, MYEONGDONG=8, HONGDAE=4, JAMSIL=2),
          "area distribution %s" % dict(areas))
    for h in d["hospitals"]:
        check(h["category"] in ("DERMA", "PLASTIC", "BOTH"), "hospital %d category" % h["id"])
        check(h["supported_languages"][0] == "ko" and set(h["supported_languages"]) <= {"ko", "en", "zh", "ja"},
              "hospital %d languages" % h["id"])
        check(set(h["open_hours"]) == {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}, "hospital %d hours" % h["id"])
        check(re.fullmatch(r"02-0000-\d{4}", h["phone"]) is not None, "hospital %d phone" % h["id"])
    names = [h["name_en"] for h in d["hospitals"]]
    check(len(set(names)) == 50, "hospital names not unique")
    nulls = sum(1 for h in d["hospitals"] if h["verified_at"] is None)
    check(1 <= nulls <= 10, "hospital verified_at nulls = %d" % nulls)
    h1 = hosp[1]
    check(h1["area_code"] == "GANGNAM" and h1["category"] == "BOTH" and
          set(h1["supported_languages"]) >= {"en", "zh", "ja"}, "hospital 1 demo requirements")

    # procedures
    check(Counter(p["category"] for p in d["procedures"]) == Counter(SKIN=10, SURGERY=8), "procedure categories")
    for p in d["procedures"]:
        check(3 <= len(p["synonyms"]) <= 6, "procedure %s synonyms count" % p["code"])

    # users
    roles = Counter(u["role"] for u in d["users"])
    check(roles == Counter(CUSTOMER=7, COUNSELOR=3, HOSPITAL_ADMIN=3, OPERATOR=1), "user roles %s" % dict(roles))
    for u in d["users"]:
        check(u["hospital_id"] is None or u["hospital_id"] in H, "user %d hospital FK" % u["id"])
        check((u["role"] in ("COUNSELOR", "HOSPITAL_ADMIN")) == (u["hospital_id"] is not None),
              "user %d hospital_id vs role" % u["id"])
        check(u["gender"] in ("F", "M", "X") and u["locale"] in ("en", "zh", "ja", "ko"), "user %d enums" % u["id"])
    check(len({u["email"] for u in d["users"]}) == len(d["users"]), "duplicate emails")

    # price options & offered procedures
    offered = {}
    for o in d["price_options"]:
        check(o["hospital_id"] in H, "price_option %d hospital FK" % o["id"])
        check(o["procedure_code"] in P, "price_option %d procedure FK" % o["id"])
        check(o["price_krw"] > 0, "price_option %d price" % o["id"])
        offered.setdefault(o["hospital_id"], set()).add(o["procedure_code"])
    for h in d["hospitals"]:
        codes = offered.get(h["id"], set())
        check(5 <= len(codes) <= 10, "hospital %d offers %d procedures" % (h["id"], len(codes)))
        cats = {proc[c]["category"] for c in codes}
        if h["category"] == "DERMA":
            check(cats == {"SKIN"}, "DERMA hospital %d offers surgery" % h["id"])
        if h["category"] == "PLASTIC":
            n_surg = sum(1 for c in codes if proc[c]["category"] == "SURGERY")
            check(n_surg >= len(codes) / 2, "PLASTIC hospital %d mostly surgery" % h["id"])
    check({"DOUBLE_EYELID_NONINCISION", "JAW_BOTOX"} <= offered[1], "hospital 1 must offer persona procedures")
    per_hp = Counter((o["hospital_id"], o["procedure_code"]) for o in d["price_options"])
    check(all(1 <= v <= 3 for v in per_hp.values()), "1-3 options per hospital/procedure")

    # doctors
    per_h = Counter(x["hospital_id"] for x in d["doctors"])
    for h in d["hospitals"]:
        check(2 <= per_h[h["id"]] <= 4, "hospital %d has %d doctors" % (h["id"], per_h[h["id"]]))
    for x in d["doctors"]:
        check(x["hospital_id"] in H, "doctor %d hospital FK" % x["id"])
        check(set(x["specialties"]) <= offered[x["hospital_id"]], "doctor %d specialty not offered" % x["id"])
        check(set(x["languages"]) <= set(hosp[x["hospital_id"]]["supported_languages"]), "doctor %d langs" % x["id"])

    # slots
    seen = set()
    for s in d["slots"]:
        check(s["hospital_id"] in H, "slot %d hospital FK" % s["id"])
        check(s["doctor_id"] in D and doc[s["doctor_id"]]["hospital_id"] == s["hospital_id"],
              "slot %d doctor FK/hospital mismatch" % s["id"])
        check(s["status"] in ("AVAILABLE", "HELD", "BOOKED"), "slot %d status" % s["id"])
        st = dt.datetime.fromisoformat(s["start_at"])
        check(10 <= st.hour and dt.datetime.fromisoformat(s["end_at"]).hour * 60 +
              dt.datetime.fromisoformat(s["end_at"]).minute <= 18 * 60, "slot %d outside 10-18" % s["id"])
        check(0 <= (st.date() - base).days < SLOT_DAYS, "slot %d outside %d-day window" % (s["id"], SLOT_DAYS))
        check((s["hospital_id"], s["start_at"]) not in seen, "slot %d duplicate time" % s["id"])
        seen.add((s["hospital_id"], s["start_at"]))
        check((s["status"] == "HELD") == (s["hold_expires_at"] is not None), "slot %d hold_expires_at" % s["id"])
    rate = sum(1 for s in d["slots"] if s["status"] != "AVAILABLE") / float(len(d["slots"]))
    check(0.28 <= rate <= 0.5, "booked rate %.2f" % rate)

    # reservations
    active_slots = Counter()
    referenced = set()
    for r in d["reservations"]:
        rid = r["id"]
        check(r["user_id"] in U and user[r["user_id"]]["role"] == "CUSTOMER", "reservation %d user" % rid)
        check(r["hospital_id"] in H and r["slot_id"] in S, "reservation %d FK" % rid)
        s = slot[r["slot_id"]]
        check(s["hospital_id"] == r["hospital_id"], "reservation %d slot hospital mismatch" % rid)
        check(r["procedure_code"] in offered[r["hospital_id"]], "reservation %d procedure not offered" % rid)
        check(r["source"] in ("AI", "DIRECT"), "reservation %d source" % rid)
        check(re.fullmatch(r"[0-9a-f-]{36}", r["idempotency_key"]) is not None, "reservation %d uuid" % rid)
        check(r["decided_by"] is None or user[r["decided_by"]]["hospital_id"] == r["hospital_id"],
              "reservation %d decided_by" % rid)
        expect = {"PENDING": "HELD", "CONFIRMED": "BOOKED", "REJECTED": "AVAILABLE", "CANCELLED": "AVAILABLE"}
        check(s["status"] == expect[r["status"]], "reservation %d (%s) slot status %s" % (rid, r["status"], s["status"]))
        if r["status"] == "PENDING":
            check(r["hold_expires_at"] == s["hold_expires_at"], "reservation %d hold mismatch" % rid)
        if r["status"] in ("PENDING", "CONFIRMED"):
            active_slots[r["slot_id"]] += 1
        if r["status"] == "REJECTED":
            check(bool(r["reject_reason"]) and len(r["alternative_slot_ids"]) >= 1, "reservation %d reject data" % rid)
            for a in r["alternative_slot_ids"]:
                check(a in S and slot[a]["hospital_id"] == r["hospital_id"] and slot[a]["status"] == "AVAILABLE",
                      "reservation %d alternative slot %d" % (rid, a))
        else:
            check(r["alternative_slot_ids"] == [] and r["reject_reason"] is None, "reservation %d stray reject data" % rid)
        check(r["slot_id"] not in referenced, "reservation %d reuses slot" % rid)
        referenced.add(r["slot_id"])
    check(all(v == 1 for v in active_slots.values()), "slot with >1 active reservation")
    held = {s["id"] for s in d["slots"] if s["status"] == "HELD"}
    pending = {r["slot_id"] for r in d["reservations"] if r["status"] == "PENDING"}
    check(held == pending, "HELD slots must equal PENDING reservation slots")
    check(set(Counter(r["status"] for r in d["reservations"])) == {"PENDING", "CONFIRMED", "REJECTED", "CANCELLED"},
          "all reservation statuses present")

    # reviews
    per_h = Counter(r["hospital_id"] for r in d["reviews"])
    for h in d["hospitals"]:
        check(20 <= per_h[h["id"]] <= 320, "hospital %d has %d reviews" % (h["id"], per_h[h["id"]]))
    for r in d["reviews"]:
        check(r["hospital_id"] in H and r["procedure_code"] in offered[r["hospital_id"]], "review %d FK" % r["id"])
        check(1 <= r["rating"] <= 5 and r["age_group"] in ("20s", "30s", "40s", "50s") and
              r["lang"] in ("ko", "en", "zh", "ja") and r["gender"] in ("F", "M", "X"), "review %d enums" % r["id"])
        days = (base - dt.datetime.fromisoformat(r["created_at"]).date()).days
        check(0 < days <= 365, "review %d created_at" % r["id"])
    avg = sum(r["rating"] for r in d["reviews"]) / float(len(d["reviews"]))
    check(3.8 <= avg <= 4.4, "review avg rating %.2f not skewed positive" % avg)

    # conversations / consultations / chat
    conv = {c["id"]: c for c in d["conversations"]}
    cons = {c["id"]: c for c in d["consultations"]}
    for c in d["conversations"]:
        check(c["user_id"] in U and c["consultation_id"] in cons, "conversation %s FK" % c["id"])
    for c in d["consultations"]:
        check(c["hospital_id"] == 1 and c["conversation_id"] in conv, "consultation %d FK" % c["id"])
        check(c["counselor_id"] is None or user[c["counselor_id"]]["role"] == "COUNSELOR", "consultation %d counselor" % c["id"])
    check(Counter(c["status"] for c in d["consultations"]) == Counter(WAITING=1, ACTIVE=1), "consultation statuses")
    for m in d["chat_messages"]:
        check(m["consultation_id"] in cons and m["sender_id"] in U, "chat_message %d FK" % m["id"])
        check({m["original_lang"], m["translated_lang"]} == {"zh", "ko"}, "chat_message %d langs" % m["id"])

    # persona: zh-speaking clinics in Gangnam/Myeongdong with double-eyelid availability for base+1..+7
    cand = [h["id"] for h in d["hospitals"] if h["area_code"] in ("GANGNAM", "MYEONGDONG")
            and "zh" in h["supported_languages"] and any(c.startswith("DOUBLE_EYELID") for c in offered[h["id"]])]
    check(len(cand) >= 3, "persona: only %d candidate hospitals" % len(cand))
    check(any(hosp[c]["area_code"] == "MYEONGDONG" for c in cand), "persona: no Myeongdong candidate")
    for k in range(1, 8):
        day = base + dt.timedelta(days=k)
        n = sum(1 for s in d["slots"] if s["hospital_id"] in cand and s["status"] == "AVAILABLE"
                and dt.datetime.fromisoformat(s["start_at"]).date() == day)
        check(n >= 5, "persona: %s has only %d available slots" % (day, n))
    return cand


# ---------------------------------------------------------------------------


def parse_schema(path):
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    tables = {}
    for m in re.finditer(r"CREATE TABLE app\.(\w+) \((.*?)\n\);", sql, re.S):
        cols = []
        for line in m.group(2).split("\n"):
            tok = line.strip().split()
            if tok and tok[0] not in ("UNIQUE", "CHECK", "PRIMARY", "FOREIGN", "CONSTRAINT"):
                cols.append(tok[0])
        tables[m.group(1)] = cols
    check(sql.count("(") == sql.count(")"), "schema.sql unbalanced parentheses")
    check("CREATE VIEW app.hospital_review_stats" in sql, "schema.sql missing hospital_review_stats view")
    for stmt in ("CREATE SCHEMA IF NOT EXISTS agent;", "CREATE SCHEMA IF NOT EXISTS rag;",
                 "CREATE EXTENSION IF NOT EXISTS vector;", "CREATE TABLE rag.documents (", "CREATE TABLE rag.chunks ("):
        check(stmt in sql, "schema.sql missing: %s" % stmt)
    check("parent_conversation_id" in tables.get("conversations", []), "conversations.parent_conversation_id missing")
    return tables


def validate_sql(out, data):
    tables = parse_schema(os.path.join(out, "schema.sql"))
    for t in data:
        check(t in tables, "schema.sql missing table %s" % t)
    with open(os.path.join(out, "V100__seed.sql"), encoding="utf-8") as f:
        seed = f.read()
    check(seed.count("BEGIN;") == 1 and seed.rstrip().endswith("COMMIT;"), "seed not wrapped in a transaction")
    rows = Counter()
    for m in re.finditer(r"INSERT INTO app\.(\w+) \(([^)]*)\) VALUES\n(.*?);\n", seed, re.S):
        t, cols, body = m.group(1), [c.strip() for c in m.group(2).split(",")], m.group(3)
        check(t in tables, "seed inserts into unknown table %s" % t)
        check(set(cols) <= set(tables.get(t, [])), "seed %s columns not in schema: %s" % (t, set(cols) - set(tables.get(t, []))))
        check(body.count("'") % 2 == 0, "seed %s: unbalanced quotes" % t)
        rows[t] += len(re.findall(r"^\(", body, re.M))
    for t, r in data.items():
        check(rows[t] == len(r), "seed %s: %d rows in SQL vs %d in JSON" % (t, rows[t], len(r)))
    # every statement must end at a line ending with ';' outside of string literals
    check(seed.count("'") % 2 == 0, "seed.sql unbalanced quotes overall")
    return rows


def validate_rag(rag, data):
    want = {"GUIDE": 18, "TRAVEL": 1, "PREP": 1, "AFTERCARE": 1, "FAQ": 1, "HOSPITAL_FAQ": 100}
    expected_samples = sample_faq_documents(data["hospitals"])
    got = Counter()
    ids = set()
    procs = {p["code"] for p in data["procedures"]}
    for root, _, files in os.walk(rag):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                text = f.read()
            m = re.match(r"---\n(.*?)\n---\n", text, re.S)
            check(m is not None, "%s: missing front matter" % fn)
            if not m:
                continue
            fm = dict(line.split(": ", 1) for line in m.group(1).split("\n") if ": " in line)
            for k in ("doc_id", "title", "doc_type", "lang", "source", "version"):
                check(k in fm, "%s: front matter missing %s" % (fn, k))
            is_sample = fm.get("doc_id") in expected_samples
            check(fm.get("lang") == ("ko" if is_sample else "en") and fm.get("version") == "1",
                  "%s: lang/version" % fn)
            check(fm.get("source") == '"SKALA capstone fictional dataset"', "%s: source" % fn)
            check("> Fictional educational content. Not medical advice." in text, "%s: disclaimer" % fn)
            check(fm.get("doc_id") not in ids, "%s: duplicate doc_id" % fn)
            ids.add(fm.get("doc_id"))
            got[fm.get("doc_type")] += 1
            if fm.get("doc_type") == "GUIDE":
                check(fm.get("procedure_code") in procs, "%s: procedure_code" % fn)
                for sec in ("Overview", "How it works", "Procedure steps", "Recovery & downtime",
                            "Common side effects", "Before your visit", "Questions to ask your doctor"):
                    check("\n## %s\n" % sec in text, "%s: missing section %s" % (fn, sec))
            if fm.get("doc_type") == "HOSPITAL_FAQ":
                check(int(fm.get("hospital_id", 0)) in {h["id"] for h in data["hospitals"]}, "%s: hospital_id" % fn)
                if is_sample:
                    check(text == expected_samples[fm["doc_id"]], "%s: FAQ source/metadata mismatch" % fn)
                else:
                    check("slot is held for 30 minutes" in text, "%s: booking policy" % fn)
    check(set(expected_samples) <= ids, "missing supplemental FAQ documents")
    check(got == Counter(want), "rag doc counts %s" % dict(got))
    return got


def load_psql(dsn, out):
    for fn in ("schema.sql", "V100__seed.sql"):
        p = subprocess.run(["psql", dsn, "-v", "ON_ERROR_STOP=1", "-q", "-f", os.path.join(out, fn)],
                           capture_output=True, text=True)
        check(p.returncode == 0, "psql %s failed: %s" % (fn, p.stderr.strip()[:500]))
        if p.returncode:
            return
    p = subprocess.run(["psql", dsn, "-At", "-c",
                        "SELECT hospital_id, review_count, avg_rating FROM app.hospital_review_stats ORDER BY 1 LIMIT 3"],
                       capture_output=True, text=True)
    print("psql load OK; hospital_review_stats sample:", p.stdout.strip().replace("\n", " | "))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--rag", default=os.path.join(HERE, "rag_docs"))
    ap.add_argument("--psql", help="optional DSN of an EMPTY database to load schema+seed into")
    args = ap.parse_args()

    data, meta = load(args.out)
    cand = validate_data(data, meta)
    validate_review_translations(data, check)
    validate_sql(args.out, data)
    docs = validate_rag(args.rag, data)
    if args.psql:
        load_psql(args.psql, args.out)

    print("base_date=%s seed=%s" % (meta["base_date"], meta["seed"]))
    for t in sorted(data):
        print("  %-15s %6d" % (t, len(data[t])))
    print("rag docs:", dict(docs))
    print("persona candidate hospitals (GANGNAM/MYEONGDONG, zh, double eyelid):", cand)
    if errors:
        print("\nFAILED: %d problem(s)" % len(errors))
        for e in errors[:50]:
            print("  -", e)
        sys.exit(1)
    print("\nOK: all checks passed")


if __name__ == "__main__":
    main()
