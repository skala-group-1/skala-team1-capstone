<script setup lang="ts">
// 「화면 목록」 H1-D 병원 대시보드 (Figma 36:2605): 오늘 예약 · 승인 대기 · 진행 상담 + 최근 요청 5건 (GET /api/hospital-admin/dashboard)
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { hospitalAdminApi } from '@/api'
import { useNow } from '@/composables/useNow'
import { useNotificationRefresh } from '@/composables/useNotificationRefresh'
import { fmtDate, remaining, seoulDate } from '@/utils/format'
import KpiCard from '@/components/staff/KpiCard.vue'
import ReservationTable from '@/components/staff/ReservationTable.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import type { HospitalDashboard } from '@/types/contract'

const router = useRouter()
const { t } = useI18n()
const now = useNow()
const data = ref<HospitalDashboard | null>(null)
const failed = ref(false)

const soonest = computed(() =>
  data.value?.recentRequests
    .filter((r) => r.status === 'PENDING' && r.holdExpiresAt)
    .sort((a, b) => a.holdExpiresAt!.localeCompare(b.holdExpiresAt!))[0] ?? null,
)
const soonUnder5 = computed(() => {
  const s = soonest.value
  return !!s && new Date(s.holdExpiresAt!).getTime() - now.value < 5 * 60_000
})

async function load() {
  failed.value = false
  try {
    data.value = await hospitalAdminApi.dashboard()
  } catch {
    failed.value = true
  }
}
onMounted(load)
// 새 예약 요청·취소·만료가 오면 KPI·최근 요청 갱신
useNotificationRefresh(['RESERVATION_REQUESTED', 'RESERVATION_CANCELLED', 'RESERVATION_EXPIRED'], load)
</script>

<template>
  <div class="page">
    <header class="title">
      <h1 class="t-title-22">{{ t('staff.nav.dashboard') }}</h1>
      <p class="t-body-14 secondary">{{ fmtDate(seoulDate()) }}</p>
    </header>
    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('staff.loadFailed')">
      <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
    </EmptyState>
    <div v-else-if="!data" class="skeleton-list" role="status" :aria-label="t('common.loading')" aria-busy="true">
      <span class="bone" style="height: 96px" /><span class="bone" style="height: 240px" />
    </div>
    <template v-else>
      <div class="kpis">
        <KpiCard :label="t('staff.kpi.today')" :value="data.todayReservations" :sub="t('staff.kpi.todaySub', { date: fmtDate(seoulDate()) })" />
        <KpiCard
          :label="t('staff.kpi.pending')"
          :value="data.pendingReservations"
          :warn="soonUnder5"
          :sub="soonest ? t('staff.kpi.soonest', { name: soonest.customer?.name ?? '', time: remaining(soonest.holdExpiresAt, now) ?? '0:00' }) : t('staff.kpi.hold')"
        />
        <KpiCard :label="t('staff.kpi.consultations')" :value="data.activeConsultations" />
      </div>
      <div class="section-head">
        <h2 class="t-title-18">{{ t('staff.recent') }}</h2>
        <RouterLink to="/hospital-admin/reservations" class="t-caption-13 link">{{ t('staff.goReservations') }} <AppIcon name="chevron-right" :size="16" /></RouterLink>
      </div>
      <ReservationTable
        v-if="data.recentRequests.length"
        :rows="data.recentRequests"
        :footer="t('staff.recentFoot', { n: data.recentRequests.length })"
        @select="(r) => router.push({ path: '/hospital-admin/reservations', query: { id: r.id } })"
      />
      <EmptyState v-else icon="calendar" :title="t('staff.recentEmpty')" />
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: var(--space-20); padding: var(--space-32); }
.title { display: flex; flex-direction: column; gap: var(--space-4); }
.secondary { color: var(--text-secondary); }
.kpis { display: flex; gap: var(--space-16); }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-top: var(--space-8); }
.link { display: inline-flex; align-items: center; gap: 2px; color: var(--text-secondary); }
</style>
