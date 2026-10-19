"""agent FastAPI 앱 (port 8000). 외부 공개 안 함 — backend 만 내부 HTTP 로 호출.

    uv run uvicorn app.api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO(agent): open_checkpointer_and_store() 로 그래프 compile → app.state.graph
    # TODO(agent): workers.consumer.start_consumers() 로 큐 소비 시작, 종료 시 connection.close()
    yield


app = FastAPI(title="capstone-agent", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    s = get_settings()
    return {"status": "ok", "useFakeTools": s.use_fake_tools}


# TODO(agent): GET /internal/docs/{doc_id} → rag-mcp read_resource("doc://...") (「MCP 설계」 3장, BE-17 근거 패널)
# TODO(agent): GET/DELETE /internal/ai-profile/{user_id} → PostgresStore 프로필 조회·삭제 (「AI Agent 설계」 9-4, P1)
