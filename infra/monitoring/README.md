# 읽기 전용 성능·로그 모니터링

서비스의 기존 코드·프롬프트·루트 Compose를 수정하지 않는다.

```sh
export GRAFANA_ADMIN_PASSWORD='별도 로컬 비밀번호'
export PERF_RESULTS_DIR='/절대경로/측정원자료'
docker compose -f infra/monitoring/compose.yaml up -d
```

- Grafana: http://127.0.0.1:13000/d/capstone-performance (사용자 admin)
- Prometheus: http://127.0.0.1:19090
- Loki: Grafana Explore에서 `{job="capstone-perf"}` 또는 `{job="capstone-perf",service="agent"}`.
- 비밀번호는 환경변수/커밋 제외 환경파일에만 저장한다.

Prometheus는 외부 벤치마크 JSONL에서 계산한 p50/p95·DONE·실패 안내·중복 SSE 수를 수집한다.
버전 `before`/`after`만 포함하고 pilot은 제외한다. 원자료 파일을 중복 복사하면 이중 집계되므로 결과 디렉터리에는 각 실행 파일을 한 번만 둔다.
DONE 지연은 품질 합격 지연이 아니다. 오류 안내도 DONE으로 올 수 있으므로 답변 검토와 함께 사용한다.
현재 앱에는 metrics endpoint를 추가하지 않아 LLM 내부·큐 대기·도구별 지연은 이 화면에서 측정하지 않는다.

Alloy는 Docker socket을 읽어 `capstone-perf` 프로젝트의 stdout만 Loki로 보낸다.
현재 로그에 trace ID가 없다면 추적할 수 없으며, 없는 trace를 생성했다고 주장하지 않는다.
대화 원문 디버그 로깅은 켜지 않는다. Docker socket 접근은 로컬 측정 환경에 한정한다.
Prometheus/Loki 보관 7일, Grafana·측정값은 로컬 접근만 허용한다.

검증: `docker compose -f infra/monitoring/compose.yaml ps`, Prometheus `/api/v1/targets`, Grafana datasource health, Loki query 결과 확인.

공식 구성 참고:
- https://grafana.com/docs/alloy/latest/monitor/monitor-docker-containers/
- https://grafana.com/docs/loki/latest/configure/examples/configuration-examples/
- https://prometheus.io/docs/practices/instrumentation/
