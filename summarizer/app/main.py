"""summarizer FastAPI 앱 (port 8002, 내부 전용 — 메인·서브 에이전트의 그래프 노드가 동기 호출).

    uv run uvicorn app.main:app --reload --port 8002
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.schemas import SummarizeRequest, SummarizeResponse
from app.summarize import procedure_names, summarize


@asynccontextmanager
async def lifespan(app: FastAPI):
    procedure_names()    # 용어집 로드 (코드 → 표시명)
    yield


app = FastAPI(title="capstone-summarizer", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/summarize", response_model=SummarizeResponse)
async def post_summarize(req: SummarizeRequest) -> SummarizeResponse:
    return await summarize(req)
