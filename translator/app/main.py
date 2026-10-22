"""translator FastAPI 앱 (port 8001, 내부 전용 — compose healthcheck 용 /health 만 노출).

    uv run uvicorn app.main:app --reload --port 8001
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.glossary import load_glossary
from app.review import start_review_consumer
from app.worker import start_consumers


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_glossary()
    connection = await start_consumers()
    await start_review_consumer(connection)
    yield
    await connection.close()


app = FastAPI(title="capstone-translator", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
