"""호출자 컨텍스트 (acting user, trace id).

「MCP 설계」 1장: acting_user_id·trace_id 는 LLM 인자에 노출하지 않고 헤더로 받아 backend 에 전달.
- http 모드: agent 가 MCP 요청 헤더에 X-Acting-User-Id / X-Trace-Id / X-Locale 을 실어 보낸다
- stdio 모드(agent fake): 헤더가 없으므로 DEFAULT_ACTING_USER_ID env 를 쓴다
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastmcp.server.dependencies import get_http_headers

from business_mcp.config import settings


@dataclass(frozen=True)
class CallContext:
    acting_user_id: int
    trace_id: str
    locale: str | None = None  # None 이면 backend 가 acting user locale 사용


def current_context() -> CallContext:
    # get_http_headers 는 HTTP 요청 밖(stdio·인메모리)이면 빈 dict 를 돌려준다
    headers = get_http_headers(include={"x-acting-user-id", "x-trace-id", "x-locale"})
    # TODO(mcp): agent 가 사용자별로 헤더를 바꿔 보내는 방법 확정
    #            (요청마다 헤더를 바꾼 MCP 세션 vs. 도구 호출 _meta). 「AI Agent 설계」 / agent 담당과 합의
    user_id = headers.get("x-acting-user-id")
    return CallContext(
        acting_user_id=int(user_id) if user_id else settings.default_acting_user_id,
        trace_id=headers.get("x-trace-id") or str(uuid.uuid4()),
        locale=headers.get("x-locale"),
    )
