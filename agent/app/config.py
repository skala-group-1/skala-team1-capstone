"""agent 서비스 설정.

12 공통 계약서 9장(포트·호스트·환경변수) 기준. 값은 환경변수 → 저장소 루트 `.env` 순으로 읽는다.
compose 안에서는 compose가 env를 넣어주고, 로컬 실행 시에는 루트 `.env`를 그대로 쓴다.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

AGENT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = AGENT_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM (D-18: 우선 gpt-5-nano, .env로 교체)
    openai_api_key: str = ""
    llm_primary_model: str = "gpt-5-nano"
    llm_fast_model: str = "gpt-5-nano"
    llm_fallback_model: str = "gpt-5-nano"
    embedding_model: str = "text-embedding-3-small"

    # LangSmith (선택)
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "skala-team1-capstone"

    # 저장소: checkpointer·store 는 schema agent. 비어 있으면 MemorySaver(개발용)
    # 예: postgresql://agent:agent@localhost:5432/capstone?options=-csearch_path%3Dagent
    # TODO(agent): INFRA-01 에서 agent 계정이 만들어지면 기본값 확정 (12 문서 9장)
    database_url: str = ""

    # 큐 (12 문서 7장)
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "capstone.direct"

    # MCP (04 문서 1장, D-29)
    # USE_FAKE_TOOLS=true  → business-mcp·rag-mcp 를 stdio 로 직접 띄우고 USE_STUB=true (mock JSON)
    # USE_FAKE_TOOLS=false → compose 의 streamable HTTP 서버에 연결
    use_fake_tools: bool = True
    business_mcp_url: str = "http://business-mcp:9101/mcp"
    rag_mcp_url: str = "http://rag-mcp:9102/mcp"
    mcp_project_dir: Path = REPO_ROOT / "mcp"

    # 서버
    agent_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
