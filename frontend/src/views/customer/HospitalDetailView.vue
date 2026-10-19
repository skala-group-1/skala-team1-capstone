<script setup lang="ts">
// 08 문서 C7 병원 상세
// TODO(fe): catalogApi.hospital(id) — 탭: 시술·가격 / 의료진 / 리뷰(통계+목록, catalogApi.reviews) / 정보(운영시간·주소·언어)
// TODO(fe): 하단 고정: '이 병원에 물어보기(AI)' → conversation.open(hospitalId) (이미 열린 대화면 그것) / '예약하기' → /hospitals/:id/book
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="C7" title="병원 상세" />
</template>
