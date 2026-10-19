<script setup lang="ts">
// 「화면 목록」 S2 통역 채팅
// TODO(fe): consultation.open(id) — REST 히스토리 + STOMP 구독
// TODO(fe): 상단 한국어 요약 카드(summaryCard, 접기)
// TODO(fe): 메시지: 번역문 우선 + 원문 토글, ⚠️ 플래그(NUMBER_MISMATCH / MEDICAL_QUESTION), 번역 실패 → 재시도
// TODO(fe): 입력창 → consultation.send(text), 상담 종료 → consultation.finish(id)
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="S2" title="통역 채팅" />
</template>
