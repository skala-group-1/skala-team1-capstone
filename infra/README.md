# 서비스 통합 확인

`#27~32` 변경을 포함하는 통합 checkout에서 실행합니다. 개별 기능 브랜치나 이전 main에서는 전체 흐름이 통과하지 않을 수 있습니다. 기존 실행 환경과 같은 Compose 프로젝트를 동시에 띄우지 마세요.

## 기동·MCP

루트 `.env.example`을 참고해 `.env`와 LLM 키를 설정합니다. 기존 `.env`를 덮어쓰거나 DB 볼륨을 삭제할 필요는 없습니다.

```sh
docker compose up -d --build
docker compose ps
docker compose exec -T business-mcp python /infra/check_mcp.py http://localhost:9101/mcp
docker compose exec -T rag-mcp python /infra/check_mcp.py http://localhost:9102/mcp
```

상시 서비스 9개가 healthy인지 확인합니다. 공개 포트는 frontend 80, backend 8080입니다. MCP는 Compose 내부에서 열리며 위 명령은 실제 HTTP 초기화와 도구 목록 조회를 수행합니다. `db-seed`는 별도 실행하는 일회성 서비스입니다.

## 실제 채팅·DB·SSE

Python 3.11+ 표준 라이브러리만 사용합니다. 먼저 고객 전용 테스트 계정을 가입하고 자격 증명을 환경변수로 설정합니다. 비밀번호를 명령 기록에 남기지 않는 예시(zsh/bash):

```sh
export SMOKE_EMAIL='테스트 고객 이메일'
export SMOKE_PASSWORD="$(python3 -c 'import getpass; print(getpass.getpass("테스트 계정 비밀번호: "))')"
python3 infra/smoke_service_flow.py --self-test
python3 infra/smoke_service_flow.py
unset SMOKE_PASSWORD
```

기본 주소는 `http://localhost`이며 필요하면 `SMOKE_BASE_URL`을 설정합니다. `python -O`는 검사문을 끄므로 사용하지 않습니다. 스크립트는 실제 LLM을 호출하므로 API 비용과 대기 시간이 발생합니다.

- MAIN 두 턴으로 모호한 시술·상담언어를 임의 확정하지 않는지, 후속 조건·병원 카드·메시지가 저장되는지 확인합니다.
- 선택 버튼과 같은 action을 보내 MCP 병원 대화 생성, 부모 조건 복사, 병원 가격 질문과 응답 저장을 확인합니다. 이미 열린 병원은 기존 대화·조건·메시지를 보존해야 합니다.
- 모든 작업의 SSE 순번 중복·역전, DONE과 저장된 작업 상태를 검사합니다. 실패는 종료 코드 1이며 마지막 TASK ID로 backend/agent 로그를 찾습니다.
- 토큰·비밀번호·전체 대화 내용은 출력하지 않습니다. 실행할 때마다 MAIN 대화와 메시지가 추가되고 병원 대화를 생성하거나 재사용합니다. 승인·예약·상담 접수는 자동 실행하지 않으며 생성 기록도 자동 삭제하지 않습니다.

`PASS`와 두 브라우저 주소가 나오면 같은 계정으로 로그인하여 다음을 확인합니다.

1. MAIN 대화에서 병원 카드와 조건 칩 표시 → 새로고침해도 빈 화면이 되지 않음.
2. 병원 카드의 상담 버튼 → 해당 병원 제목·조건 표시 → 새로고침 후 가격 질문·답변 유지.
3. 예약 버튼 → 날짜·시간 선택 → 승인 카드 확인. 거절 시 예약이 생기지 않고, 승인 시 한 건만 생성되는지 확인.
4. 상담사 연결 → 요약 공유 승인 → 해당 병원 상담사 계정의 목록·한국어 요약·번역 채팅 확인.
5. 승인 대기 중 agent 재시작 후 재개, 상담 종료 후 AI 복귀도 별도로 확인.

## 이번 검증 결과와 범위

- 이 스크립트 실서비스 실행 PASS: MAIN 2턴 11.94초/17.80초, 병원 12 대화 생성 0.05초, 가격 답변 4.74초. 새 부모 조건 복사와 메시지 저장 확인. SSE 파서 자체 검사도 통과.
- 에이전트 결합 테스트 210 passed / 3 opt-in skipped. MCP 테스트 40 passed / 4 opt-in skipped. 실제 HTTP 도구 조회·호출, 큐·SSE·조건 복사·대화 DB 저장 통과.
- 실제 예약 요청·동일 키 재시도·취소와 요약 승인 후 상담 접수는 에이전트 실행/API로 확인했습니다. 상담사 화면의 한국어 요약 표시도 확인했습니다.
- 전체 예약 승인/상담 전환의 브라우저 연속 흐름, 상담 종료 후 AI 복귀는 아직 완료하지 않았습니다. 위 수동 항목의 성공을 이 스크립트의 PASS로 대신 판단하지 않습니다.
- 실제 모델의 조건 해석은 매번 같다고 보장하지 않습니다. 실패 시 TASK ID와 조건을 확인하고 모델 오류와 서비스 연결 오류를 구분합니다. 브라우저 재진입 수정은 #32에 포함됩니다.
