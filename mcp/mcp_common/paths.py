"""저장소 안의 mock 데이터 위치 찾기.

stub 모드(USE_STUB=true)는 data/mock 의 JSON·Markdown 을 직접 읽는다.
- 로컬: 이 파일에서 위로 올라가며 data/mock 폴더를 찾는다
- 컨테이너: MOCK_DATA_DIR / RAG_DOCS_DIR env 로 지정 (Dockerfile 주석 참고)
"""

from __future__ import annotations

import os
from pathlib import Path


def _find_repo_mock_dir() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "mock"
        if candidate.is_dir():
            return candidate
    return None


def mock_out_dir() -> Path:
    """data/mock/out (테이블별 JSON)"""
    if env := os.getenv("MOCK_DATA_DIR"):
        return Path(env)
    base = _find_repo_mock_dir()
    if base is None:
        raise FileNotFoundError("data/mock 을 찾지 못했습니다. MOCK_DATA_DIR 를 지정하세요.")
    return base / "out"


def rag_docs_dir() -> Path:
    """data/mock/rag_docs (procedures/, common/, hospitals/)"""
    if env := os.getenv("RAG_DOCS_DIR"):
        return Path(env)
    base = _find_repo_mock_dir()
    if base is None:
        raise FileNotFoundError("data/mock 을 찾지 못했습니다. RAG_DOCS_DIR 를 지정하세요.")
    return base / "rag_docs"
