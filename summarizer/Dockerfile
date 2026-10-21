# build context = 저장소 루트 (compose: context: . / dockerfile: summarizer/Dockerfile)
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv

COPY summarizer/pyproject.toml summarizer/uv.lock summarizer/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY summarizer/ ./
# 용어집 — 시술 코드 → 언어별 표시명 매핑용
COPY data/mock/out/glossary.json ./data/glossary.json
ENV PATH="/app/.venv/bin:$PATH" GLOSSARY_PATH=/app/data/glossary.json
EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
