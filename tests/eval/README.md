# AI 출력 품질 평가

검증 결과서 4쪽·19~26쪽·33쪽의 평가셋, 전후 응답 원문, 판정 기록입니다.

| 파일 | 내용 |
| --- | --- |
| [quality-set-v2.1.json](quality-set-v2.1.json) | 고정 20문항의 입력·언어·유형·기대 결과·근거·병원 ID |
| [quality-before.jsonl](quality-before.jsonl) | Phase1의 실제 응답 60건: 20문항 × 3회 |
| [quality-after.jsonl](quality-after.jsonl) | 개선 후 실제 응답 60건: 20문항 × 3회 |
| [quality-review.json](quality-review.json) | 120응답의 개별 판정, 문항별 충족 횟수, 전후 집계 |

## 평가 조건

- 실행일: 2026-10-23
- 모델: `gpt-5-nano`
- 프롬프트: `P-PHASE1` → `P-FINAL-0.8`
- 평가셋: v2.1, 답 가능 15문항·답 불가 2문항·실패 유도 3문항
- 언어: 영어 15문항·중국어 3문항·일본어 2문항
- 데이터: seed 42 고정 시연 데이터, 병원 1 FAQ `HOSPITAL_FAQ_001 v1`
- 비교 환경: 업무 서버·MCP·DB·FAQ·입력을 고정하고 AI 코드·프롬프트를 교체
- 개별 판정: 문항별 기대 사실·언어·자료 부족 처리·정보 보호 조건을 응답 원문과 대조한 Codex 판정
- 문항 집계: 동일 문항의 3회 중 2회 이상 충족 시 문항 충족

## 결과

| 집계 | 개선 전 | 개선 후 |
| --- | --- | --- |
| 개별 응답 충족 | 46/60 (76.7%) | 58/60 (96.7%) |
| 문항 충족: 3회 중 2회 이상 | 15/20 (75%) | 20/20 (100%) |
| 문항 충족: 3회 모두 | 15/20 (75%) | 18/20 (90%) |

과반 집계 기준은 실행 후 개정해 전후 응답에 동일하게 적용했습니다. 원자료의 개별 판정은 유지했습니다. 집계 규칙은 `quality-review.json`의 `aggregation_rule`, 개별 판정은 `run_reviews`, 문항별 결과는 `rows`에서 확인할 수 있습니다.

개선 후 Q-17·Q-18의 개별 응답 충족은 각각 2/3입니다. 출처 반환은 별도 확인 항목으로, 개선 후 답 가능 45응답 중 출처 포함 15건·빈 배열 30건입니다.

## 원자료 읽는 순서

1. 평가셋에서 문항의 `id`, `input`, `expected`, `source`를 확인합니다.
2. 전후 JSONL에서 같은 `id`의 `repeat` 1~3을 찾습니다. `result.answer`는 응답 원문, `result.sources`는 실제 반환 출처입니다. `events`에는 SSE 이벤트가 기록돼 있습니다.
3. 판정 기록의 `run_reviews`에서 `id`·`version`·`repeat`로 해당 응답의 `review_result`와 `review_reason`을 확인합니다.
4. `rows`의 문항별 충족 횟수와 전체 집계를 대조합니다.

## 기록 대조

저장소 루트에서 Python 표준 라이브러리로 문항·반복·판정·집계의 일치를 확인할 수 있습니다.

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

p = Path('tests/eval')
questions = json.loads((p / 'quality-set-v2.1.json').read_text())
review = json.loads((p / 'quality-review.json').read_text())
assert len(questions) == 20
ids = {q['id'] for q in questions}
assert len(ids) == 20
assert len(review['run_reviews']) == 120
for version, expected in [('before', 46), ('after', 58)]:
    runs = [json.loads(s) for s in (p / f'quality-{version}.jsonl').read_text().splitlines() if s.strip()]
    assert len(runs) == 60
    keys = {(r['id'], r['repeat']) for r in runs}
    assert keys == {(qid, repeat) for qid in ids for repeat in (1, 2, 3)}
    judged = [r for r in review['run_reviews'] if r['version'] == version]
    assert len(judged) == 60
    assert {(r['id'], r['repeat']) for r in judged} == keys
    passed = Counter(r['id'] for r in judged if r['review_result'] == '충족')
    assert sum(passed.values()) == expected == review['response_counts'][version]
    assert sum(passed[qid] >= 2 for qid in ids) == review['question_counts'][version]
    assert sum(passed[qid] == 3 for qid in ids) == review['all_three_counts'][version]
    print(version, f'응답 {expected}/60', f'문항 {review["question_counts"][version]}/20')
PY
```
