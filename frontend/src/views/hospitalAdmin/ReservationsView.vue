<script setup lang="ts">
// 「화면 목록」 H2-D 예약 관리 (Figma 2:9235) + H2-1-D 반려 모달 + Edge H2-D 만료(39:2637) + 승인 Toast · 필터 0건 (04 ③)
// 표(상태 필터·검색·만료 임박순) + 오른쪽 상세 패널(400). 승인 직전 슬롯 재검사는 backend — 409 면 Toast + 새로고침
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { hospitalAdminApi, toApiError } from '@/api'
import { useNow } from '@/composables/useNow'
import { showToast } from '@/composables/useToast'
import { useNotificationRefresh } from '@/composables/useNotificationRefresh'
import { fmtDate, fmtDateTime, fmtKrw, remaining, seoulDate } from '@/utils/format'
import KpiCard from '@/components/staff/KpiCard.vue'
import ReservationTable from '@/components/staff/ReservationTable.vue'
import RejectModal from '@/components/staff/RejectModal.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge, { RESERVATION_TONE } from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import type { RejectRequest, Reservation, ReservationStatus } from '@/types/contract'

const route = useRoute()
const { t, locale } = useI18n()
const now = useNow()

const all = ref<Reservation[]>([])
const failed = ref(false)
const loading = ref(true)
const filter = ref<ReservationStatus>('PENDING')
const q = ref('')
const selectedId = ref<number | null>(route.query.id ? Number(route.query.id) : null)
const busy = ref<'approve' | 'reject' | null>(null)
const rejectOpen = ref(false)

/** 홀드가 지난 PENDING 은 화면에서 만료로 취급 (backend 스케줄러가 1분 주기로 EXPIRED 처리) */
const effective = (r: Reservation): ReservationStatus =>
  r.status === 'PENDING' && (!r.holdExpiresAt || new Date(r.holdExpiresAt).getTime() <= now.value) ? 'EXPIRED' : r.status
const STATUSES: ReservationStatus[] = ['PENDING', 'CONFIRMED', 'REJECTED', 'CANCELLED', 'EXPIRED']
const counts = computed(() => Object.fromEntries(STATUSES.map((s) => [s, all.value.filter((r) => effective(r) === s).length])) as Record<ReservationStatus, number>)
const rows = computed(() => {
  const text = q.value.trim().toLowerCase()
  return all.value
    .filter((r) => effective(r) === filter.value)
    .filter((r) => !text || r.customer?.name.toLowerCase().includes(text) || `r-${String(r.id).padStart(4, '0')}`.includes(text))
    .sort((a, b) => (filter.value === 'PENDING' ? (a.holdExpiresAt ?? '').localeCompare(b.holdExpiresAt ?? '') : a.slot.startAt.localeCompare(b.slot.startAt)))
})
const selected = computed(() => all.value.find((r) => r.id === selectedId.value) ?? null)
const pending = computed(() => all.value.filter((r) => effective(r) === 'PENDING'))
const soon = computed(() => pending.value.filter((r) => new Date(r.holdExpiresAt!).getTime() - now.value < 5 * 60_000))
const today = computed(() => all.value.filter((r) => r.status === 'CONFIRMED' && seoulDate(r.slot.startAt) === seoulDate()).length)
const nation = (code?: string) => (code ? new Intl.DisplayNames([locale.value], { type: 'region' }).of(code) : '')

