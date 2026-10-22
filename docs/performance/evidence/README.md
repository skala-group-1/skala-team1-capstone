# 실측 근거

- before-a.jsonl / before-b.jsonl: 개선 직전 agent 179b685, 각각 15회.
- after-formal.jsonl: 개선 후 agent 3a8f4ed, 30회.
- latency-main-2026-10-22.csv: 위 60회에서 추출한 지연·카드·선택지·SSE 개수.
- manifest.json: 비교 경계, 커밋, 이미지 ID, 모델 설정, 런타임, 원본 문서·프롬프트·데이터 해시.
- search-condition-audit.json: 일본어 검색 20회의 API 저장 조건·카드 ID 대조.
- issue-observations.json: 미수정 관찰 사항. 원인별 독립 실험을 수행했다는 뜻이 아니다.
- sse-replay.json: 완료 task의 GET 스트림 2회 재조회. 저장 task 불변·동일 이벤트 확인.
- regression-tests.txt: 관련 기존 테스트 31 passed. 전체 인수시험 대체 아님.
- monitoring-health.json / monitoring.png: Prometheus·Loki 연결과 9개 서비스 로그·대시보드.
- ui-evidence.json / choices-*.png: 실제 브라우저 선택지 클릭 후 단일 POST와 문구 일치.

성능 시간은 API 클라이언트의 POST 직전→SSE 수신 경계이며 브라우저 렌더링 시간은 아니다.
각 시나리오/버전 n=10. nearest-rank p95는 최댓값이며 통계적 일반화를 하지 않는다.
DONE에는 처리 불가 안내가 포함되어 있으므로 전체 완료율과 기능 성공을 구분한다.
본문의 기존 12×3 전체 시험 CSV에 이 별도 실험을 덮어쓰지 않았다.

모든 대화는 합성 입력이다. 인증 토큰·계정 비밀번호·API 키는 포함하지 않는다.
선택지 UI는 본 성능시험 종료 후, 앱의 기존 CORS 허용 주소인 http://localhost:80에서 별도 확인했다.
측정 환경의 18081 포트는 기존 CORS 허용 목록에 없으므로 브라우저 인증 시 403이 발생한다.
기존 앱 설정을 수정하지 않고, 로컬 UI 확인 때만 frontend에 loopback 80 포트를 추가했다.
