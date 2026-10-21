"""CLI 러너 — 큐·backend·FE 없이 그래프와 대화 (「파트별 착수 가이드」 Agent 착수 순서 4).

    uv run python -m app.cli --thread t1
    uv run python -m app.cli --thread h1 --mode HOSPITAL --hospital-id 1     # 병원 대화창 ("예약" 입력 → 승인 y/n)
    uv run python -m app.cli --conditions '{"procedure_code":"JAW_BOTOX","date_from":"2026-10-20"}'

interrupt(승인 대기)가 나오면 y/n 으로 Command(resume=...) 재개.
TODO(agent): 노드 진행·도구 호출을 같이 보여주는 --verbose (astream_events)
"""

import argparse
import asyncio
import json
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graph.builder import compile_graph
from app.harness.memory import open_checkpointer_and_store
from app.mcp_client.client import mcp_request_context


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--thread", default="cli")
    p.add_argument("--user-id", "--user", type=int, default=1)
    p.add_argument("--locale", choices=["en", "zh", "ja", "ko"])
    p.add_argument("--mode", choices=["MAIN", "HOSPITAL", "HUMAN"])
    p.add_argument("--hospital-id", type=int)
    p.add_argument("--conditions", type=json.loads, default=None, help="초기 Conditions JSON (snake_case)")
    args = p.parse_args()
    if not args.thread.strip() or args.user_id <= 0:
        p.error("thread는 비어 있을 수 없고 user는 양수여야 합니다.")
    if args.conditions is not None and not isinstance(args.conditions, dict):
        p.error("conditions는 JSON 객체여야 합니다.")

    config = {"configurable": {"thread_id": args.thread}}
    async with open_checkpointer_and_store() as (checkpointer, store):
        graph = compile_graph(checkpointer, store)
        snapshot = await graph.aget_state(config)
        saved = snapshot.values
        if saved:
            if saved.get("user", {}).get("user_id") != args.user_id:
                p.error("이 thread는 다른 사용자 소유입니다. 같은 사용자 또는 새 thread를 사용하세요.")
            for supplied, stored in (
                (args.mode, saved.get("mode")),
                (args.hospital_id, saved.get("selected_hospital_id")),
                (args.locale, saved.get("user", {}).get("locale")),
                (args.conditions, saved.get("conditions")),
            ):
                if supplied is not None and supplied != stored:
                    p.error("저장된 대화 설정과 다릅니다. 설정을 생략하거나 새 thread를 사용하세요.")
            first = {}
        else:
            mode = args.mode or "MAIN"
            if mode == "HOSPITAL" and (args.hospital_id is None or args.hospital_id <= 0):
                p.error("HOSPITAL 모드는 양수 hospital-id가 필요합니다.")
            if mode != "HOSPITAL" and args.hospital_id is not None:
                p.error("hospital-id는 HOSPITAL 모드에서만 사용합니다.")
            first = {
                "user": {"user_id": args.user_id, "role": "CUSTOMER", "locale": args.locale or "en"},
                "mode": mode,
                "selected_hospital_id": args.hospital_id,
            }
            if args.conditions is not None:
                first["conditions"] = args.conditions
        if snapshot.next and not snapshot.interrupts:
            p.error("완료되지 않은 실행입니다. 오류를 확인한 뒤 복구하세요. 새 입력으로 덮어쓰지 않습니다.")
        print(f"thread={args.thread} mode={(saved or first)['mode']} (빈 줄 또는 Ctrl-D 로 종료)")
        if saved:
            print(f"복원한 메시지: {len(saved.get('messages', []))}")
        result = {**saved, "__interrupt__": snapshot.interrupts}
        locale = (saved or first)["user"]["locale"]
        try:
            while True:
                while result.get("__interrupt__"):
                    decisions = {}
                    for pending in result["__interrupt__"]:
                        print("APPROVAL_REQUIRED>", json.dumps(pending.value, ensure_ascii=False, indent=2))
                        while (answer := input("승인할까요? [y/n] ").strip().lower()) not in {"y", "n"}:
                            print("y 또는 n을 입력하세요. Ctrl-D로 승인 대기를 보존하고 종료합니다.")
                        decisions[pending.id] = {
                            "approved": answer == "y", "editedArgs": {},
                            "reason": None if answer == "y" else "rejected in CLI",
                        }
                    with mcp_request_context(args.user_id, locale, str(uuid4())):
                        result = await graph.ainvoke(Command(resume=decisions), config)
                messages = result.get("messages", [])
                if messages and messages[-1].type == "ai":
                    print("agent>", messages[-1].content)
                text = input("you> ").strip()
                if not text:
                    break
                with mcp_request_context(args.user_id, locale, str(uuid4())):
                    result = await graph.ainvoke({
                        **first, "messages": [HumanMessage(text)], "conversation_id": args.thread,
                        "task_id": str(uuid4()),
                    }, config)
                first = {}  # 초기값은 새 대화의 첫 턴에만
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다. PostgreSQL 사용 시 같은 thread와 user로 재개할 수 있습니다.")


if __name__ == "__main__":
    asyncio.run(main())
