# aftercare — 시술 사후관리 에이전트

승인 대기·확정 예약 1건마다 열리는 사후관리 대화방(`mode=AFTERCARE`)을 담당합니다.
병원 상담(`concierge/`)과 별도 대화방이며, 실행 프로세스·큐·State는 `../agent/`를 함께 씁니다.

- 그날 안내: backend가 방을 열 때 그날(Asia/Seoul) 안내가 없으면 `AFTERCARE_INTRO`(처음) 또는
  `AFTERCARE_DAILY`(다른 날 첫 방문) 작업을 보냅니다. 시술 전에는 `doc_type=PREP` 문서
  (`data/mock/rag_docs/prep/`)로 1주 전·2일 전·전날·당일 준비를, 시술 후에는 `doc_type=AFTERCARE` 문서
  (`data/mock/rag_docs/aftercare/`)로 기간별 관리를 사용자 언어로 요약합니다. 경과일 문장과 제목은 코드가 고정합니다.
- 예약이 반려·취소·만료되면 방은 남고, 안내·질문에는 종료 안내 고정 문구로 답합니다.
- 질문: RAG(시술 문서·병원 FAQ), 병원 정보, 내 예약 조회만 사용합니다. 예약 생성·취소 도구는 주지 않습니다.
- 이상 증상: 출혈·발열·호흡곤란·시야 변화·피부색 변화·심한 통증 등 키워드(ko/en/zh/ja)를 감지하면
  모델을 거치지 않고 고정 안전 문구(병원 이름·전화번호, 119·응급실 안내, 상담사 연결 제안)를 보냅니다.
- 상담사 연결: concierge의 요약 카드 준비 → 승인 interrupt → MCP 상담 요청을 그대로 재사용합니다.
  승인되면 같은 방이 `HUMAN`이 되고, 상담이 끝나면 backend가 `AFTERCARE`로 되돌립니다.

| 파일 | 역할 |
| --- | --- |
| `nodes/load_aftercare_context.py` | 예약을 MCP로 다시 조회해 본인·병원 일치 확인, 종료 여부, 시술일 기준 경과일(시술 전 음수) 계산 |
| `nodes/red_flag.py` | 이상 증상 감지와 고정 안전 문구 |
| `nodes/aftercare_agent.py` | 그날 안내(시술 전 준비/시술 후 관리), 질문 도구 루프, 상담사 연결 카드 준비 |
| `graph.py` | 서브그래프 (도구·승인·실행 노드는 concierge 재사용) |
| `prompts/` | 첫 안내·질문 응답 지침 |

```bash
cd agent
uv run --frozen pytest -c pyproject.toml -q ../aftercare/tests
```
