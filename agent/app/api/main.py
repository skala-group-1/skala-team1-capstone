"""agent FastAPI 앱 (port 8000). 외부 공개 안 함 — backend 만 내부 HTTP 로 호출.

    uv run uvicorn app.api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.graph.builder import build_hospital_subgraph, compile_graph
from app.graph.state import AgentState
from app.harness.memory import open_checkpointer_and_store
from app.nodes.respond import respond
from app.workers.consumer import start_consumers


def compile_hospital_chat(checkpointer, store):
    """Standalone hospital entry point: no main-agent/planner nodes."""
    graph = StateGraph(AgentState)
    graph.add_node("hospital", build_hospital_subgraph().compile())
    graph.add_node("respond", respond)
    graph.add_edge(START, "hospital")
    graph.add_edge("hospital", "respond")
    graph.add_edge("respond", END)
    return graph.compile(checkpointer=checkpointer, store=store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with open_checkpointer_and_store() as (checkpointer, store):
        app.state.graph = compile_graph(checkpointer, store)
        connection = await start_consumers(app.state.graph, store)
        try:
            yield
        finally:
            await connection.close()


app = FastAPI(title="capstone-agent", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    s = get_settings()
    return {"status": "ok", "useFakeTools": s.use_fake_tools}


# TODO(agent): GET /internal/docs/{doc_id} → rag-mcp read_resource("doc://...") (「MCP 설계」 3장, BE-17 근거 패널)
# TODO(agent): GET/DELETE /internal/ai-profile/{user_id} → PostgresStore 프로필 조회·삭제 (「AI Agent 설계」 9-4, P1)
