"""Idempotent offline indexing into the existing rag schema (never writes app)."""
import argparse
from pathlib import Path

import psycopg

from mcp_common.paths import rag_docs_dir
from rag_mcp.config import settings
from rag_mcp.embeddings import Embedder, vector_literal
from rag_mcp.store import MAX_CHUNK_CHARS, Section, parse_text, slugify


def chunk_sections(doc):
    chunks = []
    for section in doc.sections:
        remaining = section.text.strip()
        parts = []
        while remaining:
            cut = min(len(remaining), MAX_CHUNK_CHARS)
            if cut < len(remaining):
                boundary = max(remaining.rfind("\n", 0, cut + 1),
                               remaining.rfind(" ", 0, cut + 1))
                if boundary > cut // 2:
                    cut = boundary
            parts.append(remaining[:cut])
            remaining = remaining[cut:].lstrip()
        for i, part in enumerate(parts):
            title = section.title if len(parts) == 1 else f"{section.title} part {i + 1}"
            chunks.append(Section(title, slugify(title), part))
    slugs = [c.slug for c in chunks]
    if not chunks or not all(slugs) or len(slugs) != len(set(slugs)):
        raise ValueError(f"Empty or duplicate section slugs: {doc.doc_id}")
    return chunks


def index(root, dsn, embedder):
    if not dsn:
        raise ValueError("Set RAG_INDEX_DATABASE_URL to the indexing writer DSN")
    prepared, ids = [], set()
    for path in sorted(Path(root).rglob("*.md")):
        if path.name == "README.md":
            continue
        raw = path.read_text(encoding="utf-8")
        doc = parse_text(raw, path.stem)
        if doc.doc_id in ids:
            raise ValueError(f"Duplicate document ID: {doc.doc_id}")
        if doc.doc_type == "HOSPITAL_FAQ" and doc.hospital_id is None:
            raise ValueError(f"Hospital FAQ missing hospital_id: {doc.doc_id}")
        ids.add(doc.doc_id)
        prepared.append((doc, raw, chunk_sections(doc)))
    if not prepared:
        raise ValueError("No documents found")
    changed = skipped = count = 0
    with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn:
        # One indexing writer at a time; search remains available.
        conn.execute("SELECT pg_advisory_lock(9102)")
        try:
            for doc, raw, chunks in prepared:
                old = conn.execute("SELECT body FROM rag.documents WHERE doc_id=%s",
                                   (doc.doc_id,)).fetchone()
                old_chunks = conn.execute("""
                    SELECT section, text, embedding_model, embedding IS NOT NULL
                    FROM rag.chunks WHERE doc_id=%s ORDER BY chunk_id
                """, (doc.doc_id,)).fetchall()
                expected = [(s.title, s.text, embedder.model, True) for s in chunks]
                if old and old[0] == raw and old_chunks == expected:
                    skipped += 1
                    count += len(chunks)
                    continue
                inputs = [f"{doc.title}\n{s.title}\n{s.text}" for s in chunks]
                vectors = []
                for start in range(0, len(inputs), 32):
                    vectors.extend(embedder.embed(inputs[start:start + 32]))
                if len(vectors) != len(chunks):
                    raise ValueError("Embedding count mismatch")
                literals = [vector_literal(v) for v in vectors]
                # Replace each document atomically; errors never leave half a document.
                with conn.transaction():
                    conn.execute("""
                        INSERT INTO rag.documents
                        (doc_id,title,doc_type,procedure_code,hospital_id,lang,source,version,body)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (doc_id) DO UPDATE SET title=EXCLUDED.title,
                        doc_type=EXCLUDED.doc_type,procedure_code=EXCLUDED.procedure_code,
                        hospital_id=EXCLUDED.hospital_id,lang=EXCLUDED.lang,
                        source=EXCLUDED.source,version=EXCLUDED.version,body=EXCLUDED.body
                    """, (doc.doc_id, doc.title, doc.doc_type, doc.procedure_code, doc.hospital_id,
                          doc.meta["lang"], doc.meta["source"], int(doc.meta["version"]), raw))
                    conn.execute("DELETE FROM rag.chunks WHERE doc_id=%s", (doc.doc_id,))
                    with conn.cursor() as cursor:
                        cursor.executemany("""
                            INSERT INTO rag.chunks (doc_id,section,text,embedding,embedding_model)
                            VALUES (%s,%s,%s,%s::vector,%s)
                        """, [(doc.doc_id, s.title, s.text, v, embedder.model)
                              for s, v in zip(chunks, literals, strict=True)])
                changed += 1
                count += len(chunks)
                print(f"Indexed {doc.doc_id}: {len(chunks)} chunks", flush=True)
        finally:
            conn.execute("SELECT pg_advisory_unlock(9102)")
    result = {"documents": len(prepared), "chunks": count, "updated": changed, "skipped": skipped}
    print(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=Path, default=rag_docs_dir())
    args = parser.parse_args()
    index(args.docs, settings.rag_index_database_url,
          Embedder(settings.openai_api_key, settings.embedding_model))


if __name__ == "__main__":
    main()
