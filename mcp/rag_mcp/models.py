"""rag-mcp 출력 모델. agent 는 chunk 를 근거(Source, 12 계약서 5장 AI)로 변환해 SSE DONE 에 싣는다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

DocType = Literal["GUIDE", "PREP", "AFTERCARE", "FAQ", "TRAVEL", "HOSPITAL_FAQ"]


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    section: str
    text: str  # ≤ 800자
    score: float
    uri: str  # doc://{doc_id}#{section_slug}


class SearchResult(BaseModel):
    chunks: list[Chunk]
    message: str | None = None  # 0건이면 "No grounded document found"
