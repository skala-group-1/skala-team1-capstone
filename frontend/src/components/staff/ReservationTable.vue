<script setup lang="ts">
// H1-D 최근 요청 · H2-D 요청 표: 고객(마스킹) · 시술·번호 · 희망 일시·의료진 · 남은 시간(승인 대기) / 상태
import { useI18n } from 'vue-i18n'
import AppBadge, { RESERVATION_TONE } from '../ui/AppBadge.vue'
import { useNow } from '@/composables/useNow'
import { fmtDateTime, remaining } from '@/utils/format'
import type { Reservation } from '@/types/contract'

defineProps<{ rows: Reservation[]; selectedId?: number | null; footer?: string }>()
defineEmits<{ select: [r: Reservation] }>()
const { t, locale } = useI18n()
const now = useNow()

const nation = (code?: string) => (code ? new Intl.DisplayNames([locale.value], { type: 'region' }).of(code) : '')
const holdTone = (r: Reservation) => {
  const ms = r.holdExpiresAt ? new Date(r.holdExpiresAt).getTime() - now.value : 0
  return ms < 5 * 60_000 ? 'danger' : 'warning'
}
</script>

<template>
  <div class="table" role="table">
    <div class="tr th t-caption-12-sb" role="row">
      <span role="columnheader">{{ t('staff.table.customer') }}</span>
      <span role="columnheader">{{ t('staff.table.procedure') }}</span>
      <span role="columnheader">{{ t('staff.table.when') }}</span>
      <span role="columnheader">{{ t('staff.table.status') }}</span>
    </div>
    <button
      v-for="r in rows"
      :key="r.id"
      type="button"
      role="row"
      class="tr td"
      :class="{ 'td--on': r.id === selectedId }"
      @click="$emit('select', r)"
    >
      <span class="cust">
        <span class="avatar t-caption-12-sb">{{ r.customer?.name.slice(0, 1) }}</span>
        <span>
          <span class="t-body-14-sb">{{ r.customer?.name }}</span>
          <span class="t-caption-12 muted">{{ nation(r.customer?.nationality) }} · {{ r.customer ? t(`domain.lang.${r.customer.locale}`) : '' }}</span>
        </span>
      </span>
      <span>
        <span class="t-body-14-sb">{{ r.procedure.name }}</span>
        <span class="t-caption-12 muted">R-{{ String(r.id).padStart(4, '0') }}</span>
      </span>
      <span>
        <span class="t-body-14-sb">{{ fmtDateTime(r.slot.startAt) }}</span>
        <span class="t-caption-12 muted">{{ r.slot.doctorName }}</span>
      </span>
      <span>
        <AppBadge v-if="r.status === 'PENDING' && remaining(r.holdExpiresAt, now)" :tone="holdTone(r)" icon="clock">
          {{ t('domain.holdLeft', { time: remaining(r.holdExpiresAt, now) }) }}
        </AppBadge>
        <AppBadge v-else :tone="RESERVATION_TONE[r.status === 'PENDING' ? 'EXPIRED' : r.status]" dot>
          {{ t(`domain.status.${r.status === 'PENDING' ? 'EXPIRED' : r.status}`) }}
        </AppBadge>
      </span>
    </button>
    <p v-if="footer" class="foot t-caption-12">{{ footer }}</p>
  </div>
</template>

<style scoped>
.table { overflow: hidden; border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.tr { display: grid; grid-template-columns: 1.2fr 1fr 1.1fr 140px; align-items: center; gap: var(--space-16); width: 100%; padding: var(--space-12) var(--space-20); border: 0; border-top: 1px solid var(--border-default); background: none; text-align: left; }
.tr > span { display: flex; flex-direction: column; min-width: 0; }
.th { border-top: 0; background: var(--bg-subtle); color: var(--text-secondary); }
.td { position: relative; cursor: pointer; }
.td:hover { background: var(--bg-subtle); }
.td--on { background: var(--brand-subtle); }
.td--on::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--brand-primary); }
.cust { flex-direction: row !important; align-items: center; gap: var(--space-12); }
.cust > span:last-child { display: flex; flex-direction: column; }
.avatar { display: grid; place-items: center; flex: none; width: 32px; height: 32px; border-radius: 50%; background: var(--bg-muted); color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.foot { padding: var(--space-12) var(--space-20); border-top: 1px solid var(--border-default); color: var(--text-tertiary); }
</style>
