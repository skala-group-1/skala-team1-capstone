<script setup lang="ts">
// 「화면 목록」 C9 내 예약 목록 (Figma 1:4462): 탭 전체 · 진행 중(승인 대기·확정 예정) · 지난 예약. 상태 5종 + 홀드 타이머
// 상태 전이는 backend 가 판단 — 여기서는 status 만 보여 줌. 0건이면 AI 상담 시작 (04 ③)
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useReservationStore } from '@/stores/reservation'
import { useNow } from '@/composables/useNow'
import { showToast } from '@/composables/useToast'
import { useNotificationRefresh } from '@/composables/useNotificationRefresh'
import { fmtDateTime, remaining } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge, { RESERVATION_TONE } from '@/components/ui/AppBadge.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import { toApiError } from '@/api'
import type { Reservation } from '@/types/contract'

const router = useRouter()
const { t } = useI18n()
const store = useReservationStore()
const now = useNow()
const tab = ref<'all' | 'active' | 'past'>('all')
const loading = ref(true)
const failed = ref(false)

// 대안 시간이 온 반려 건은 고객이 고를 일이 남아 있으므로 진행 중
const isActive = (r: Reservation) =>
  r.status === 'PENDING' ||
  (r.status === 'REJECTED' && r.alternatives.length > 0) ||
  (r.status === 'CONFIRMED' && new Date(r.slot.startAt).getTime() > now.value)
const list = computed(() =>
  store.mine.filter((r) => (tab.value === 'all' ? true : tab.value === 'active' ? isActive(r) : !isActive(r))),
)
const counts = computed(() => ({
  all: store.mine.length,
  active: store.mine.filter(isActive).length,
  past: store.mine.filter((r) => !isActive(r)).length,
}))

async function load() {
  loading.value = true
  failed.value = false
  try {
    await store.loadMine()
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
// 병원이 승인·반려하거나 만료되면 목록 갱신 (로딩 표시 없이)
useNotificationRefresh(['RESERVATION_CONFIRMED', 'RESERVATION_REJECTED', 'RESERVATION_EXPIRED', 'RESERVATION_CANCELLED'], () => store.loadMine())

// 요청 취소는 슬롯이 풀리는 되돌릴 수 없는 동작 → 확인 후 실행, 처리 중엔 다시 못 누름
const cancelTarget = ref<Reservation | null>(null)
const cancelling = ref(false)
async function cancel() {
  const r = cancelTarget.value
  if (!r || cancelling.value) return
  cancelling.value = true
  try {
    await store.cancel(r.id)
    showToast(t('chat.requested.cancelled'))
  } catch (e) {
    showToast(toApiError(e)?.message || t('common.error'), 'error')
    await store.loadMine().catch(() => undefined)
  } finally {
    cancelling.value = false
    cancelTarget.value = null
  }
}
onMounted(load)
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('reservations.title')" />
    <div class="tabs">
      <AppChip v-for="k in ['all', 'active', 'past'] as const" :key="k" :selected="tab === k" @click="tab = k">
        {{ t(`reservations.tabs.${k}`, { n: counts[k] }) }}
      </AppChip>
    </div>

    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('reservations.loadFailed')">
      <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
    </EmptyState>
    <div v-else-if="loading" class="skeleton-list" role="status" :aria-label="t('common.loading')" aria-busy="true">
      <span v-for="i in 3" :key="i" class="bone" style="height: 120px" />
    </div>
    <EmptyState
      v-else-if="!list.length"
      icon="calendar"
      :title="t('reservations.emptyTitle')"
      :description="t('reservations.emptyBody')"
    >
      <AppButton variant="secondary" @click="router.push('/chat')">{{ t('reservations.startAi') }}</AppButton>
    </EmptyState>

    <ul v-else class="list">
      <li v-for="r in list" :key="r.id">
        <article class="card" :class="{ 'card--muted': r.status === 'EXPIRED' || r.status === 'CANCELLED' }">
          <RouterLink :to="`/reservations/${r.id}`" class="card__main">
            <div class="badges">
              <AppBadge :tone="RESERVATION_TONE[r.status]" dot>{{ t(`domain.status.${r.status}`) }}</AppBadge>
              <AppBadge v-if="r.status === 'PENDING' && remaining(r.holdExpiresAt, now)" tone="warning" icon="clock">
                {{ t('domain.holdLeft', { time: remaining(r.holdExpiresAt, now) }) }}
              </AppBadge>
              <AppIcon name="chevron-right" :size="18" class="chev" />
            </div>
            <p class="t-body-16-sb">{{ r.hospital.name }}</p>
            <p class="t-caption-13 secondary">{{ r.procedure.name }} · {{ fmtDateTime(r.slot.startAt) }}</p>
          </RouterLink>
          <footer class="card__foot t-caption-12">
            <template v-if="r.status === 'PENDING'">
              <span class="muted">{{ t('reservations.pendingNote') }}</span>
              <button type="button" class="act" @click="cancelTarget = r">{{ t('chat.requested.cancel') }}</button>
            </template>
            <template v-else-if="r.status === 'REJECTED'">
              <span class="danger">{{ t('reservations.rejectedNote', { n: r.alternatives.length }) }}</span>
              <RouterLink :to="`/reservations/${r.id}`" class="act brand">{{ t('reservations.seeAlternatives') }}</RouterLink>
            </template>
            <template v-else-if="r.status === 'CONFIRMED'">
              <span class="ok">{{ t('reservations.confirmedNote') }}</span>
              <RouterLink :to="`/reservations/${r.id}`" class="act">{{ t('reservations.visitGuide') }}</RouterLink>
            </template>
            <template v-else-if="r.status === 'EXPIRED'">
              <span class="muted">{{ t('reservations.expiredNote') }}</span>
              <RouterLink :to="`/reservations/${r.id}`" class="act brand">{{ t('reservations.requestAgain') }}</RouterLink>
            </template>
            <span v-else class="muted">{{ t('reservations.cancelledNote') }}</span>
          </footer>
        </article>
      </li>
    </ul>

    <AppDialog :open="!!cancelTarget" :title="t('reservations.cancelTitle')" :body="t('reservations.cancelBody')">
      <template #actions>
        <AppButton variant="secondary" :disabled="cancelling" @click="cancelTarget = null">{{ t('reservations.keep') }}</AppButton>
        <AppButton variant="danger" :loading="cancelling" @click="cancel">{{ t('chat.requested.cancel') }}</AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-subtle); }
.tabs { display: flex; gap: var(--space-8); padding: var(--space-8) var(--space-16) var(--space-12); background: var(--bg-default); }
.list { display: flex; flex-direction: column; gap: var(--space-12); margin: 0; padding: var(--space-16); list-style: none; }
.card { border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.card--muted .card__main { opacity: 0.7; }
.card__main { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-16) var(--space-16) var(--space-8); }
.badges { display: flex; align-items: center; gap: var(--space-8); }
.chev { margin-left: auto; color: var(--icon-subtle); }
.card__foot { display: flex; align-items: center; justify-content: space-between; gap: var(--space-8); padding: 0 var(--space-16) var(--space-16); }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.danger { color: var(--status-danger); }
.ok { color: var(--status-success); }
.brand { color: var(--text-brand); }
.act { flex: none; padding: 0; border: 0; background: none; font-weight: 600; color: var(--text-secondary); }
.act.brand { color: var(--text-brand); }
</style>
