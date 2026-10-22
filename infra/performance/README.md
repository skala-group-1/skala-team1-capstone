# 非侵襲 성능 측정

애플리케이션·프롬프트를 편집하지 않는 외부 API/SSE 측정이다.
별도 프로젝트는 기존 DB와 분리되며 18080/18081을 사용한다.

```sh
docker compose -p capstone-perf -f docker-compose.yml -f infra/performance/compose.yaml up -d --no-build
python3 infra/performance/benchmark.py --self-test
PERF_ACCOUNTS_FILE=/path/to/private-accounts.json python3 infra/performance/benchmark.py --version after --commit <SHA> --repeats 10 --output /tmp/capstone-perf/after.jsonl
```

계정은 합성 테스트 고객을 사용한다. 자격 증명은 환경변수로만 전달한다.
각 실행마다 새 MAIN 대화를 생성한다. 예약·상담 승인 API는 호출하지 않는다.
시간은 작업 POST 직전부터 SSE 수신까지이며 브라우저 렌더링 시간은 포함하지 않는다.
동시성은 1이다. 중복 SSE ID와 transport 실패를 기록한다. DONE은 내용 품질 통과와 다르다.
원자료 출력에 토큰·비밀번호를 포함하지 않는다. 합성 질문/답변·task ID만 저장한다.

비교 시 backend·MCP·DB는 고정하고 agent 이미지/원본 코드만 교체한다면 반드시
**고정 인프라에서 에이전트 버전 비교**라고 보고한다. 전체 과거 서비스 재현이라고 표현하지 않는다.
선택지·검수·reasoning·병렬화 변경은 함께 포함되므로 개별 효과로 분해하지 않는다.

계정 파일은 locale별 {"en":{"email":"...","password":"..."},...} 형태다. JWT의 locale이 시나리오와 일치해야 한다.
