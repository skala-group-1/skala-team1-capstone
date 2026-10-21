# coordinator — 병원 탐색 조율 에이전트

일반 채팅에서 조건을 누적하고 Business MCP로 병원을 검색·비교합니다.
`nodes/planner_agent.py`는 기존 Tool A/B 루프를 사용하며 `collect_conditions`로
매 턴 먼저 조건을 저장합니다. 새 시술명은 실제 정규화 응답의 코드로 확인한 뒤 저장하며,
정규화 실패에도 지역·일정·예산·상담언어는 보존합니다. `extract_conditions`는 이 루프로 진입하게 하고,
실제 누락 질문은 `ask_clarify`가 로그인 언어로 묶어서 만듭니다.

- 첫 턴의 시술·지역·입출국일·사용자가 선택한 정렬을 보존합니다. 예산과 상담 언어는
  한 번만 함께 묻고, 다음 턴에는 응답한 필드만 덮어씁니다. 명시적인 null은 상관없음입니다.
- 시술 정규화·검색·비교는 기존 MCP 도구를 호출합니다. 검색은 최대 5개,
  비교는 표시된 병원 중 1~3개이며 가격·시간·미확인 값은 도구 응답을 따릅니다.
- `SET_SORT`는 기존 조건을 유지하고 선택한 정렬을 적용합니다. 조건 변경·0건·검색 실패는
  이전 목록과 선택을 지웁니다. 자동 조건 완화·병원 추천은 하지 않습니다.
- 조건 수집을 생략한 모델 응답은 한 번 재요청하고, 필요한 조회 근거가 없거나 오류가 나면
  안전한 현지화 답변으로 끝냅니다. 검색 답변은 반환된 병원명·가격·리뷰 수만 표시합니다.
- `SELECT_HOSPITAL`은 현재 목록의 실제 ID를 검사한 뒤 승인된 기존 MCP 도구로 병원 대화를
  열고, 실제 UUID·병원 일치·HOSPITAL/HUMAN 모드를 확인합니다. 부모 MAIN은 유지합니다.
  자연어 선택은 여전히 미전송 인계 초안만 준비합니다.

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

Task 4의 AgentState는 `optional_conditions_asked: bool`을 보존하며,
worker는 `action` 원본 camelCase, `conversation_id`, `task_id`를 전달합니다.
`conditions`·`missing`·`candidates`는 기존 snake_case state이고 SSE 변환은 worker 담당입니다.

`SELECT_HOSPITAL`은 `business_open_hospital_conversation(hospital_id, parent_conversation_id)`를
호출합니다. 부모 ID는 현재 `conversation_id`이며 모델이 만들지 않습니다. MCP의 Conversation
응답 `id`·`hospital.id`를 내부 `opened_conversation.conversation_id`·`hospital_id`로 변환하고,
`mode`·`parent_conversation_id`·`consultation_id`·`conditions`는 그대로 보존합니다.
실패·잘못된 선택·자기 자신 ID·다른 병원의 응답에는 `opened_conversation=None`을 반환합니다.
새 자식 thread 초기화와 기존 thread 재사용, 초기화 후 SSE 발행은 task4 worker 담당입니다.
기존 대화의 HUMAN 모드·기존 부모·null 조건도 유효하며 coordinator가 덮어쓰지 않습니다.

2026-10-21 실제 gpt-5-nano + HTTP Business MCP 조회 검증에서 low effort는 도구 생략·
인자 구조 오류·잘못된 시술 선택을 보였습니다. coordinator는 최근 추가했던 low 전달을 제거해
provider 기본 reasoning을 사용합니다. 모델명·키는 기존 Settings를 사용하며 전역 설정은 변경하지 않습니다.
기본 테스트·mock MCP 테스트와 실제 모델 결과를 혼동하지 않도록 실행별 로그와 조건을 보고서에 기록합니다.
예약·취소·상담 요청은 이 coordinator의 범위 밖이며 별도 interrupt 승인 경로가 필요합니다.
Tool A 외부 근거 검색은 미연결 상태입니다.
