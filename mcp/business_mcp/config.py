"""business-mcp 설정 (12 계약서 9장 포트·env)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    # 기본 true: backend /internal 이 아직 없을 때도 agent·MCP 개발이 막히지 않게 (13 문서 3장 stub 전략).
    # compose 최종본에서는 USE_STUB=false 로 띄운다 (12 계약서 9장).
    use_stub: bool = True
    backend_internal_url: str = "http://localhost:8080/internal"
    service_token: str = "change-me-internal-service-token"
    backend_timeout_s: float = 3.0  # 04 문서 1장: 타임아웃 3s 후 1회 재시도

    # stdio(로컬·agent fake 모드)에는 HTTP 헤더가 없으므로 이 값을 acting user 로 쓴다.
    # 3 = customer.zh1 (mock users.json, 데모 시나리오 A 의 중국어 고객). http 모드에서는 X-Acting-User-Id 헤더가 우선.
    default_acting_user_id: int = 3


settings = Settings()
