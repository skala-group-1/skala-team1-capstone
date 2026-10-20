"""rag-mcp 설정 (「공통 계약서」 9장)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[2] / ".env",
                  Path(__file__).resolve().parents[1] / ".env.rag"), extra="ignore",
        env_ignore_empty=True,
    )

    # 기본 true: 색인(indexer)·pgvector 가 준비되기 전에도 agent 가 근거 검색을 쓸 수 있게.
    # compose 최종본에서는 USE_STUB=false (pgvector 검색)
    use_stub: bool = True
    # 읽기 전용 계정 rag_ro, schema rag (「공통 계약서」 9장). INFRA-01 에서 계정 생성
    database_url: str = ""
    rag_database_url: str = ""  # Optional override, independent of agent DATABASE_URL.
    rag_index_database_url: str = ""  # Writer DSN; never used by the search server.
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    # 이 점수 미만 chunk 는 버린다 → 0건이면 'No grounded document found' (「MCP 설계」 3장)
    # TODO(rag): stub(키워드 점수)과 pgvector(코사인 유사도)의 스케일이 다르므로 실제 값은 검색 품질 점검 후 확정
    rag_score_threshold: float = 0.2


settings = Settings()
