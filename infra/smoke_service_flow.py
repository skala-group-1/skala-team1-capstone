"""Live frontend proxy → backend → queue → agent → MCP smoke check (stdlib only)."""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request


def sse_events(lines):
    event = {}
    data = []
    for raw in lines:
        line = raw.decode().rstrip("\r\n")
        if not line:
            if data:
                yield {**event, "data": json.loads("\n".join(data))}
            event, data = {}, []
        elif not line.startswith(":"):
            key, _, value = line.partition(":")
            value = value.removeprefix(" ")
            if key == "data":
                data.append(value)
            else:
                event[key] = value


def main():
    base = os.environ.get("SMOKE_BASE_URL", "http://localhost").rstrip("/")
    email, password = os.environ["SMOKE_EMAIL"], os.environ["SMOKE_PASSWORD"]
    token = None

    def request(path, body=None, stream=False):
        headers = {"Content-Type": "application/json", "Accept-Language": "zh"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if stream:
            headers["Accept"] = "text/event-stream"
        return urllib.request.urlopen(urllib.request.Request(
            base + "/api" + path, headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        ), timeout=150 if stream else 20)

    def call(path, body=None):
        with request(path, body) as response:
            return json.load(response)

    def task(conversation_id, message=None, action=None):
        task_id = call("/ai/tasks", {
            "conversationId": conversation_id, "message": message, "action": action,
        })["taskId"]
        print("TASK", task_id, flush=True)
        started = time.monotonic()
        events = []
        with request(f"/ai/tasks/{task_id}/stream", stream=True) as response:
            for event in sse_events(response):
                events.append(event)
                if event.get("event") in {"DONE", "FAILED", "APPROVAL_REQUIRED"}:
                    break
        assert events and events[-1]["event"] == "DONE", f"Task incomplete: {task_id}"
        seq = [int(event["id"]) for event in events]
        assert seq == sorted(set(seq)), f"Duplicate/out-of-order SSE: {task_id}"
        assert call(f"/ai/tasks/{task_id}")["status"] == "DONE", "Task status not persisted"
        print("DONE", round(time.monotonic() - started, 2), "seconds",
              ",".join(event["event"] for event in events), flush=True)
        return events

    token = call("/auth/login", {"email": email, "password": password})["accessToken"]
    existing = {c["hospital"]["id"]: c for c in call("/ai/conversations") if c["hospital"]}
    parent = call("/ai/conversations", {"hospitalId": None, "parentConversationId": None})
    parent_id = parent["id"]
    print("MAIN", parent_id, flush=True)
    task(parent_id, "2026년 10월 20일부터 26일까지 한국 여행 가요. 강남이나 명동 근처에서 쌍꺼풀 하고 싶어요. 후기 좋고 많은 곳으로요.")
    partial = call(f"/ai/conversations/{parent_id}")["conditions"] or {}
    assert not partial.get("procedureCode"), "Ambiguous procedure chosen without user input"
    assert not partial.get("consultLanguage"), "Consultation language inferred without user input"
    events = task(parent_id, "매몰 쌍꺼풀이요. 200만 원 이하요. 중국어로 상담 받고 싶어요. 리뷰 수 많은 순으로 보여주세요.")
    cards = next(e["data"]["cards"] for e in reversed(events)
                 if e["event"] == "RESULT_CARDS" and e["data"]["cards"])
    saved = call(f"/ai/conversations/{parent_id}")
    expected = {"procedureCode": "DOUBLE_EYELID_NONINCISION", "budgetMaxKrw": 2000000,
                "consultLanguage": "zh", "sortBy": "REVIEW_COUNT",
                "dateFrom": "2026-10-20", "dateTo": "2026-10-26"}
    for key, value in expected.items():
        assert saved["conditions"].get(key) == value, f"Unexpected condition: {key}"
    assert set(saved["conditions"]["areas"]) == {"GANGNAM", "MYEONGDONG"}
    assert len(saved["messages"]) == 4, "MAIN messages not persisted"
    available = [c["id"] for c in cards
                 if c["id"] not in existing or existing[c["id"]]["mode"] == "HOSPITAL"]
    assert available, "All candidate rooms are HUMAN; use a dedicated test customer"
    picked = next((hospital for hospital in available if hospital not in existing), available[0])
    previous = call("/ai/conversations/" + existing[picked]["id"]) if picked in existing else None
    events = task(parent_id, action={"type": "SELECT_HOSPITAL", "hospitalId": picked})
    nav = next(e["data"] for e in events if e["event"] == "CONVERSATION_OPENED")
    assert set(nav) == {"conversationId", "hospitalId"} and nav["hospitalId"] == picked
    child_id = nav["conversationId"]
    child = call(f"/ai/conversations/{child_id}")
    assert child["hospital"]["id"] == picked and child["mode"] == "HOSPITAL"
    if previous:
        for key in ("id", "parentConversationId", "conditions", "messages"):
            assert child[key] == previous[key], f"Reused room overwritten: {key}"
    else:
        assert child["parentConversationId"] == parent_id
        assert child["conditions"] == saved["conditions"], "Parent conditions not copied"
    before_count = len(child["messages"] or [])
    task(child_id, "请告诉我埋线双眼皮的价格和是否包含增值税。只查询价格，不预约。")
    messages = call(f"/ai/conversations/{child_id}")["messages"]
    assert len(messages) == before_count + 2, "HOSPITAL messages not persisted"
    assert messages[-1]["text"].strip(), "Empty hospital answer"
    print("PASS", "hospital=" + str(picked), "reused=" + str(previous is not None), flush=True)
    print("Browser:", base + "/chat/" + parent_id, base + "/chat/" + child_id)


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sample = b': heartbeat\r\n\r\nid: 1\r\nevent: TOKEN\r\ndata: {"text":\r\ndata: "hello"}\r\n\r\nid: 2\nevent: DONE\ndata: {}\n\n'
        assert list(sse_events(io.BytesIO(sample))) == [
            {"id": "1", "event": "TOKEN", "data": {"text": "hello"}},
            {"id": "2", "event": "DONE", "data": {}},
        ]
        try:
            list(sse_events(io.BytesIO(b"data: invalid\n\n")))
        except json.JSONDecodeError:
            pass
        else:
            raise AssertionError("Invalid SSE JSON accepted")
        print("SELF_TEST_PASS")
    else:
        try:
            main()
        except (AssertionError, KeyError, StopIteration, ValueError, urllib.error.URLError, TimeoutError) as exc:
            print("FAIL", type(exc).__name__, str(exc), file=sys.stderr)
            sys.exit(1)
