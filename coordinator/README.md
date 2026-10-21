# coordinator — 병원 탐색 조율 에이전트

고민을 듣고 사용자가 시술을 선택하면 조건을 누적해 Business MCP로 병원을 검색·비교합니다.
`feat/agent-coordinator`의 상담 흐름을 복원하되 현재 조건 저장·검색·병원 연결을 유지합니다.
`nodes/planner_agent.py`는 기존 Tool A/B 루프를 사용합니다. 상담 질문은 도구 호출 없이
답할 수 있고, 사용자가 준 검색 조건은 `collect_conditions`로 저장합니다.
새 시술명은 실제 정규화 응답의 코드로 확인한 뒤 저장하며,
정규화 실패에도 지역·일정·예산·상담언어는 보존합니다. `extract_conditions`는 이 루프로 진입하게 하고,
누락 조건이 있어도 고민상담 답변을 검색 질문으로 덮어쓰지 않습니다.
‘쌍수’는 ‘쌍꺼풀’로 조회하고, 복수 후보는 실제 명칭을 보여주며 사용자의 선택을 기다립니다.

- [최신 AI 기획](https://app.notion.com/p/AI-3ff5c6f2c23d80d4a269f3cb9f195d55)에 따라
  지역·시술·날짜만 있으면 즉시 검색합니다. 예산·상담 언어·정렬은 선택 조건이며,
  정렬 미지정 시 기존 MCP 기본값인 `REVIEW_COUNT`를 적용합니다.
  서울 전체를 명시하면 `areas: []`, 지역 미입력/null이면 지역을 질문합니다.
  다음 턴에는 입력한 필드만 덮어쓰고, 명시적인 null은 해당 필터를 해제합니다.
- 시술 정규화·검색·비교는 기존 MCP 도구를 호출합니다. 검색은 최대 5개,
  비교는 표시된 병원 중 1~3개이며 가격·시간·미확인 값은 도구 응답을 따릅니다.
- `SET_SORT`는 기존 조건을 유지하고 선택한 정렬을 적용합니다. 조건 변경·0건·검색 실패는
  이전 목록과 선택을 지웁니다. 자동 조건 완화·병원 추천은 하지 않습니다.
- 의료 판단·효과 보장·근거 없는 사실 설명은 프롬프트에서 금지합니다. 조회 없는 답변은
  별도 모델 검사로 상담 질문인지, 시술 근거·병원 조회가 필요한지 확인합니다. 필요한 도구를
  건너뛴 답변은 조회로 되돌리며, 검사 실패 시에는 답변을 차단합니다. 이 검사는 모델 판단에
  의존하고, 도구 결과와 개별 사실을 대조하는 완전한 검증기는 아직 구현되지 않았습니다.
  조회 실패는 현지화된 실패 안내로 끝내고, 미연결된 시술 정보 조회는 확인된 자료가 없음을
  안내합니다. 검색 답변은 표시할 병원 수·정렬 기준만 안내하며, 병원별 정보는 구조화된 카드로 전달합니다.
  시술 미정 상담에 불필요한 의학 설명·자료 없음 안내가 생성되면 상담 질문으로 한 번 다시 작성하고 재검사합니다.
  유행 질문에는 최신 인기 자료가 없다는 안내와 가능한 다음 행동을 전달합니다. 생성된 인기 시술·의학 설명을 내보내거나 이전의 희망 변화 질문을 반복하지 않습니다.
  CLI에서는 카드 데이터를 별도로 출력합니다.
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

웹 확인은 `http://localhost/chat`에서 메인 상단의 `+`(새 대화 시작)를 누릅니다.
새 대화는 새 UUID를 사용하며 기존 기록을 삭제하지 않습니다. 결과의 ‘3곳 비교하기’는
현재 대화에 질문을 보내므로 주소와 대화 맥락이 유지됩니다.
브랜치 코드를 Docker 실행에 반영하려면 저장소 루트에서
`docker compose up -d --build --no-deps agent frontend`를 실행합니다.

기본 테스트는 ScriptedModel과 조회 spy로 필수 조건만으로 검색, 누락 조건 질문,
선택 조건의 유지·변경·해제와 두 턴 조건 유지,
검색·비교·정렬·선택·0건·도구 실패를 검증합니다. 자연어 해석의 실제 LLM 품질이나
실제 DB 연동 성공을 뜻하지 않습니다. opt-in 테스트는 stdio MCP 프로토콜과
mock 검색·비교를 검증하며 실제 backend/DB를 사용하지 않습니다.

## 공유 연결과 남은 범위

AgentState의 기존 `optional_conditions_asked` 값은 검색 여부에 사용하지 않습니다.
worker는 `action` 원본 camelCase, `conversation_id`, `task_id`를 전달합니다.
`conditions`·`missing`·`candidates`는 기존 snake_case state이고 SSE 변환은 worker 담당입니다.

`SELECT_HOSPITAL`은 `business_open_hospital_conversation(hospital_id, parent_conversation_id)`를
호출합니다. 부모 ID는 현재 `conversation_id`이며 모델이 만들지 않습니다. MCP의 Conversation
응답 `id`·`hospital.id`를 내부 `opened_conversation.conversation_id`·`hospital_id`로 변환하고,
`mode`·`parent_conversation_id`·`consultation_id`·`conditions`는 그대로 보존합니다.
실패·잘못된 선택·자기 자신 ID·다른 병원의 응답에는 `opened_conversation=None`을 반환합니다.
새 자식 thread 초기화와 기존 thread 재사용, 초기화 후 SSE 발행은 task4 worker 담당입니다.
기존 대화의 HUMAN 모드·기존 부모·null 조건도 유효하며 coordinator가 덮어쓰지 않습니다.
재사용하는 HOSPITAL 방은 최신 메인 요약을 갱신하며 기존 병원 대화·조건을 보존합니다.
승인 대기나 HUMAN 방은 진행 중인 상담 상태를 보존합니다. 병원 상세에서 직접 만든 방도
첫 메시지 처리 때 같은 사용자 소유의 MAIN 체크포인트에서 조건·고민 요약을 가져옵니다.
부모 체크포인트가 유실된 경우에는 과거 대화를 복구할 수 없습니다.

2026-10-21 실제 gpt-5-nano + HTTP Business MCP 조회 검증에서 low effort는 도구 생략·
인자 구조 오류·잘못된 시술 선택을 보였습니다. coordinator는 최근 추가했던 low 전달을 제거해
provider 기본 reasoning을 사용합니다. 모델명·키는 기존 Settings를 사용하며 전역 설정은 변경하지 않습니다.
기본 테스트·mock MCP 테스트와 실제 모델 결과를 혼동하지 않도록 실행별 로그와 조건을 보고서에 기록합니다.
예약·취소·상담 요청은 이 coordinator의 범위 밖이며 별도 interrupt 승인 경로가 필요합니다.
Tool A 외부 근거 검색은 미연결 상태입니다.
