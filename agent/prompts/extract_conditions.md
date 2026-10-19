---
version: 0.1
node: extract_conditions
model: LLM_PRIMARY_MODEL
---

<!-- 03 문서 3장, 12 문서 Conditions: 대화 → 조건 병합 -->

# Task
<!-- TODO(agent): 시술명(자유 텍스트 → normalize 대상), 지역(AreaCode), 입국일(date_from)·출국일(date_to), 예산(KRW), 상담 언어, 정렬 기준 추출 -->

# Rules
<!-- TODO(agent): 상대 날짜('다음 주')는 오늘 날짜(Asia/Seoul) 기준으로 변환, 모르는 값은 null -->

# Output schema
<!-- TODO(agent): Conditions JSON -->
