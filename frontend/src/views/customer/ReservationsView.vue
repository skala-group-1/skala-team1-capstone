<script setup lang="ts">
// 08 문서 C9 내 예약
// TODO(fe): reservation.loadMine() — 상태 배지 5종(PENDING·CONFIRMED·REJECTED·EXPIRED·CANCELLED)
// TODO(fe): PENDING: 홀드 남은 시간 카운트다운(holdExpiresAt)
// TODO(fe): REJECTED: 반려 사유 + 대안 시간 선택 → reservation.acceptAlternative()
// TODO(fe): 취소 → reservation.cancel(), CONFIRMED: 방문 안내
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="C9" title="내 예약" />
</template>
