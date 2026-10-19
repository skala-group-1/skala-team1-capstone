<script setup lang="ts">
// 「화면 목록」 C6 비교표
// TODO(fe): search.loadCompare(procedureCode) — 최대 3열
// TODO(fe): 행: 가격 옵션(제품·용량·VAT·조건), 언어, 최조 예약, 리뷰수·평점, 확인일
// TODO(fe): null 값은 '확인 필요' 로 표시 (「공통 계약서」 1장)
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="C6" title="비교표" />
</template>
