"""translator 서비스 설정.

「공통 계약서」 9장 기준. 값은 환경변수 → 저장소 루트 `.env` 순으로 읽는다 (agent/app/config.py 와 같은 방식).
compose 안에서는 compose 가 env 를 넣어주고, 로컬 실행 시에는 루트 `.env` 를 그대로 쓴다.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

TRANSLATOR_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TRANSLATOR_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM (실시간 번역이라 fast 모델만 쓴다)
    openai_api_key: str = ""
    llm_fast_model: str = "gpt-5-nano"

    # 큐 (「공통 계약서」 7장)
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # 용어집: 컨테이너에서는 Dockerfile 이 COPY 한 경로를 GLOSSARY_PATH 로 넘긴다
    glossary_path: Path = REPO_ROOT / "data" / "mock" / "out" / "glossary.json"

    # 서버 (내부 전용, compose healthcheck 용)
    translator_port: int = 8001


@lru_cache
def get_settings() -> Settings:
    return Settings()
