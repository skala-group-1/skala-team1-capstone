<script setup lang="ts">
// 「화면 목록」 H2 예약 관리
// TODO(fe): hospitalAdminApi.reservations({status, date}) — 상태 필터
// TODO(fe): 요청 카드: 고객 국적, 시술, 일시, 홀드 남은 시간
// TODO(fe): 승인 → approve(id) (CONCURRENT_UPDATE 가능) / 반려 모달: 사유(필수) + 대안 슬롯 최대 3 → reject(id, body)
// TODO(fe): 새 예약 요청 알림은 STOMP
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="H2" title="예약 관리" />
</template>
