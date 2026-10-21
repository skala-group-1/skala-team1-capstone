"""Memory fallback and PostgreSQL schema boundary; no business DB writes."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from app.harness import memory


async def test_memory_fallback_is_ephemeral(monkeypatch):
    monkeypatch.setattr(memory, "get_settings", lambda: SimpleNamespace(database_url=""))
    async with memory.open_checkpointer_and_store() as (saver, store):
        assert isinstance(saver, MemorySaver)
        assert isinstance(store, InMemoryStore)
        await store.aput((memory.PROFILE_NAMESPACE, "3"), memory.PROFILE_KEY, {"budgetMaxKrw": 100})
        assert await store.aget((memory.PROFILE_NAMESPACE, "4"), memory.PROFILE_KEY) is None
    async with memory.open_checkpointer_and_store() as (_, store):
        assert await store.aget((memory.PROFILE_NAMESPACE, "3"), memory.PROFILE_KEY) is None


@pytest.mark.parametrize("fail_setup", [False, True])
@pytest.mark.parametrize("schema_exists", [False, True])
async def test_postgres_schema_before_setup_and_no_silent_fallback(monkeypatch, fail_setup, schema_exists):
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.store.postgres.aio import AsyncPostgresStore

    monkeypatch.setattr(memory, "get_settings", lambda: SimpleNamespace(database_url="postgresql://test"))
    calls = []

    def connection(kind):
        async def execute(sql):
            calls.append((kind, sql))
            return SimpleNamespace(fetchone=AsyncMock(return_value={"name": "agent" if schema_exists else None}))

        async def setup():
            calls.append((kind, "setup"))
            if fail_setup:
                raise RuntimeError("setup failed")

        return SimpleNamespace(conn=SimpleNamespace(execute=execute), setup=setup)

    saver, store = connection("saver"), connection("store")
    closed = []

    @asynccontextmanager
    async def open_saver(url):
        try:
            yield saver
        finally:
            closed.append("saver")

    @asynccontextmanager
    async def open_store(url):
        try:
            yield store
        finally:
            closed.append("store")

    monkeypatch.setattr(AsyncPostgresSaver, "from_conn_string", open_saver)
    monkeypatch.setattr(AsyncPostgresStore, "from_conn_string", open_store)

    async def run():
        async with memory.open_checkpointer_and_store() as pair:
            assert pair == (saver, store)

    if fail_setup:
        with pytest.raises(RuntimeError, match="setup failed"):
            await run()
    else:
        await run()
    expected = [("saver", "SELECT to_regnamespace('agent') AS name")]
    if not schema_exists:
        expected.append(("saver", "CREATE SCHEMA IF NOT EXISTS agent"))
    expected += [
        ("saver", "SET search_path TO agent"),
        ("store", "SET search_path TO agent"),
        ("saver", "setup"),
    ]
    assert calls[:len(expected)] == expected
    if schema_exists:
        assert ("saver", "CREATE SCHEMA IF NOT EXISTS agent") not in calls
    assert closed == ["store", "saver"]
