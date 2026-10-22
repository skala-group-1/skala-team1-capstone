# 변경 근거와 비교 버전

조사 시 원격 main: `3a8f4ed3a4471be9e05268280da1be44b1acde16`.
어제 마지막 first-parent main: `1a2bee70f94f8fcb6e14bc40a47cb2f5bfc9b765`.
이는 시간 기준 후보이며 제출 PDF의 정확한 빌드 SHA로 입증된 값은 아니다.

| 변경 | 커밋 | 코드 근거 | 보고서에 쓸 수 있는 주장 |
|---|---|---|---|
| 응답 속도 | 3cf5526 | coordinator/nodes/planner_agent.py, agent/app/workers/consumer.py | 내부 ReplyReview 제거, 도구 병렬 실행, user-facing 스트리밍, reasoning 설정 적용 |
| 주제별 첫 대화·흐름 | db02558 | coordinator/nodes/planner_agent.py, coordinator/prompts/coordinator.md, agent/app/graph/builder.py | 주제 context 전달, SKIN_CONCERN 첫 질문의 정적 분기, 외부 verify 경로 제거 |
| 선택지 클릭 | 09bf6a7 | coordinator/nodes/suggest_choices.py, agent/app/workers/consumer.py | DONE.suggestions에 최대 4개 선택지; FE의 기존 클릭 전송과 연결 |
| 화면 전송 | 조사 기준 main | frontend/src/views/customer/ChatView.vue, frontend/src/stores/conversation.ts | 선택지를 누르면 문구 전송; 실제 브라우저 검증과 정적 구현 확인을 구분 |

속도 변경 직전은 `179b685f86edaf3a510ec9ef44c1a1deac405bce`이다.
이 버전과 현재 main의 비교는 여러 변경의 **합산 효과**다. 검수 제거·병렬화 각각의 기여율로 해석하지 않는다.
각 버전의 프롬프트는 원래 커밋 그대로 실행하며 이번 작업에서는 편집하지 않는다.
선택지 커밋 설명의 '평균 0.8초'는 원자료 미확인으로 성과 수치에서 제외한다.

## 중복 처리 조사

동일 taskId 재전달, 서로 다른 taskId의 중복 접수, SSE 재수신, 동일 도구 반복,
동일 문장을 의도적으로 재질문한 경우를 구분한다. 동일 문장 자체는 중복 판단 근거가 아니다.
기존 worker는 완료 task 결과를 재전송하며 coordinator는 턴 내 동일 도구/인자를 제한한다.
이 구현의 존재만으로 모든 경합·재시작 상황의 멱등성을 보장한다고 쓰지 않는다.

## 검증 루프의 정확한 구분

`179b685`의 coordinator/nodes/verify.py는 항상 passed=True를 반환하는 자리표시자이며 LLM을 호출하지 않는다.
실제 검수 LLM은 coordinator/nodes/planner_agent.py의 ReplyReview 경로에 있으며, 재작성 후 재검수가 가능하다.
따라서 SSE VERIFY 이벤트 수는 내부 검수 LLM 호출 횟수가 아니다. 바깥 verify 삭제 자체를 수십 초 개선 원인으로 설명하지 않는다.
선택지 FE 구현 커밋은 `f36aba9`이며 agent 전송 커밋 `09bf6a7`과 함께 설명한다.

측정 중 원격 main이 `5cc408c`(frontend polish)로 전진한 것을 확인했다. 실험 도중 코드를 섞지 않고 `3a8f4ed`를 고정했다. 후속 main 전체의 성능이라고 일반화하지 않는다.
