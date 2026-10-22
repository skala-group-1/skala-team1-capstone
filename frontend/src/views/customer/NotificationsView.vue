<script setup lang="ts">
// 「화면 목록」 C10 알림 (Figma 1:6618): 날짜별 묶음, 안 읽은 것 강조, 모두 읽음, 종류별 바로가기. 실시간은 STOMP /user/queue/notifications
// payload 는 {reservationId} 등 id 만 있어서 내 예약 목록으로 병원·시술·일시를 채움
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '@/stores/notification'
import { useReservationStore } from '@/stores/reservation'
import { useAuthStore } from '@/stores/auth'
import { fmtDate, fmtDateTime, fmtTime, seoulDate } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import AppIcon, { type IconName } from '@/components/ui/AppIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import type { Notification, NotificationType } from '@/types/contract'

const router = useRouter()
const { t } = useI18n()
const store = useNotificationStore()
const reservations = useReservationStore()
const auth = useAuthStore()

const META: Record<NotificationType, { icon: IconName; tone: string }> = {
  RESERVATION_REQUESTED: { icon: 'calendar', tone: 'info' },
  RESERVATION_CONFIRMED: { icon: 'check', tone: 'success' },
  RESERVATION_REJECTED: { icon: 'x', tone: 'danger' },
  RESERVATION_EXPIRED: { icon: 'clock', tone: 'muted' },
  RESERVATION_CANCELLED: { icon: 'x', tone: 'muted' },
  CONSULTATION_REQUESTED: { icon: 'message-circle', tone: 'info' },
  CONSULTATION_ACCEPTED: { icon: 'headphones', tone: 'info' },
  CONSULTATION_CLOSED: { icon: 'message-circle', tone: 'muted' },
  AFTERCARE_MESSAGE: { icon: 'file-text', tone: 'success' },
}
const today = seoulDate()
const yesterday = seoulDate(new Date(Date.now() - 86400000))
const groups = computed(() => {
  const map = new Map<string, Notification[]>()
  for (const n of store.items) {
    const d = seoulDate(n.createdAt)
    map.set(d, [...(map.get(d) ?? []), n])
  }
  return [...map.entries()].map(([d, items]) => ({
    label: d === today ? t('notifications.today') : d === yesterday ? t('notifications.yesterday') : fmtDate(d),
    items,
  }))
})
function detail(n: Notification) {
  const id = n.payload.reservationId as number | undefined
  const r = id ? reservations.mine.find((x) => x.id === id) : undefined
  return r ? `${r.hospital.name} · ${r.procedure.name} · ${fmtDateTime(r.slot.startAt)}` : ''
}
function target(n: Notification): { to: string; label: string } | null {
  const rid = n.payload.reservationId
  switch (n.type) {
    case 'RESERVATION_CONFIRMED':
      return { to: `/reservations/${rid}`, label: t('notifications.actions.visit') }
    case 'RESERVATION_REJECTED':
      return { to: `/reservations/${rid}`, label: t('notifications.actions.alternatives') }
    case 'RESERVATION_EXPIRED':
      return { to: `/reservations/${rid}`, label: t('reservations.requestAgain') }
    case 'RESERVATION_REQUESTED':
      return { to: '/hospital-admin/reservations', label: t('notifications.actions.review') }
    case 'CONSULTATION_REQUESTED':
      return { to: '/counselor', label: t('notifications.actions.inbox') }
    case 'CONSULTATION_ACCEPTED':
      return n.payload.conversationId ? { to: `/chat/${n.payload.conversationId}`, label: t('notifications.actions.chat') } : null
    case 'AFTERCARE_MESSAGE':
      return n.payload.conversationId ? { to: `/chat/${n.payload.conversationId}`, label: t('notifications.actions.aftercare') } : null
    default:
      return null
  }
}
async function open(n: Notification) {
  if (!n.readAt) void store.markRead(n.id).catch(() => undefined)
  const to = target(n)?.to
  if (to) await router.push(to)
}
onMounted(() => {
  void store.load().catch(() => undefined)
  if (auth.role === 'CUSTOMER') void reservations.loadMine().catch(() => undefined)
})
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('notifications.title')" back />
    <EmptyState v-if="!store.items.length" icon="bell" :title="t('notifications.emptyTitle')" :description="t('notifications.emptyBody')" />
    <template v-for="g in groups" :key="g.label">
      <header class="group t-caption-12">
        <span class="muted">{{ g.label }}</span>
        <button v-if="g === groups[0] && store.unread" type="button" class="read-all" @click="store.readAll()">{{ t('notifications.readAll') }}</button>
      </header>
      <ul class="list">
        <li v-for="n in g.items" :key="n.id">
          <button type="button" class="item" :class="{ 'item--unread': !n.readAt }" @click="open(n)">
            <span class="icon-wrap" :class="`tone--${META[n.type].tone}`"><AppIcon :name="META[n.type].icon" :size="18" /></span>
            <span class="text">
              <span class="row">
                <span class="t-body-14-sb">{{ t(`notifications.types.${n.type}`) }}</span>
                <span class="t-caption-12 muted">{{ fmtTime(n.createdAt) }}</span>
              </span>
              <span v-if="detail(n)" class="t-caption-13 secondary">{{ detail(n) }}</span>
              <span class="t-caption-13 secondary">{{ t(`notifications.bodies.${n.type}`) }}</span>
              <span v-if="target(n)" class="t-caption-13 link">{{ target(n)!.label }}</span>
            </span>
          </button>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100dvh; }
.group { display: flex; justify-content: space-between; padding: var(--space-12) var(--space-16) var(--space-4); }
.muted { color: var(--text-tertiary); }
.secondary { color: var(--text-secondary); }
.read-all { padding: 0; border: 0; background: none; color: var(--text-primary); font-weight: 600; }
.list { margin: 0; padding: 0; list-style: none; }
.item { position: relative; display: flex; gap: var(--space-12); width: 100%; padding: var(--space-16); border: 0; background: none; text-align: left; }
.item--unread { background: var(--brand-subtle); }
.item--unread::before { content: ''; position: absolute; left: 6px; top: 50%; width: 6px; height: 6px; border-radius: 50%; background: var(--brand-primary); }
.icon-wrap { display: grid; place-items: center; flex: none; width: 36px; height: 36px; border-radius: 50%; }
.tone--success { background: var(--status-success-bg); color: var(--status-success); }
.tone--danger { background: var(--status-danger-bg); color: var(--status-danger); }
.tone--info { background: var(--status-info-bg); color: var(--status-info); }
.tone--muted { background: var(--bg-muted); color: var(--text-secondary); }
.text { display: flex; flex: 1; flex-direction: column; gap: var(--space-2); }
.row { display: flex; justify-content: space-between; gap: var(--space-8); }
.link { margin-top: var(--space-4); color: var(--text-brand); font-weight: 600; }
</style>
