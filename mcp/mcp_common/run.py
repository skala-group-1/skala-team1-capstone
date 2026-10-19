"""두 서버 공통 실행 진입점.

MCP_TRANSPORT
- http  (기본): Streamable HTTP. compose 에서 http://business-mcp:9101/mcp 로 접근 (04 문서 1장)
- stdio       : agent 의 fake 모드(USE_FAKE_TOOLS=true)가 서브프로세스로 띄워 쓴다 (D-26)
"""

from __future__ import annotations

import os

from fastmcp import FastMCP


def run_server(mcp: FastMCP, default_port: int) -> None:
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    if transport == "stdio":
        # stdio 에서는 stdout 이 프로토콜 채널이라 배너·print 금지
        mcp.run(transport="stdio", show_banner=False)
        return
    mcp.run(
        transport="streamable-http",
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", default_port)),
        path="/mcp",
    )
