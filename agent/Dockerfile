# build context = 저장소 루트 (compose: context: . / dockerfile: agent/Dockerfile)
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/
WORKDIR /app/agent
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/agent/.venv PYTHONPATH=/app

COPY agent/pyproject.toml agent/uv.lock agent/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY agent/ ./
COPY coordinator/ /app/coordinator/
COPY concierge/ /app/concierge/
COPY aftercare/ /app/aftercare/
# compose 안에서는 USE_FAKE_TOOLS=false (MCP 는 별도 컨테이너, streamable HTTP)
ENV PATH="/app/agent/.venv/bin:$PATH" USE_FAKE_TOOLS=false
EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
