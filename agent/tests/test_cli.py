"""Deterministic CLI graph; optional real PostgreSQL/process test, no LLM/MCP/queues."""

import asyncio
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_store
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langgraph.types import interrupt

from app import cli
from app.graph.state import AgentState
from app.harness.memory import PROFILE_KEY, PROFILE_NAMESPACE, open_checkpointer_and_store
from app.mcp_client.client import inject_request_headers


class CLIState(AgentState):
    # Worker task 4 owns adding these shared fields to AgentState.
    conversation_id: str
    task_id: str


def compile_cli_test_graph(checkpointer, store):
    async def load_profile(state):
        item = await get_store().aget((PROFILE_NAMESPACE, str(state["user"]["user_id"])), PROFILE_KEY)
        return {"profile": item.value if item else None}

    def approval(state):
        answer = interrupt({"action": "REQUEST_CONSULTATION", "display": {"title": "test only"}})
        status = "approved" if answer["approved"] else "rejected"
        return {"messages": [AIMessage(f"{status}: {state['messages'][-1].content}")]}

    nested = StateGraph(CLIState)
    nested.add_node("approval", approval)
    nested.add_edge(START, "approval")
    nested.add_edge("approval", END)
    builder = StateGraph(CLIState)
    builder.add_node("load_profile", load_profile)
    builder.add_node("hospital", nested.compile())
    builder.add_edge(START, "load_profile")
    builder.add_edge("load_profile", "hospital")
    builder.add_edge("hospital", END)
    return builder.compile(checkpointer=checkpointer, store=store)


@pytest.fixture
def cli_graph(monkeypatch):
    saver, store = MemorySaver(), InMemoryStore()
    graph = compile_cli_test_graph(saver, store)

    @asynccontextmanager
    async def open_memory():
        yield saver, store

    monkeypatch.setattr(cli, "open_checkpointer_and_store", open_memory)
    monkeypatch.setattr(cli, "compile_graph", lambda *_: graph)
    return graph


async def run_cli(monkeypatch, args, answers):
    answers = iter(answers)

    def read(prompt):
        try:
            return next(answers)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr(sys, "argv", ["cli", *args])
    monkeypatch.setattr("builtins.input", read)
    await cli.main()


@pytest.mark.parametrize("answer,expected", [("y", "approved"), ("n", "rejected")])
async def test_cli_restores_pending_before_new_input(cli_graph, monkeypatch, answer, expected):
    args = ["--thread", "t1", "--user", "3"]
    await run_cli(monkeypatch, [*args, "--mode", "HOSPITAL", "--hospital-id", "7", "--locale", "zh"], ["request"])
    config = {"configurable": {"thread_id": "t1"}}
    before = await cli_graph.aget_state(config)
    assert before.interrupts
    assert before.values["conversation_id"] == "t1"
    UUID(before.values["task_id"])
    await run_cli(monkeypatch, args, ["invalid", "", answer])
    after = await cli_graph.aget_state(config)
    assert not after.interrupts
    assert after.values["task_id"] == before.values["task_id"]
    assert [m.content for m in after.values["messages"]] == ["request", f"{expected}: request"]
    assert after.values["user"] == {"user_id": 3, "role": "CUSTOMER", "locale": "zh"}
    assert after.values["mode"] == "HOSPITAL"
    assert after.values["selected_hospital_id"] == 7
    await run_cli(monkeypatch, args, ["next", "n"])
    next_turn = await cli_graph.aget_state(config)
    assert len(next_turn.values["messages"]) == 4
    assert next_turn.values["task_id"] != after.values["task_id"]


@pytest.mark.parametrize("extra", [
    ["--user", "4"], ["--mode", "HOSPITAL", "--hospital-id", "9"],
    ["--locale", "ja"], ["--conditions", '{"date_from":"2026-10-22"}'],
])
async def test_cli_rejects_changed_owner_or_context(cli_graph, monkeypatch, extra, capsys):
    await run_cli(monkeypatch, ["--thread", "private", "--user", "3"], ["secret"])
    with pytest.raises(SystemExit) as error:
        await run_cli(monkeypatch, ["--thread", "private", "--user", "3", *extra], ["y"])
    assert error.value.code == 2
    snapshot = await cli_graph.aget_state({"configurable": {"thread_id": "private"}})
    assert snapshot.interrupts
    assert len(snapshot.values["messages"]) == 1
    assert "secret" not in capsys.readouterr().out


async def test_cli_new_thread_does_not_restore_other_conversation(cli_graph, monkeypatch):
    await run_cli(monkeypatch, ["--thread", "old"], ["private"])
    await run_cli(monkeypatch, ["--thread", "new"], ["new message", "n"])
    snapshot = await cli_graph.aget_state({"configurable": {"thread_id": "new"}})
    assert [m.content for m in snapshot.values["messages"]] == ["new message", "rejected: new message"]


async def test_cli_supplies_mcp_identity_for_new_and_resumed_turns(cli_graph, monkeypatch):
    monkeypatch.setattr("app.mcp_client.client.get_settings", lambda: SimpleNamespace(use_fake_tools=False))
    request = MCPToolCallRequest(name="get_my_reservations", args={}, server_name="business")
    seen = []
    invoke = cli_graph.ainvoke

    async def inspect_context(*args, **kwargs):
        handler = AsyncMock()
        await inject_request_headers(request, handler)
        seen.append(handler.call_args.args[0].headers)
        return await invoke(*args, **kwargs)

    monkeypatch.setattr(cli_graph, "ainvoke", inspect_context)
    await run_cli(monkeypatch, ["--user", "3", "--locale", "zh"], ["request"])
    await run_cli(monkeypatch, ["--user", "3"], ["n"])
    assert len(seen) == 2
    for headers in seen:
        assert headers["X-Acting-User-Id"] == "3"
        assert headers["X-Locale"] == "zh"
        UUID(headers["X-Trace-Id"])
    with pytest.raises(ValueError, match="trusted request identity"):
        await inject_request_headers(request, AsyncMock())


