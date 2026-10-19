<script setup lang="ts">
// 「화면 목록」 C8 예약 시트 (직접 예약)
// TODO(fe): 시술/가격옵션 → 달력 → 시간 슬롯(reservation.loadSlots) → 메모 → 확인
// TODO(fe): 시트 열 때 reservation.startBooking() (멱등키 새로 발급), 확인 → reservation.create()
// TODO(fe): SLOT_UNAVAILABLE → alternatives 로 대안 시간, CONCURRENT_UPDATE → 안내
// TODO(fe): 성공 시 PENDING + '병원 승인 후 확정 / 30분 홀드' 안내 → /reservations
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="C8" title="예약 시트 (직접 예약)" />
</template>
