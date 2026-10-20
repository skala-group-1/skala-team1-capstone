import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from app.mcp_client.client import inject_request_headers, mcp_request_context


@pytest.fixture(autouse=True)
def http_mode(monkeypatch):
    monkeypatch.setattr("app.mcp_client.client.get_settings", lambda: SimpleNamespace(use_fake_tools=False))


async def test_parallel_requests_keep_identity_separate():
    request = MCPToolCallRequest(name="get_my_reservations", args={}, server_name="business")

    async def invoke(user, locale):
        handler = AsyncMock()
        with mcp_request_context(user, locale, f"trace-{user}"):
            await asyncio.sleep(0)
            await inject_request_headers(request, handler)
        return handler.call_args.args[0]

    first, second = await asyncio.gather(invoke(3, "zh"), invoke(14, "ko"))
    assert first.headers == {"X-Acting-User-Id": "3", "X-Locale": "zh", "X-Trace-Id": "trace-3"}
    assert second.headers == {"X-Acting-User-Id": "14", "X-Locale": "ko", "X-Trace-Id": "trace-14"}
    assert first.args == second.args == {}
    with pytest.raises(ValueError, match="trusted request identity"):
        await inject_request_headers(request, AsyncMock())


async def test_rag_does_not_receive_user_headers():
    request = MCPToolCallRequest(name="search_hospital_docs", args={}, server_name="rag")
    handler = AsyncMock()
    with mcp_request_context(14, "ko", "trace"):
        await inject_request_headers(request, handler)
    assert handler.call_args.args[0].headers is None
