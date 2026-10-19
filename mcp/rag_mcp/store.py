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
        return int(v) if v and v != "null" else None


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
    return Document(doc_id=meta.get("doc_id", path.stem), title=meta.get("title", path.stem),
                    doc_type=meta.get("doc_type", ""), meta=meta, body=body.strip(), sections=sections)


class StubDocStore:
    """키워드 겹침 비율로 점수를 매기는 근사 검색. 다국어 질의(zh/ja)는 거의 못 찾는다 — 실제는 임베딩 검색."""

    def __init__(self, root: Path | None = None) -> None:
        root = root or rag_docs_dir()
        self._docs = {d.doc_id: d for d in (_parse(p) for p in sorted(root.rglob("*.md")) if p.name != "README.md")}

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    def search(self, query, *, procedure_code=None, doc_type=None, hospital_id=None, top_k=5):
        terms = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 2}
        hits: list[Hit] = []
        for doc in self._docs.values():
            if procedure_code and doc.procedure_code not in (procedure_code, None):
                continue
            if doc_type and doc.doc_type != doc_type:
                continue
            if hospital_id is not None and doc.hospital_id != hospital_id:
                continue
            if hospital_id is None and doc.doc_type == "HOSPITAL_FAQ":
                continue  # 병원 FAQ 는 search_hospital_docs 로만
            for sec in doc.sections:
                words = set(re.findall(r"\w+", f"{sec.title} {sec.text}".lower()))
                score = len(terms & words) / len(terms) if terms else 0.0
                if score > 0:
                    hits.append(Hit(doc, sec, round(score, 3)))
        return sorted(hits, key=lambda h: -h.score)[:top_k]


class PgVectorStore:
    """rag.chunks 임베딩 검색.

    TODO(rag): 구현 (「파트별 착수 가이드」 4장, 「데이터·DB 설계」 rag 스키마)
      1. data/rag_docs/indexer.py 가 front matter 파싱 → '##' 섹션 청킹 → 임베딩 → rag.documents·rag.chunks 저장
         (임베딩 모델·차원을 메타로 함께 저장)
      2. 여기서는 query 를 같은 EMBEDDING_MODEL 로 임베딩 → `ORDER BY embedding <=> :q LIMIT top_k`
      3. procedure_code / doc_type / hospital_id 필터는 WHERE 로
      4. DATABASE_URL 은 읽기 전용 계정 rag_ro (INFRA-01)
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def search(self, query, *, procedure_code=None, doc_type=None, hospital_id=None, top_k=5):
        raise NotImplementedError("TODO(rag): pgvector 검색 구현")

    def get(self, doc_id):
        raise NotImplementedError("TODO(rag): rag.documents 원문 조회 구현")


def build_store() -> DocStore:
    from rag_mcp.config import settings

    if settings.use_stub:
        return StubDocStore()
    return PgVectorStore(settings.database_url)
