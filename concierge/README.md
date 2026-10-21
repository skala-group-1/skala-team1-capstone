# concierge — 선택 병원 상담 에이전트

사용자가 선택한 병원의 정보·FAQ를 조회하고 예약 의사를 수집해 승인 카드를 준비합니다.
예약·취소·상담사 연결이 이 역할의 범위이며, 실제 변경 실행은 아직 연결 전입니다.

- `nodes/hospital_agent.py`: 병원 범위 LLM 도구 루프
- `nodes/load_hospital_context.py`, `nodes/tools.py`: 선택 병원 컨텍스트와 병원 ID 강제 주입
- `nodes/hospital_reply.py`: 사용자 응답 검증
- `nodes/approval.py`, `nodes/execute_action.py`: 승인 interrupt와 변경 실행 경계
- `prompts/`, `tests/`: 병원 상담 지침과 상담·RAG·워커 테스트

공통 의존성·State·Harness·MCP·그래프 조립은 `../agent/`를 사용합니다.
Python namespace package이며 저장소 루트를 `PYTHONPATH`에 포함합니다.
웹 채팅은 기존 `agent/app/api/main.py`와 단일 큐 워커로 실행합니다.
실행 방법과 승인·저장 제한은 [공통 런타임 문서](../agent/README.md)를 참고하세요.

```bash
# 저장소 루트에서
cd agent
uv sync --frozen
uv run --frozen pytest -c pyproject.toml ../concierge/tests -q
PYTHONPATH=.. uv run --frozen python -m app.cli --mode HOSPITAL --hospital-id 1
```

CLI 대화에는 LLM 키와 MCP 실행 환경이 필요합니다. 웹 채팅의 예약 승인 후에는
실제 예약을 저장하지 않고 미접수를 알리는 `FAILED` 이벤트를 보내는 기존 동작을 유지합니다.
