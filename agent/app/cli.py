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

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graph.builder import compile_graph
from app.harness.memory import open_checkpointer_and_store


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--thread", default="cli")
    p.add_argument("--user-id", type=int, default=1)
    p.add_argument("--locale", default="en")
    p.add_argument("--mode", default="MAIN", choices=["MAIN", "HOSPITAL", "HUMAN"])
    p.add_argument("--hospital-id", type=int)
    p.add_argument("--conditions", type=json.loads, default=None, help="초기 Conditions JSON (snake_case)")
    args = p.parse_args()

    config = {"configurable": {"thread_id": args.thread}}
    first = {
        "user": {"user_id": args.user_id, "role": "CUSTOMER", "locale": args.locale},
        "mode": args.mode,
        "selected_hospital_id": args.hospital_id,
    }
    if args.conditions:
        first["conditions"] = args.conditions

    async with open_checkpointer_and_store() as (checkpointer, store):
        graph = compile_graph(checkpointer, store)
        print(f"thread={args.thread} mode={args.mode} (빈 줄 또는 Ctrl-D 로 종료)")
        while True:
            try:
                text = input("you> ").strip()
            except EOFError:
                break
            if not text:
                break
            payload = {**first, "messages": [HumanMessage(text)]}
            first = {}  # 초기값은 첫 턴에만
            result = await graph.ainvoke(payload, config)
            while result.get("__interrupt__"):
                pending = result["__interrupt__"][0].value
                print("APPROVAL_REQUIRED>", json.dumps(pending, ensure_ascii=False, indent=2))
                answer = input("승인할까요? [y/n] ").strip().lower()
                resume = {"approved": answer == "y", "editedArgs": {}, "reason": None if answer == "y" else "rejected in CLI"}
                result = await graph.ainvoke(Command(resume=resume), config)
            print("agent>", result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
