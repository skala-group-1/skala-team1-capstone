# business-mcp / rag-mcp 공용 이미지. build context 는 저장소 루트 (backend 와 같은 방식)
#   docker build -f mcp/Dockerfile -t capstone-mcp .
# 실행할 서버는 compose 에서 command 로 고른다 (INFRA-03 에서 compose 에 추가):
#   business-mcp: command: ["python", "-m", "business_mcp.server"]   ports 9101
#   rag-mcp:      command: ["python", "-m", "rag_mcp.server"]        ports 9102
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"

WORKDIR /app/mcp
COPY mcp/pyproject.toml mcp/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY mcp/ ./
# stub 모드(USE_STUB=true)용 mock 데이터. 실제 모드에서는 쓰지 않는다
COPY data/mock/out /app/data/mock/out
COPY data/mock/rag_docs /app/data/mock/rag_docs
ENV MOCK_DATA_DIR=/app/data/mock/out RAG_DOCS_DIR=/app/data/mock/rag_docs \
    MCP_TRANSPORT=http MCP_HOST=0.0.0.0

CMD ["python", "-m", "business_mcp.server"]
