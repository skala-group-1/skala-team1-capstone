"""문서 저장소 인터페이스.

- StubDocStore    : data/mock/rag_docs/**/*.md 를 읽어 메모리에서 키워드 점수로 검색 (USE_STUB=true)
- PgVectorStore   : rag.documents / rag.chunks (pgvector) 검색 — RAG 담당 구현 몫

문서 형식 (data/mock/rag_docs): YAML front matter(doc_id, title, doc_type, procedure_code | hospital_id, lang, version)
+ 본문은 '## ' 제목 단위 섹션. 색인 규칙과 동일하게 '##' 섹션 = 1 chunk 로 본다 (「파트별 착수 가이드」 4장).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from mcp_common.paths import rag_docs_dir

MAX_CHUNK_CHARS = 800


@dataclass
class Section:
    title: str
    slug: str
    text: str


@dataclass
class Document:
    doc_id: str
    title: str
    doc_type: str
    meta: dict[str, str]
    body: str
    sections: list[Section] = field(default_factory=list)

    @property
    def procedure_code(self) -> str | None:
        v = self.meta.get("procedure_code")
        return None if v in (None, "", "null") else v

    @property
    def hospital_id(self) -> int | None:
        v = self.meta.get("hospital_id")
        return None if v is None or v.strip().lower() in ("", "null", "~") else int(v)


@dataclass
class Hit:
    doc: Document
    section: Section
    score: float


class DocStore(Protocol):
    def search(self, query: str, *, procedure_code: str | None = None, doc_type: str | None = None,
               hospital_id: int | None = None, top_k: int = 5) -> list[Hit]: ...

    def get(self, doc_id: str) -> Document | None: ...


def slugify(title: str) -> str:
    """'Recovery & downtime' → 'recovery-downtime' (「공통 계약서」 Source.uri 예시와 같은 규칙)"""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _parse(path: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    return parse_text(raw, path.stem)


def parse_text(raw: str, fallback_id: str) -> Document:
    meta: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    sections = []
    for block in re.split(r"^## ", body, flags=re.M)[1:]:
        heading, _, text = block.partition("\n")
        sections.append(Section(title=heading.strip(), slug=slugify(heading), text=text.strip()))
    return Document(doc_id=meta.get("doc_id", fallback_id), title=meta.get("title", fallback_id),
                    doc_type=meta.get("doc_type", ""), meta=meta, body=body.strip(), sections=sections)


class StubDocStore:
    """키워드 겹침 비율로 점수를 매기는 근사 검색. 다국어 질의(zh/ja)는 거의 못 찾는다 — 실제는 임베딩 검색."""

    def __init__(self, root: Path | None = None) -> None:
        root = root or rag_docs_dir()
        self._docs = {d.doc_id: d for d in (_parse(p) for p in sorted(root.rglob("*.md")) if p.name != "README.md")}

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    def search(self, query, *, procedure_code=None, doc_type=None, hospital_id=None, top_k=5):
        if hospital_id is not None and (isinstance(hospital_id, bool) or hospital_id <= 0):
            raise ValueError("hospital_id must be a positive ID")
        # Include two-character Korean topics such as 통역, 예약 and 흉터.
        terms = {t for t in re.findall(r"\w+", query.lower()) if len(t) >= 2}
        hits: list[Hit] = []
        for doc in self._docs.values():
            # Scope BEFORE ranking/top_k. No hospital context means common only.
            if doc.hospital_id is not None and doc.hospital_id != hospital_id:
                continue
            if procedure_code and doc.procedure_code not in (procedure_code, None):
                continue
            if doc_type and doc.doc_type != doc_type:
                continue
            for sec in doc.sections:
                words = set(re.findall(r"\w+", f"{sec.title} {sec.text}".lower()))
                score = len(terms & words) / len(terms) if terms else 0.0
                if score > 0:
                    hits.append(Hit(doc, sec, round(score, 3)))
        return sorted(hits, key=lambda h: -h.score)[:top_k]


class PgVectorStore:
    """Exact cosine search, scoped before ranking. Connections are read-only."""

    def __init__(self, database_url: str, embedder=None) -> None:
        from rag_mcp.config import settings
        from rag_mcp.embeddings import Embedder
        if not database_url:
            raise ValueError("Set RAG_DATABASE_URL or DATABASE_URL for vector search")
        self._database_url = database_url
        self.embedder = embedder or Embedder(settings.openai_api_key, settings.embedding_model)

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(self._database_url, row_factory=dict_row, connect_timeout=10)
        conn.read_only = True
        return conn

    def search(self, query, *, procedure_code=None, doc_type=None, hospital_id=None, top_k=5):
        from rag_mcp.embeddings import vector_literal
        if hospital_id is not None and (type(hospital_id) is not int or hospital_id <= 0):
            raise ValueError("hospital_id must be a positive ID")
        if type(top_k) is not int or not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        if not query.strip():
            return []
        vector = vector_literal(self.embedder.embed([query])[0])
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT d.doc_id, d.body, c.section, c.text,
                       1 - (c.embedding <=> %(vector)s::vector) AS score
                FROM rag.chunks c JOIN rag.documents d USING (doc_id)
                WHERE (d.hospital_id = %(hospital)s OR d.hospital_id IS NULL)
                  AND (%(procedure)s::text IS NULL OR d.procedure_code = %(procedure)s
                       OR d.procedure_code IS NULL)
                  AND (%(type)s::text IS NULL OR d.doc_type = %(type)s)
                  AND c.embedding_model = %(model)s AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %(vector)s::vector, c.chunk_id
                LIMIT %(limit)s
            """, {"vector": vector, "hospital": hospital_id, "procedure": procedure_code,
                  "type": doc_type, "model": self.embedder.model, "limit": top_k}).fetchall()
        return [Hit(parse_text(r["body"], r["doc_id"]),
                    Section(r["section"], slugify(r["section"]), r["text"]), float(r["score"]))
                for r in rows]

    def get(self, doc_id):
        with self._connect() as conn:
            row = conn.execute("SELECT body FROM rag.documents WHERE doc_id = %s",
                               (doc_id,)).fetchone()
            if row is None:
                return None
            chunks = conn.execute("""
                SELECT section, text, embedding_model, created_at FROM rag.chunks
                WHERE doc_id = %s ORDER BY chunk_id
            """, (doc_id,)).fetchall()
        doc = parse_text(row["body"], doc_id)
        # Include split-section resource targets while retaining original full sections.
        slugs = {s.slug for s in doc.sections}
        for chunk in chunks:
            slug = slugify(chunk["section"])
            if slug not in slugs:
                doc.sections.append(Section(chunk["section"], slug, chunk["text"]))
                slugs.add(slug)
        if chunks:
            doc.meta["embedding_model"] = chunks[0]["embedding_model"]
            doc.meta["indexed_at"] = chunks[0]["created_at"].isoformat()
            doc.meta["embedding_dimensions"] = "1536"
        return doc


def build_store() -> DocStore:
    from rag_mcp.config import settings

    if settings.use_stub:
        return StubDocStore()
    return PgVectorStore(settings.rag_database_url or settings.database_url)
