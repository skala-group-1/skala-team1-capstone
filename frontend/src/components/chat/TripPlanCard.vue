<script setup lang="ts">
// SSE TRIP_PLAN 일정 카드 (04 ④ C4 제안): 입국 → 시술 → 회복 예상일(다운타임) → 출국(여유일). 계산은 backend plan_trip
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '../ui/AppIcon.vue'
import AppBadge from '../ui/AppBadge.vue'
import { fmtDate, fmtHm } from '@/utils/format'
import type { SseEventMap } from '@/types/contract'

const props = defineProps<{ plan: SseEventMap['TRIP_PLAN']; procedureName: (code: string) => string }>()
const { t } = useI18n()

const nights = computed(() => {
  const ms = new Date(props.plan.departureDate).getTime() - new Date(props.plan.arrivalDate).getTime()
  return Math.round(ms / 86400000)
})
const main = computed(() => props.plan.plans[0] ?? null)
</script>

<template>
  <section class="card">
    <header class="head">
      <AppIcon name="calendar" :size="20" class="brand" />
      <h3 class="t-body-16-sb">{{ t('chat.trip.title') }}</h3>
      <AppBadge tag>{{ t('chat.trip.nights', { n: nights, d: nights + 1 }) }}</AppBadge>
    </header>
    <ol class="rows">
      <li class="row"><span class="t-caption-13 when">{{ fmtDate(plan.arrivalDate) }}</span><span class="t-body-14">{{ t('chat.trip.arrival') }}</span></li>
      <li v-if="main?.slot" class="row row--brand">
        <span class="t-caption-13 when">{{ fmtDate(main.slot.startAt) }} {{ fmtHm(main.slot.startAt) }}</span>
        <span class="t-body-14">{{ main.hospitalName }} · {{ procedureName(main.procedureCode) }}</span>
      </li>
      <li v-if="main?.recoveryEndDate" class="row">
        <span class="t-caption-13 when">{{ fmtDate(main.recoveryEndDate) }}</span>
        <span class="t-body-14">{{ t('chat.trip.recovery', { n: main.downtimeDays }) }}</span>
      </li>
      <li class="row">
        <span class="t-caption-13 when">{{ fmtDate(plan.departureDate) }}</span>
        <span class="t-body-14" :class="{ warn: main && !main.feasible }">
          {{ main?.bufferDays != null ? t('chat.trip.departureBuffer', { n: main.bufferDays }) : t('chat.trip.departure') }}
        </span>
      </li>
    </ol>
    <p class="foot t-caption-12">{{ t('chat.trip.note') }}</p>
  </section>
</template>

<style scoped>
.card { display: flex; flex-direction: column; gap: var(--space-12); width: 100%; padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.head { display: flex; align-items: center; gap: var(--space-8); }
.head h3 { flex: 1; }
.brand { color: var(--brand-primary); }
.rows { display: flex; flex-direction: column; gap: var(--space-12); margin: 0; padding: 0; list-style: none; }
.row { display: grid; grid-template-columns: 110px 1fr; gap: var(--space-12); }
.when { color: var(--text-secondary); }
.row--brand .when, .row--brand span:last-child { color: var(--brand-text); font-weight: 600; }
.warn { color: var(--status-warning); font-weight: 600; }
.foot { color: var(--text-tertiary); }
</style>
