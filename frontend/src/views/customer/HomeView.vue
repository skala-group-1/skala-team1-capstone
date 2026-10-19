<script setup lang="ts">
// 08 문서 C3 홈
// TODO(fe): AI 상담 진입 CTA → conversation.open() 후 /chat/:id
// TODO(fe): 검색바·시술 카테고리(피부/성형) → search.loadProcedures(), /explore 로 이동
// TODO(fe): 내 예약 요약 → reservation.loadMine()
// TODO(fe): 하단 탭(홈·탐색·AI·예약·내정보) 은 App.vue 레이아웃으로
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="C3" title="홈" />
</template>
