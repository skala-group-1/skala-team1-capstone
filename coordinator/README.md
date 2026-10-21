# coordinator — 병원 탐색 조율 에이전트

병원 선택 전 시술 정보·병원 조회를 조율하고, 사용자 조건과 병원 선택 결과를 정리합니다.
`nodes/`는 그래프 노드와 도구, `prompts/`는 이 역할의 지침, `tests/`는 역할별 테스트입니다.

- `planner_agent.py`: Tool A `procedure_consultation` / Tool B `hospital_lookup` 호출 루프
- `coordinator_tools.py`: Business MCP 조회·검색 조건·미전송 인계 요약
- 조건 수집·가드·기억·검증·병원 대화 열기 노드도 이 폴더에서 관리합니다.

공통 의존성·State·Harness·MCP·그래프 조립은 `../agent/`를 사용합니다.
Python namespace package이며 저장소 루트를 `PYTHONPATH`에 포함합니다. 별도 큐 소비자는 없습니다.
실행 방법과 남은 연동 제한은 [공통 런타임 문서](../agent/README.md)를 참고하세요.

```bash
# 저장소 루트에서
cd agent
uv sync --frozen
uv run --frozen pytest -c pyproject.toml ../coordinator/tests -q
PYTHONPATH=.. uv run --frozen python -m coordinator.nodes.planner_agent --locale en
```

대화 명령은 실제 LLM을 사용합니다. 현재 Tool A 외부 검색·병원 대화 생성은 미연결이며,
인계 요약은 미전송 초안입니다. 조회에는 기존 mock Business MCP를 사용합니다.
