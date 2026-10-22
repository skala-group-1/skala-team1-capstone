# concierge — 선택 병원 상담 에이전트

사용자가 선택한 병원의 정보·FAQ를 조회하고 예약 의사를 수집해 승인 카드를 준비합니다.
예약·취소·상담사 연결은 사용자 승인 후 기존 MCP 경로로 실행합니다.

리뷰 질문에는 `business_get_hospital_reviews`로 선택 병원의 최신 리뷰를 조회합니다.
기본 5개, 최대 10개씩 페이지 조회하며 원문 언어 필터는 사용자가 요청할 때만 적용합니다.
조회한 표본 수와 전체 일치 건수를 구분하고, 개인 경험을 의료적 사실이나 병원 추천 근거로 사용하지 않습니다.
병원 ID는 도구 실행 직전에도 상담방의 선택 병원으로 강제합니다.

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

CLI 대화에는 LLM 키와 MCP 실행 환경이 필요합니다. 웹 승인 재개와 HUMAN 전환은
공통 런타임의 승인 처리 및 이벤트 연결을 함께 적용해야 합니다.


## 승인 후 변경 실행

`hospital_agent`는 예약·취소·상담을 실행하지 않고 `pending_action`을 준비합니다.
예약은 선택 병원의 의사·가격·슬롯을 MCP로 재확인하고, 취소는 본인 예약 조회에서
선택 병원 일치를 확인합니다. `approval`의 LangGraph interrupt 승인 전에는 변경
도구를 호출하지 않습니다. 수정 허용 필드는 예약 `note`, 취소 `reason`뿐입니다.
병원·슬롯·가격·요약 변경은 새 제안과 승인이 필요합니다.
한 사용자 메시지에서는 승인 카드를 한 번만 처리합니다. 승인·거절·실행 오류 이후에는
변경 도구를 모델에 제공하지 않으며, 새로운 사용자 메시지에서만 다시 허용합니다.
승인 ID 없는 현재 resume 계약에서 중복 승인으로 다음 변경이 실행되는 것을 막습니다.

상담은 `SUMMARIZER_URL`의 `POST /summarize`에 고객 발화와 확인된 조건을 보내고
응답 카드를 먼저 표시합니다. 이 카드 확인과 병원 공유 동의를 함께 승인한 경우만
MCP 상담 요청을 실행합니다. 현재 summarizer/MCP 계약의 지원 언어는 en/zh/ja이며,
지원하지 않는 언어 또는 요약 오류는 인계 성공으로 처리하지 않습니다.
성공 결과의 상담 ID와 `mode=HUMAN`은 공통 그래프·worker가 종료 및 MODE_CHANGED로 연결합니다.

예약·상담 idempotency key는 conversation/task/tool-call에 묶어서 생성하고 승인
체크포인트에 보존합니다. MCP 취소 계약에는 idempotency key 인자가 없으므로 추가하지
않습니다. 정상 worker 중복 배달 방지는 공통 런타임 책임이며, 취소 도중 프로세스가
중단된 경우 backend 결과를 재조회해야 합니다. 오류 결과는 성공으로 표시하지 않고,
슬롯 충돌은 새 슬롯 조회 → 고객 선택 → 새 승인으로 처리합니다.

검증 (외부 서비스·업무 DB 변경 없음):

```sh
cd agent
uv run pytest ../concierge/tests/test_approved_actions.py ../concierge/tests/test_hospital_agent.py -q
uv run pytest -q
```

`test_approved_actions.py`는 mock MCP와 실제 LangGraph interrupt/resume으로 승인 전
0회·승인 후 1회·거절 0회, 인자 변조 차단, 중복 키, 오류·요약 실패·동의 검증을 확인합니다.
실제 업무 DB 예약/취소/상담 검증은 별도 승인된 데이터 범위에서 수행해야 합니다.

## 메인 → 병원 인계 로그

로컬 `.env`에서 `HANDOFF_DEBUG_LOG=true`로 설정하고 agent를 재생성하면
서버 터미널에 `MAIN_TO_HOSPITAL` JSON 로그가 출력됩니다.
`docker logs -f skala-hospital-chat-agent-1`로 확인할 수 있습니다.
로그에는 실제 저장한 병원 대화 ID, 병원 ID, 조건, 인계 요약이 포함됩니다.
`initialized`는 새 상태 저장, `summary_refreshed`는 요약 갱신,
`preserved`는 기존 상태 유지(승인 대기 포함)를 뜻합니다.
사용자 발언 원문을 포함하므로 기본값은 false이며, 확인 후 다시 끕니다.
