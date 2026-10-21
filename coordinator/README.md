# coordinator — 병원 탐색 조율 에이전트

일반 채팅에서 조건을 누적하고 Business MCP로 병원을 검색·비교합니다.
`nodes/planner_agent.py`는 기존 Tool A/B 루프를 사용하며 `collect_conditions`로
검색 전에도 조건을 저장합니다. `extract_conditions`는 이 루프로 진입하게 하고,
실제 누락 질문은 `ask_clarify`가 로그인 언어로 묶어서 만듭니다.

- 첫 턴의 시술·지역·입출국일·사용자가 선택한 정렬을 보존합니다. 예산과 상담 언어는
  한 번만 함께 묻고, 다음 턴에는 응답한 필드만 덮어씁니다. 명시적인 null은 상관없음입니다.
- 시술 정규화·검색·비교는 기존 MCP 도구를 호출합니다. 검색은 최대 5개,
  비교는 표시된 병원 중 1~3개이며 가격·시간·미확인 값은 도구 응답을 따릅니다.
- `SET_SORT`는 기존 조건을 유지하고 선택한 정렬을 적용합니다. 조건 변경·0건·검색 실패는
  이전 목록과 선택을 지웁니다. 자동 조건 완화·병원 추천은 하지 않습니다.
- `SELECT_HOSPITAL`은 현재 목록의 실제 ID를 검사해 조건과 사용자 발언을 담은
  미전송 인계 초안을 만듭니다. 자연어 선택도 같은 인계 함수로 검증합니다.

## 실행과 검증

공통 런타임·의존성·State는 `../agent/`를 사용합니다. 별도 큐 소비자는 없습니다.

```bash
cd agent
uv sync --frozen
uv run --frozen pytest -c pyproject.toml ../coordinator/tests -q
uv run --frozen pytest -c pyproject.toml tests ../coordinator/tests ../concierge/tests -q
# 실제 stdio MCP + repository mock JSON, LLM 없음
RUN_MOCK_MCP=1 uv run --frozen pytest -c pyproject.toml ../coordinator/tests -q
# MCP interpreter가 다른 경로면 MCP_TEST_PYTHON=/absolute/path/to/mcp/.venv/bin/python
# 수동 대화: 실제 LLM 사용(API 비용) + mock Business MCP
PYTHONPATH=.. uv run --frozen python -m coordinator.nodes.planner_agent --locale ko
```

기본 테스트는 ScriptedModel과 조회 spy로 두 턴 조건 유지, 한 번의 선택필터 질문,
검색·비교·정렬·선택·0건·도구 실패를 검증합니다. 자연어 해석의 실제 LLM 품질이나
실제 DB 연동 성공을 뜻하지 않습니다. opt-in 테스트는 stdio MCP 프로토콜과
mock 검색·비교를 검증하며 실제 backend/DB를 사용하지 않습니다.

## 공유 연결과 남은 범위

Task 4의 AgentState에는 `optional_conditions_asked: bool`을 추가해야 하며,
worker는 `action` 원본 camelCase, `conversation_id`, `task_id`를 전달합니다.
`conditions`·`missing`·`candidates`는 기존 snake_case state이고 SSE 변환은 worker 담당입니다.

병원 대화 생성은 **미연결**입니다. backend `POST /internal/conversations`는
`{hospitalId, parentConversationId}`를 받고 기존 고객-병원 대화를 재사용하거나
부모 conditions를 복사해 새 대화를 만듭니다. 하지만 대응하는 MCP 도구가 없습니다.
연결하려면 MCP 담당자가 이 API를 감싸는 도구 계약을 먼저 확정하고, worker가
반환된 대화 ID의 새 thread에 conditions·summary·parent_conversation_id를 전달해야 합니다.
현재는 agent의 직접 HTTP/업무 DB 쓰기를 하지 않고 `CONVERSATION_OPENED`도 발행하지 않습니다.
예약·취소·상담 요청은 이 coordinator의 범위 밖이며 별도 interrupt 승인 경로가 필요합니다.
Tool A 외부 근거 검색도 미연결 상태입니다.
