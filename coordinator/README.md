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
- 의료 판단·효과 보장·근거 없는 사실 설명은 프롬프트에서 금지합니다.
  별도 답변 검토 AI와 항상 통과하던 verify 노드는 제거했습니다.
  `procedure_consultation`은 OpenAI Responses 웹 검색으로 일반 시술 정보를 조회합니다.
  검색된 답변은 출처 링크를 보존해 전달하며, 추가 모델 재작성은 하지 않습니다.
  완료된 검색과 허용 도메인의 인용 출처가 없으면 자료 부족 안내로 종료합니다.
  메인은 RAG를 사용하지 않으며 병원 서브에이전트의 RAG 도구는 유지합니다.
  병원 검색 답변은 병원 수·정렬 기준과 카드로 전달합니다.
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
외부 시술 검색은 기존 OPENAI_API_KEY를 사용합니다.
PROCEDURE_SEARCH_MODEL(기본 gpt-4.1-mini), PROCEDURE_SEARCH_TIMEOUT_SECONDS(기본 45),
PROCEDURE_SEARCH_DOMAINS(의료 학회·공공 보건·의료기관 교육 사이트)로 설정합니다.
이 모델은 API의 filters 옵션을 지원하지 않아 site 검색어와 지침으로 범위를 제한하고,
반환된 모든 인용 URL의 도메인을 코드로 재검사합니다. 전체 주장에 대한 임상적 사실 검증을 뜻하지 않습니다.
웹 검색은 별도 API 비용이 발생하며, 실제 모델/외부 검색 검증과 대역 테스트를 구분합니다.
프론트의 일반 텍스트 말풍선에서는 Markdown 출처 링크가 문자열로 보일 수 있습니다.
