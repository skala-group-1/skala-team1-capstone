# 성능 검증 기록과 실행 안내

성능 측정 결과는 docs/performance/에 별도로 축적한다. 제출용 PDF·HTML 및 생성 스크립트는 이번 PR에서 제외한다. 보고서 일괄 반영은 후속 요청 시 진행한다.

비교 코드는 3a8f4ed에 고정했다. 병합 대상 main의 후속 변경까지 측정한 결과는 아니다.

## 모니터링

Grafana: http://127.0.0.1:13000/d/capstone-performance (사용자 admin)
Prometheus: http://127.0.0.1:19090
로그: Grafana Explore → Loki → `{job="capstone-perf",service="agent"}`.
로컬 로그인 비밀번호·원자료 경로는 `infra/monitoring/.env`에 저장했다(mode 600, Git 제외).

```sh
docker compose --env-file infra/monitoring/.env -f infra/monitoring/compose.yaml up -d
```

원자료는 /tmp 대신 저장소 docs/performance/evidence/에서 읽는다. 표시는 합성 실험 집계이며
일반 서비스 트래픽 전체의 성능 지표가 아니다. 기존 앱에 LLM/큐 내부 계측을 추가하지 않았다.

## 반복 측정 재현

실제 모델 호출 비용이 발생한다. 별도 측정 프로젝트·합성 계정과 빈 결과 디렉터리를 사용한다.
현재 원자료를 덮어쓰거나 이전 JSONL을 복사해 중복 집계하지 않는다.

```sh
git archive 179b685 | tar -x -C /이미_만든_비교용_빈_디렉터리
docker build -f /비교용_디렉터리/agent/Dockerfile -t capstone-perf-agent:before /비교용_디렉터리
docker compose -p capstone-perf -f docker-compose.yml -f infra/performance/compose.yaml up -d --no-build
PERF_ACCOUNTS_FILE=/비공개/계정.json python3 infra/performance/benchmark.py \
  --version after --commit 3a8f4ed --repeats 10 --output /새결과/after-formal.jsonl
```

현재 서비스 이미지는 3a8f4ed에서 빌드한 이미지다. 다른 환경에서는 해당 커밋을 따로 추출해
기존 Dockerfile로 이미지를 빌드하고 manifest의 이미지/의존성/데이터 해시를 비교한다.
기준 측정은 별도 override의 `services.agent.image: capstone-perf-agent:before`를 지정해
agent만 `up -d --no-deps --no-build --wait agent`로 교체한다. 진행 중 작업 없이 전환한다.
순서: before 5회씩 → after 준비 1회씩 + 본 10회씩 → before 준비 1회씩 + 본 5회씩.
각 버전 첫 시작의 준비 실행도 별도 제외했고, 최종 환경은 after 이미지로 복구했다.

계정 JSON은 locale별 로그인 자격 증명이다. JWT locale을 확인하므로 Accept-Language만 바꾸지 않는다.
별도 측정 frontend의 18081은 기존 CORS 허용 주소가 아니다. 실제 UI 검증은 본 시험 후
frontend에 loopback 80 포트를 추가하고 기존 허용 주소 http://localhost를 사용했다.
CORS·앱 코드 변경이나 브라우저 응답 mocking은 하지 않았다.

## 관련 PR 의존성

계획 PR 병합 후 이 결과 PR의 기준을 main으로 변경한다. 반복 실행에는 test/infra-performance-benchmark, 대시보드에는 feat/infra-monitoring 변경이 필요하다.

현재 저장소 코드로 이미지를 다시 빌드하면 역사적 실험 재현이 아니다. manifest의 고정 커밋·이미지 해시와 비교해야 한다.
