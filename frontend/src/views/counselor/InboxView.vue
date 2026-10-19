<script setup lang="ts">
// 「화면 목록」 S1 상담사 문의함
// TODO(fe): consultation.loadInbox(status) — 탭: 대기(WAITING)/진행(ACTIVE)/종료(CLOSED)
// TODO(fe): 카드: 고객 국적·언어, 시술, 희망일, 대기시간 (고객 이름은 마스킹된 값 그대로)
// TODO(fe): 수락 → consultation.accept(id) → /counselor/consultations/:id
// TODO(fe): 새 상담 알림은 STOMP /user/queue/notifications
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="S1" title="상담사 문의함" />
</template>
