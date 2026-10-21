import pytest
from fastmcp import Client

from business_mcp import server
from business_mcp.stub_backend import StubBackendClient


async def test_stub_reviews_filter_hospital_language_and_paginate(monkeypatch):
    stub = StubBackendClient()
    monkeypatch.setattr(server, "backend", stub)
    async with Client(server.mcp) as client:
        first = (await client.call_tool("get_hospital_reviews", {"hospital_id": 1, "size": 2})).structured_content
        second = (await client.call_tool("get_hospital_reviews", {"hospital_id": 1, "size": 2, "page": 1})).structured_content
        empty = (await client.call_tool("get_hospital_reviews", {"hospital_id": 1, "page": 99999})).structured_content
        ja = (await client.call_tool("get_hospital_reviews", {"hospital_id": 2, "lang": "ja"})).structured_content
    expected = sorted([r for r in stub.reviews if r["hospital_id"] == 1],
                      key=lambda r: (r["created_at"], r["id"]), reverse=True)
    assert [r["id"] for r in first["items"] + second["items"]] == [r["id"] for r in expected[:4]]
    assert first["total"] == len(expected)
    assert empty["items"] == [] and empty["total"] == len(expected)
    expected_ja = {r["id"] for r in stub.reviews if r["hospital_id"] == 2 and r["lang"] == "ja"}
    assert all(r["id"] in expected_ja for r in ja["items"])
    assert ja["total"] == len(expected_ja)
