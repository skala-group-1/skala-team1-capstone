"""Hospital scoping must happen before ranking, including non-FAQ documents."""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from rag_mcp import server
from rag_mcp.store import StubDocStore


@pytest.fixture
def scoped_store(tmp_path, monkeypatch):
    for name, hospital, kind, text in [
        ("selected", "1", "HOSPITAL_FAQ", "통역 방문 준비"),
        ("common", "null", "AFTERCARE", "통역 준비 관리"),
        ("uppercase_null", "NULL", "PREP", "통역 준비"),
        ("other", "2", "HOSPITAL_FAQ", "통역 방문 준비 관리 회복"),
        ("other_aftercare", "2", "AFTERCARE", "통역 방문 준비 관리 회복"),
    ]:
        (tmp_path / f"{name}.md").write_text(
            f"---\ndoc_id: {name}\ntitle: {name}\ndoc_type: {kind}\n"
            f"hospital_id: {hospital}\nprocedure_code: JAW_BOTOX\n---\n"
            f"## Notes\n{text}\n", encoding="utf-8",
        )
    store = StubDocStore(tmp_path)
    monkeypatch.setattr(server, "store", store)
    return store


def test_selected_plus_common(scoped_store):
    hits = scoped_store.search("통역", hospital_id=1, top_k=10)
    assert {h.doc.doc_id for h in hits} == {"selected", "common", "uppercase_null"}


def test_unscoped_is_common_only(scoped_store):
    hits = scoped_store.search("통역", top_k=10)
    assert {h.doc.doc_id for h in hits} == {"common", "uppercase_null"}


def test_scope_before_top_k(scoped_store):
    # Other hospitals score highest but cannot occupy the result budget.
    hits = scoped_store.search("통역 방문 준비 관리 회복", hospital_id=1, top_k=1)
    assert len(hits) == 1 and hits[0].doc.hospital_id in (None, 1)


def test_procedure_and_type_are_combined_with_scope(scoped_store):
    hits = scoped_store.search("통역", hospital_id=1, procedure_code="JAW_BOTOX", doc_type="AFTERCARE")
    assert [h.doc.doc_id for h in hits] == ["common"]
    assert not scoped_store.search("통역", hospital_id=1, procedure_code="RHINOPLASTY")


@pytest.mark.parametrize("tool", ["search_hospital_docs", "search_procedure_docs"])
async def test_mcp_tools_enforce_scope(scoped_store, tool):
    async with Client(server.mcp) as client:
        response = await client.call_tool(tool, {"hospital_id": 1, "query": "통역", "top_k": 10})
    assert {c["doc_id"] for c in response.structured_content["chunks"]} == {
        "selected", "common", "uppercase_null",
    }


@pytest.mark.parametrize("hospital_id", [0, -1])
async def test_invalid_hospital_cannot_expand_scope(scoped_store, hospital_id):
    async with Client(server.mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("search_hospital_docs", {"hospital_id": hospital_id, "query": "통역"})


def test_repository_documents_are_scoped():
    store = StubDocStore()
    for hospital_id in (1, 2):
        hits = store.search("통역", hospital_id=hospital_id, top_k=50)
        assert any(h.doc.doc_id == f"SAMPLE_HOSPITAL_FAQ_{hospital_id:03d}" for h in hits)
        assert all(h.doc.hospital_id in (None, hospital_id) for h in hits)
    common = store.search("aftercare", hospital_id=1, top_k=50)
    assert any(h.doc.hospital_id is None for h in common)