async function load() {
  failed.value = false
  try {
    all.value = (await hospitalAdminApi.reservations({ size: 50 })).items
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
async function approve() {
  if (!selected.value) return
  busy.value = 'approve'
  try {
    const r = await hospitalAdminApi.approve(selected.value.id)
    replace(r)
    showToast(t('staff.toast.approved'))
  } catch (e) {
    const code = toApiError(e)?.code
    showToast(code === 'INVALID_STATE_TRANSITION' ? t('staff.toast.expired') : code === 'CONCURRENT_UPDATE' ? t('staff.toast.concurrent') : t('common.error'), 'error')
    await load()
  } finally {
    busy.value = null
  }
}
async function reject(body: RejectRequest) {
  if (!selected.value) return
  busy.value = 'reject'
  try {
    replace(await hospitalAdminApi.reject(selected.value.id, body))
    rejectOpen.value = false
    showToast(t('staff.toast.rejected'))
  } catch {
    showToast(t('common.error'), 'error')
    await load()
  } finally {
    busy.value = null
  }
}
function replace(r: Reservation) {
  const i = all.value.findIndex((x) => x.id === r.id)
  if (i >= 0) all.value[i] = { ...all.value[i], ...r }
}
// 새 예약 요청·고객 취소·만료가 오면 목록 갱신. 열어 둔 상세(selectedId)는 그대로 유지
useNotificationRefresh(['RESERVATION_REQUESTED', 'RESERVATION_CANCELLED', 'RESERVATION_EXPIRED'], load)

onMounted(async () => {
  await load()
  if (selected.value) filter.value = effective(selected.value)
})
watch(filter, () => {
  if (selected.value && effective(selected.value) !== filter.value) selectedId.value = null
})
</script>

<template>
  <div class="layout">
    <div class="main">
      <header class="title">
        <h1 class="t-title-22">{{ t('staff.nav.reservations') }}</h1>
        <p class="t-body-14 secondary">{{ t('staff.reservations.sub') }}</p>
      </header>
      <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('staff.loadFailed')">
        <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
      </EmptyState>
      <template v-else>
        <div class="kpis">
          <KpiCard :label="t('staff.kpi.pending')" :value="counts.PENDING" :sub="t('staff.kpi.hold')" />
          <KpiCard
            :label="t('staff.kpi.soon')"
            :value="soon.length"
            :warn="soon.length > 0"
            :sub="soon[0] ? `${soon[0].customer?.name} · ${t('domain.holdLeft', { time: remaining(soon[0].holdExpiresAt, now) })}` : t('staff.kpi.noneSoon')"
          />
          <KpiCard :label="t('staff.kpi.today')" :value="today" :sub="t('staff.kpi.todaySub', { date: fmtDate(seoulDate()) })" />
        </div>
        <div class="toolbar">
          <AppChip v-for="s in STATUSES" :key="s" :selected="filter === s" @click="filter = s">{{ t(`domain.status.${s}`) }} {{ counts[s] }}</AppChip>
          <span class="spacer" />
          <label class="search">
            <AppIcon name="search" :size="16" />
            <input v-model="q" class="t-caption-13" :placeholder="t('staff.reservations.search')" :aria-label="t('staff.reservations.search')" />
          </label>
        </div>
        <ReservationTable
          v-if="rows.length"
          :rows="rows"
          :selected-id="selectedId"
          :footer="t('staff.reservations.foot', { status: t(`domain.status.${filter}`), n: rows.length })"
          @select="(r) => (selectedId = r.id)"
        />
        <EmptyState
          v-else-if="!loading"
          :icon="filter === 'EXPIRED' ? 'clock' : 'calendar'"
          :title="t('staff.reservations.emptyTitle', { status: t(`domain.status.${filter}`) })"
          :description="filter === 'EXPIRED' ? t('staff.reservations.emptyExpired') : ''"
        />
      </template>
    </div>

    <!-- 상세 패널 -->
    <aside v-if="selected" class="panel">
      <header class="panel__head">
        <h2 class="t-body-16-sb">{{ t('staff.reservations.detail', { no: `R-${String(selected.id).padStart(4, '0')}` }) }}</h2>
        <button type="button" class="x" :aria-label="t('common.close')" @click="selectedId = null"><AppIcon name="x" :size="20" /></button>
      </header>
      <div class="cust">
        <span class="avatar t-body-16-sb">{{ selected.customer?.name.slice(0, 1) }}</span>
        <div>
          <p class="t-title-18">{{ selected.customer?.name }}</p>
          <p class="t-caption-12 muted">{{ nation(selected.customer?.nationality) }} · {{ selected.customer ? t(`domain.lang.${selected.customer.locale}`) : '' }}</p>
        </div>
      </div>
      <div class="badges">
        <AppBadge :tone="RESERVATION_TONE[effective(selected)]" dot>{{ t(`domain.status.${effective(selected)}`) }}</AppBadge>
        <AppBadge v-if="effective(selected) === 'PENDING'" tone="danger" icon="clock">{{ t('domain.holdLeft', { time: remaining(selected.holdExpiresAt, now) }) }}</AppBadge>
      </div>
      <hr />
      <dl class="kv">
        <div><dt>{{ t('booking.procedure') }}</dt><dd>{{ selected.procedure.name }}</dd></div>
        <div><dt>{{ t('booking.when') }}</dt><dd>{{ fmtDateTime(selected.slot.startAt) }}</dd></div>
        <div><dt>{{ t('booking.doctor') }}</dt><dd>{{ selected.slot.doctorName }}</dd></div>
        <div>
          <dt>{{ t('booking.option') }}</dt>
          <dd>{{ selected.priceOption ? `${fmtKrw(selected.priceOption.priceKrw)} · ${selected.priceOption.product} · ${selected.priceOption.vatIncluded ? t('compare.vatIn') : t('compare.vatEx')}` : t('common.needsCheck') }}</dd>
        </div>
        <div v-if="selected.rejectReason"><dt>{{ t('reservations.rejectReason') }}</dt><dd>{{ selected.rejectReason }}</dd></div>
      </dl>
      <div v-if="selected.note" class="memo">
        <p class="t-caption-12 muted">{{ t('staff.reservations.memo') }}</p>
        <p class="t-body-15">“{{ selected.note }}”</p>
      </div>
      <span class="fill" />
      <p v-if="effective(selected) === 'EXPIRED' && selected.status === 'PENDING'" class="notice t-caption-13">
        <AppIcon name="info" :size="16" />{{ t('staff.reservations.expiredNotice') }}
      </p>
      <p v-else-if="effective(selected) === 'PENDING'" class="notice t-caption-13"><AppIcon name="info" :size="16" />{{ t('staff.reservations.notice') }}</p>
      <div v-if="selected.status === 'PENDING'" class="actions">
        <AppButton variant="outline" size="l" block :disabled="effective(selected) !== 'PENDING' || !!busy" @click="rejectOpen = true">{{ t('staff.reservations.reject') }}</AppButton>
        <AppButton size="l" block :disabled="effective(selected) !== 'PENDING'" :loading="busy === 'approve'" @click="approve">{{ t('staff.reservations.approve') }}</AppButton>
      </div>
    </aside>

    <RejectModal :open="rejectOpen" :reservation="selected" :busy="busy === 'reject'" @close="rejectOpen = false" @submit="reject" />
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100%; }
.main { display: flex; flex: 1; flex-direction: column; gap: var(--space-20); min-width: 0; padding: var(--space-32); }
.title { display: flex; flex-direction: column; gap: var(--space-4); }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.kpis { display: flex; gap: var(--space-16); }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-8); }
.spacer { flex: 1; }
.search { display: flex; align-items: center; gap: var(--space-6); width: 220px; height: 36px; padding: 0 var(--space-12); border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--bg-default); color: var(--icon-subtle); }
.search input { flex: 1; min-width: 0; border: 0; outline: none; color: var(--text-primary); }
.panel { position: sticky; top: 0; display: flex; flex: none; flex-direction: column; gap: var(--space-16); width: 400px; height: calc(100dvh - var(--staff-top-h)); padding: var(--space-24); border-left: 1px solid var(--border-default); background: var(--bg-default); overflow-y: auto; }
.panel__head { display: flex; align-items: center; justify-content: space-between; }
.x { border: 0; background: none; color: var(--icon-subtle); }
.cust { display: flex; align-items: center; gap: var(--space-12); }
.avatar { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 50%; background: var(--bg-muted); color: var(--text-secondary); }
.badges { display: flex; gap: var(--space-8); }
hr { width: 100%; height: 1px; margin: 0; border: 0; background: var(--border-default); }
.kv { display: flex; flex-direction: column; gap: var(--space-12); margin: 0; }
.kv div { display: grid; grid-template-columns: 64px 1fr; font: 600 14px/20px var(--font-sans); }
.kv dt { font-weight: 500; color: var(--text-tertiary); }
.kv dd { margin: 0; }
.memo { display: flex; flex-direction: column; gap: var(--space-8); padding: var(--space-16); border-radius: var(--radius-md); background: var(--bg-subtle); }
.fill { flex: 1; }
.notice { display: flex; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); background: var(--status-info-bg); color: var(--status-info); }
.actions { display: flex; gap: var(--space-8); }
</style>
