<script setup lang="ts">
// 「화면 목록」 C5 탐색 리스트 (+ C5-1 필터 바텀시트)
// TODO(fe): search.search(query) — 필터: 시술, 지역(다중), 가격 범위(priceMax), 날짜 범위, 언어
// TODO(fe): 정렬 드롭다운 SortBy 4종 (추천 표현 금지, D-01)
// TODO(fe): 병원 카드: 이름, 지역, 최저가(null → '확인 필요'), 평점·리뷰수, 언어 아이콘, 가장 빠른 예약
// TODO(fe): 비교 체크박스 ≤3 → search.toggleCompare(), 비교하기 → /compare
// TODO(fe): 빈 결과 상태
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="C5" title="탐색 리스트 (+ C5-1 필터 바텀시트)" />
</template>
