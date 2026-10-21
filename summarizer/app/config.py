"""summarizer 서비스 설정. 값은 환경변수 → 저장소 루트 `.env` 순으로 읽는다 (agent/app/config.py 와 같은 방식)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SUMMARIZER_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SUMMARIZER_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    llm_fast_model: str = "gpt-5-nano"

    # 시술 코드 → 표시명 (언어별) 매핑용. 컨테이너에서는 Dockerfile 이 GLOSSARY_PATH 로 지정
    glossary_path: Path = REPO_ROOT / "data" / "mock" / "out" / "glossary.json"

    # 서버 (내부 전용 — agent 그래프 노드가 동기 호출)
    summarizer_port: int = 8002


@lru_cache
def get_settings() -> Settings:
    return Settings()
