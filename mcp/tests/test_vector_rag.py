"""Chunk integrity and optional real PostgreSQL integration checks."""
import os
from pathlib import Path

import pytest

from rag_mcp.indexer import chunk_sections, index
from rag_mcp.store import Document, Section, PgVectorStore, _parse
from mcp_common.paths import rag_docs_dir


def test_splitting_preserves_content_and_resource_targets():
    text = ("hello world\n" * 200).strip()
    doc = Document("test", "title", "GUIDE", {}, "", [Section("Notes", "notes", text)])
    chunks = chunk_sections(doc)
    assert len(chunks) > 1
    assert all(0 < len(c.text) <= 800 for c in chunks)
    assert "".join("".join(c.text.split()) for c in chunks) == "".join(text.split())
    assert len({c.slug for c in chunks}) == len(chunks)


def test_all_documents_chunk_without_truncation():
    docs = [_parse(p) for p in rag_docs_dir().rglob("*.md")]
    assert len(docs) == 140
    for doc in docs:
        chunks = chunk_sections(doc)
        assert all(len(c.text) <= 800 for c in chunks)
        expected = "".join("".join(s.text.split()) for s in doc.sections)
        assert "".join("".join(c.text.split()) for c in chunks) == expected


@pytest.fixture
def vector_store():
    if os.getenv("RAG_INTEGRATION") != "1":
        pytest.skip("Set RAG_INTEGRATION=1 after indexing to test local PostgreSQL")
    import json
    import psycopg
    from rag_mcp.config import settings
    with psycopg.connect(settings.rag_database_url) as conn:
        row = conn.execute("SELECT embedding::text, embedding_model FROM rag.chunks LIMIT 1").fetchone()
    assert row, "Index documents before integration tests"

    class ExistingVector:
        model = row[1]

        def embed(self, texts):
            return [json.loads(row[0]) for _ in texts]

    return PgVectorStore(settings.rag_database_url, ExistingVector())


def test_real_db_all_hospital_scopes_and_common_only(vector_store):
    for hospital_id in range(1, 51):
        hits = vector_store.search("scope check", hospital_id=hospital_id, top_k=10)
        assert hits and all(h.doc.hospital_id in (None, hospital_id) for h in hits)
    hits = vector_store.search("common", top_k=10)
    assert hits and all(h.doc.hospital_id is None for h in hits)
    assert not vector_store.search("missing", doc_type="UNKNOWN")
    assert not vector_store.search(" ")
    with pytest.raises(ValueError):
        vector_store.search("invalid", hospital_id=-1)


def test_real_db_resource_targets_and_metadata(vector_store):
    hits = vector_store.search("scope check", hospital_id=1, top_k=10)
    for hit in hits:
        doc = vector_store.get(hit.doc.doc_id)
        section = next(s for s in doc.sections if s.slug == hit.section.slug)
        assert section.text == hit.section.text
        assert doc.meta["embedding_model"] == vector_store.embedder.model
    assert vector_store.get("missing") is None
    sample = vector_store.get("SAMPLE_HOSPITAL_FAQ_001")
    assert sample.meta["is_synthetic"] == "true"
    assert "source_origin:" in sample.body


def test_real_db_reindex_is_noop(vector_store):
    from rag_mcp.config import settings

    class MustNotEmbed:
        model = vector_store.embedder.model

        def embed(self, texts):
            raise AssertionError("Unchanged documents should not be embedded")

    result = index(rag_docs_dir(), settings.rag_index_database_url, MustNotEmbed())
    assert result["updated"] == 0 and result["skipped"] == 122


def test_real_db_reader_cannot_write(vector_store):
    import psycopg
    with pytest.raises((psycopg.errors.ReadOnlySqlTransaction, psycopg.errors.InsufficientPrivilege)):
        with vector_store._connect() as conn:
            conn.execute("DELETE FROM rag.chunks WHERE false")
