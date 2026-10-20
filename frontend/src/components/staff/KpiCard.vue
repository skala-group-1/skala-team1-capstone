<script setup lang="ts">
// H1-D · H2-D KPI 카드 (승인 대기 · 5분 안에 만료 · 오늘 예약 · 진행 상담). warn = 주황 강조
defineProps<{ label: string; value: number | string; sub?: string; warn?: boolean }>()
</script>

<template>
  <div class="kpi" :class="{ 'kpi--warn': warn }">
    <span class="t-caption-13 label">{{ label }}</span>
    <span class="t-display-28">{{ value }}</span>
    <span v-if="sub" class="t-caption-12 sub">{{ sub }}</span>
  </div>
</template>

<style scoped>
.kpi { display: flex; flex: 1; flex-direction: column; gap: var(--space-4); min-width: 0; padding: var(--space-20); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.label, .sub { color: var(--text-secondary); }
.kpi--warn { border-color: var(--status-warning); background: var(--status-warning-bg); }
.kpi--warn .label, .kpi--warn .sub, .kpi--warn .t-display-28 { color: var(--status-warning); }
</style>
