---
version: 0.1
node: workers/consumer.handle_chat_translate
model: LLM_FAST_MODEL
---

<!-- 03 문서 8장, D-12: 상담 채팅 번역 (고객 언어 ↔ ko) -->

# Glossary
<!-- TODO(agent): data/mock/out/glossary.json 시술 용어집 주입 자리 -->

# Rules
<!-- TODO(agent): 숫자·날짜·금액은 원문 그대로 보존 → 불일치 시 NUMBER_MISMATCH, 의료 판단 질문이면 MEDICAL_QUESTION -->

# Output schema
<!-- TODO(agent): {"translated_text": "...", "flags": [...]} -->