@pytest.mark.parametrize("args", [
    ["--thread", " "], ["--user", "0"], ["--conditions", "[]"],
    ["--mode", "HOSPITAL"], ["--hospital-id", "1"],
])
async def test_cli_rejects_invalid_initial_context(cli_graph, monkeypatch, args):
    with pytest.raises(SystemExit) as error:
        await run_cli(monkeypatch, args, ["request"])
    assert error.value.code == 2
    assert not (await cli_graph.aget_state({"configurable": {"thread_id": "cli"}})).values


async def test_cli_does_not_overwrite_failed_execution(cli_graph, monkeypatch):
    def fail(state):
        raise RuntimeError("test failure")

    builder = StateGraph(CLIState)
    builder.add_node("fail", fail)
    builder.add_edge(START, "fail")
    builder.add_edge("fail", END)
    graph = builder.compile(checkpointer=MemorySaver())
    monkeypatch.setattr(cli, "compile_graph", lambda *_: graph)
    with pytest.raises(RuntimeError, match="test failure"):
        await run_cli(monkeypatch, [], ["original"])
    with pytest.raises(SystemExit) as error:
        await run_cli(monkeypatch, [], ["overwrite"])
    assert error.value.code == 2
    snapshot = await graph.aget_state({"configurable": {"thread_id": "cli"}})
    assert [m.content for m in snapshot.values["messages"]] == ["original"]


@pytest.mark.skipif(not os.environ.get("AGENT_TEST_DATABASE_URL"), reason="requires isolated PostgreSQL")
async def test_postgres_cli_restart_in_separate_processes(monkeypatch):
    """Kill at approval, restart to approve/reject, then inspect with new connections."""
    from app.config import get_settings

    url = os.environ["AGENT_TEST_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    env = {**os.environ, "DATABASE_URL": url, "PYTHONUNBUFFERED": "1"}
    agent_dir = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = os.pathsep.join([str(agent_dir), str(agent_dir.parent)])
    profile = {"preferredAreas": ["GANGNAM"], "consultLanguage": "zh"}
    try:
        async with open_checkpointer_and_store() as (saver, store):
            await store.aput((PROFILE_NAMESPACE, "3"), PROFILE_KEY, profile)
            for connection in (saver.conn, store.conn):
                row = await (await connection.execute("SHOW search_path")).fetchone()
                assert row["search_path"] == "agent"
            tables = await (await saver.conn.execute(
                "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')"
            )).fetchall()
            assert tables and {row["schemaname"] for row in tables} == {"agent"}

        for answer, expected in [("y", "approved"), ("n", "rejected")]:
            thread = str(uuid4())
            command = [sys.executable, str(Path(__file__).resolve()), "--thread", thread, "--user", "3", "--locale", "zh"]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, env=env)
            try:
                process.stdin.write(b"request\n")
                process.stdin.flush()
                output = b""
                deadline = time.monotonic() + 30
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while "승인할까요? [y/n] ".encode() not in output:
                        assert time.monotonic() < deadline, "CLI did not reach approval"
                        if selector.select(timeout=1):
                            chunk = os.read(process.stdout.fileno(), 4096)
                            assert chunk, output.decode()
                            output += chunk
                process.terminate()
                process.wait(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
                process.stdin.close()
                process.stdout.close()

            async with open_checkpointer_and_store() as (saver, store):
                graph = compile_cli_test_graph(saver, store)
                pending = await graph.aget_state({"configurable": {"thread_id": thread}})
                assert pending.interrupts
                task_id = pending.values["task_id"]
                UUID(task_id)
            wrong_user = subprocess.run([*command, "--user", "4"], input="y\n", text=True,
                                        capture_output=True, env=env, timeout=30)
            assert wrong_user.returncode == 2
            assert "APPROVAL_REQUIRED>" not in wrong_user.stdout
            resumed = subprocess.run(command, input=f"{answer}\n\n", text=True,
                                     capture_output=True, env=env, timeout=30)
            assert resumed.returncode == 0, resumed.stderr
            assert f"agent> {expected}: request" in resumed.stdout
            assert resumed.stdout.index("APPROVAL_REQUIRED>") < resumed.stdout.index("you>")
            async with open_checkpointer_and_store() as (saver, store):
                graph = compile_cli_test_graph(saver, store)
                snapshot = await graph.aget_state({"configurable": {"thread_id": thread}})
                assert not snapshot.interrupts
                assert snapshot.values["task_id"] == task_id
                assert snapshot.values["conversation_id"] == thread
                assert [m.content for m in snapshot.values["messages"]] == ["request", f"{expected}: request"]
                assert snapshot.values["profile"] == profile
                assert (await store.aget((PROFILE_NAMESPACE, "3"), PROFILE_KEY)).value == profile
                assert await store.aget((PROFILE_NAMESPACE, "4"), PROFILE_KEY) is None
                assert not (await graph.aget_state({"configurable": {"thread_id": str(uuid4())}})).values
            print(f"PostgreSQL process restart: {expected}; messages/store/user/thread isolation verified")
    finally:
        get_settings.cache_clear()


if __name__ == "__main__":
    cli.compile_graph = compile_cli_test_graph
    asyncio.run(cli.main())
