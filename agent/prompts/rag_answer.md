---
version: 0.1
node: planner_agent (rag_search_procedure_docs 결과 사용 시)
model: LLM_PRIMARY_MODEL
---

<!-- 03 문서 5장: 질문 + RAG chunk → 근거 인용 답변 (v2 에서는 planner 도구 루프가 사용) -->

# Task
<!-- TODO(agent): chunk 에 있는 내용만으로 답변, 각 문장에 근거(doc_id#section) 연결 -->

# No grounding
<!-- TODO(agent): 검색 결과가 비면 '확인된 문서 없음'으로 답하고 상담사 연결 제안 -->
