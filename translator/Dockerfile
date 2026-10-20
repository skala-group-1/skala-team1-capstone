# build context = 저장소 루트 (compose: context: . / dockerfile: translator/Dockerfile)
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv

COPY translator/pyproject.toml translator/uv.lock translator/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY translator/ ./
# 용어집 (66건) — 기동 시 로드, 원문에 등장하는 용어만 프롬프트에 주입
COPY data/mock/out/glossary.json ./data/glossary.json
ENV PATH="/app/.venv/bin:$PATH" GLOSSARY_PATH=/app/data/glossary.json
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
