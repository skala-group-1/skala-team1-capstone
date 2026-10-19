"""rag-mcp 서버 (port 9102). 검색 도구 2 + Resource doc:// (04 문서 3장).

agent 에서는 rag_search_procedure_docs / rag_search_hospital_docs 로 보인다.
FE 근거 패널: backend GET /api/docs/{docId} → agent read_resource → 이 서버의 doc:// (BE-17, AGENT-16)

실행: cd mcp && uv run python -m rag_mcp.server   (MCP_TRANSPORT=stdio 로 stdio)
"""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
from pydantic import Field

from mcp_common.run import run_server
from rag_mcp.config import settings
from rag_mcp.models import Chunk, DocType, SearchResult
from rag_mcp.store import MAX_CHUNK_CHARS, DocStore, Hit, build_store

READ_ONLY = {"readOnlyHint": True, "openWorldHint": False}
NO_RESULT = "No grounded document found. Answer that this could not be confirmed."

mcp = FastMCP(
    name="rag-mcp",
    instructions="Search fictional procedure guides and clinic FAQs. Cite the returned uri for every fact you use.",
)

store: DocStore = build_store()


def _to_result(hits: list[Hit]) -> SearchResult:
    chunks = [
        Chunk(chunk_id=f"{h.doc.doc_id}#{h.section.slug}", doc_id=h.doc.doc_id, title=h.doc.title,
              section=h.section.title, text=h.section.text[:MAX_CHUNK_CHARS], score=h.score,
              uri=f"doc://{h.doc.doc_id}#{h.section.slug}")
        for h in hits if h.score >= settings.rag_score_threshold
    ]
    return SearchResult(chunks=chunks, message=None if chunks else NO_RESULT)


@mcp.tool(annotations=READ_ONLY)
async def search_procedure_docs(
    query: Annotated[str, Field(description="The user's question, in any language")],
    procedure_code: Annotated[str | None, Field(description="Limit to one procedure, e.g. JAW_BOTOX")] = None,
    doc_type: Annotated[DocType | None, Field(description="GUIDE, PREP, AFTERCARE, FAQ or TRAVEL")] = None,
    top_k: Annotated[int, Field(ge=1, le=10)] = 5,
) -> SearchResult:
    """Search general procedure guides and travel/aftercare documents.

    Use for questions about how a procedure works, recovery and downtime, risks, preparation and aftercare.
    Output chunks: chunk_id, doc_id, title, section, text (<= 800 chars), score, uri (doc://...).
    If chunks is empty, say the information could not be confirmed; do not answer from memory.
    General information only, never a personal medical judgment.
    """
    # TODO(rag): 다국어 질의 → 다국어 임베딩 검색 (03 문서 6장). stub 은 영어 키워드만 잘 맞음
    return _to_result(store.search(query, procedure_code=procedure_code, doc_type=doc_type, top_k=top_k))


@mcp.tool(annotations=READ_ONLY)
async def search_hospital_docs(
    hospital_id: int,
    query: str,
    top_k: Annotated[int, Field(ge=1, le=10)] = 3,
) -> SearchResult:
    """Search one hospital's FAQ / visitor notes (location, languages, payment, interpreter, visit flow).
    Same output format as search_procedure_docs.
    """
    # TODO(rag): 병원 대화창에서는 hospital_id 를 agent state 에서 강제 주입 (03 문서 4장)
    return _to_result(store.search(query, hospital_id=hospital_id, top_k=top_k))


@mcp.resource("doc://{doc_id}", mime_type="text/markdown")
def read_document(doc_id: str) -> str:
    """Full source document (markdown) with its metadata header."""
    doc = store.get(doc_id)
    if doc is None:
        raise ResourceError(f"Document {doc_id} not found")
    # TODO(rag): 메타에 임베딩 모델·색인 시각도 포함 (04 문서 3장 Resource 메타: 출처, 버전, 언어, 임베딩 모델)
    header = "\n".join(f"{k}: {v}" for k, v in doc.meta.items())
    return f"---\n{header}\n---\n\n{doc.body}"


@mcp.resource("doc://{doc_id}/sections/{section}", mime_type="text/markdown")
def read_section(doc_id: str, section: str) -> str:
    """One section of a document. section = slug from the chunk uri (after '#')."""
    doc = store.get(doc_id)
    sec = next((s for s in doc.sections if s.slug == section), None) if doc else None
    if sec is None:
        raise ResourceError(f"Section {doc_id}/{section} not found")
    return f"## {sec.title}\n\n{sec.text}"


# TODO(rag): (선택) Prompt answer_with_citations(question, locale) — 근거 인용 답변 템플릿 (04 문서 3장)


if __name__ == "__main__":
    run_server(mcp, default_port=9102)
