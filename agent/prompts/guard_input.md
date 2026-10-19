---
version: 0.1
node: guard_input
model: LLM_FAST_MODEL
---

<!-- 「AI Agent 설계」 5장·7장: 마지막 사용자 메시지 → {intent, guard_flags} structured output -->

# Task
<!-- TODO(agent): intent 1개 분류 — SEARCH | INFO | PLAN | SELECT | HOSPITAL_QA | BOOK | HANDOFF | OTHER -->

# Guard flags
<!-- TODO(agent): RECOMMEND_REQUEST / MEDICAL_JUDGMENT / GUARANTEE / OFF_TOPIC / INJECTION 정의와 언어별 예시 (「AI Agent 설계」 7장 표) -->

# Output schema
<!-- TODO(agent): {"intent": "...", "guard_flags": [...]} -->
