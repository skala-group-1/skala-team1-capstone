<script setup lang="ts">
// 「화면 목록」 C3 홈 (Figma 1:3213): AI 상담 CTA(크게) · 검색바 · 내 예약 요약 · 시술 카테고리(피부/성형)
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useSearchStore } from '@/stores/search'
import { useReservationStore } from '@/stores/reservation'
import { useNotificationStore } from '@/stores/notification'
import { useNow } from '@/composables/useNow'
import { useNotificationRefresh } from '@/composables/useNotificationRefresh'
import { fmtDateTime, remaining } from '@/utils/format'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge, { RESERVATION_TONE } from '@/components/ui/AppBadge.vue'
import type { ProcedureCategory } from '@/types/contract'

const router = useRouter()
const { t } = useI18n()
const auth = useAuthStore()
const search = useSearchStore()
const reservations = useReservationStore()
const notifications = useNotificationStore()
const now = useNow()

const ask = ref('')
const category = ref<ProcedureCategory>('SURGERY')
const procedures = computed(() => search.procedures.filter((p) => p.category === category.value))
/** 진행 중 예약 하나 (승인 대기 → 다가오는 확정 순). 없으면 섹션 숨김 */
const upcoming = computed(
  () =>
    reservations.mine.find((r) => r.status === 'PENDING') ??
    reservations.mine
      .filter((r) => r.status === 'CONFIRMED' && new Date(r.slot.startAt).getTime() > now.value)
      .sort((a, b) => a.slot.startAt.localeCompare(b.slot.startAt))[0] ??
    null,
)

function startChat() {
  const q = ask.value.trim()
  void router.push(q ? { path: '/chat', query: { q } } : '/chat')
}

// 병원이 승인·반려하거나 만료되면 '내 예약' 카드 갱신
useNotificationRefresh(['RESERVATION_CONFIRMED', 'RESERVATION_REJECTED', 'RESERVATION_EXPIRED', 'RESERVATION_CANCELLED'], () => reservations.loadMine())

onMounted(() => {
  void search.loadProcedures().catch(() => undefined)
  void reservations.loadMine().catch(() => undefined)
  void notifications.load().catch(() => undefined)
})
</script>

<template>
  <div class="page">
    <header class="bar">
      <span class="logo">
        <img class="logo__mark" src="/favicon.svg" alt="" width="28" height="28" />
        {{ t('app.brand') }}
      </span>
      <RouterLink to="/notifications" class="bell" :aria-label="t('home.notifications')">
        <AppIcon name="bell" />
        <span v-if="notifications.unread" class="bell__dot" />
      </RouterLink>
    </header>

    <section class="hello">
      <p class="t-body-14 secondary">{{ t('home.hello', { name: auth.user?.name ?? '' }) }}</p>
      <h1 class="t-title-22">{{ t('home.title') }}</h1>
    </section>

    <form class="cta" @submit.prevent="startChat">
      <div class="cta__head">
        <span class="cta__icon"><AppIcon name="sparkles" /></span>
        <div>
          <p class="t-title-18">{{ t('home.ctaTitle') }}</p>
          <p class="t-caption-12 cta__sub">{{ t('home.ctaBody') }}</p>
        </div>
      </div>
      <label class="cta__input">
        <span class="sr-only">{{ t('home.ctaTitle') }}</span>
        <input v-model="ask" class="t-body-14" :placeholder="t('home.ctaPlaceholder')" />
        <button type="submit" :aria-label="t('chat.send')"><AppIcon name="send" :size="20" /></button>
      </label>
    </form>

    <RouterLink to="/explore" class="search t-body-14">
      <AppIcon name="search" :size="20" />
      <span>{{ t('home.searchPlaceholder') }}</span>
    </RouterLink>

    <section v-if="upcoming" class="section">
      <header class="section__head">
        <h2 class="t-body-16-sb">{{ t('home.myReservation') }}</h2>
        <RouterLink to="/reservations" class="t-caption-13 secondary">{{ t('home.all') }}</RouterLink>
      </header>
      <RouterLink to="/reservations" class="resv">
        <div class="resv__badges">
          <AppBadge :tone="RESERVATION_TONE[upcoming.status]" dot>{{ t(`domain.status.${upcoming.status}`) }}</AppBadge>
          <AppBadge v-if="upcoming.status === 'PENDING' && remaining(upcoming.holdExpiresAt, now)" tone="warning" icon="clock">
            {{ t('domain.holdLeft', { time: remaining(upcoming.holdExpiresAt, now) }) }}
          </AppBadge>
          <AppIcon name="chevron-right" :size="18" class="resv__chev" />
        </div>
        <p class="t-body-16-sb">{{ upcoming.hospital.name }}</p>
        <p class="t-caption-13 secondary">{{ upcoming.procedure.name }} · {{ fmtDateTime(upcoming.slot.startAt) }}</p>
      </RouterLink>
    </section>

    <section class="section">
      <header class="section__head">
        <h2 class="t-body-16-sb">{{ t('home.categories') }}</h2>
        <RouterLink to="/explore" class="t-caption-13 secondary">{{ t('home.seeAll') }}</RouterLink>
      </header>
      <div class="segment" role="tablist">
        <button
          v-for="c in ['SKIN', 'SURGERY'] as const"
          :key="c"
          type="button"
          role="tab"
          class="segment__tab t-body-14"
          :class="{ 'segment__tab--on': category === c }"
          :aria-selected="category === c"
          @click="category = c"
        >
          {{ t(`home.category.${c}`) }}
        </button>
      </div>
      <div class="procs">
        <RouterLink v-for="p in procedures" :key="p.code" :to="{ path: '/explore', query: { procedure: p.code } }" class="proc t-body-14">
          {{ p.name }}
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: var(--space-20); padding: 0 var(--space-16) var(--space-24); }
.bar { display: flex; align-items: center; justify-content: space-between; height: var(--app-bar-h); margin: 0 4px; }
.logo { display: inline-flex; align-items: center; gap: var(--space-8); font: 700 22px/30px var(--font-sans); letter-spacing: -0.3px; color: var(--brand-primary); }
.logo__mark { display: block; flex: none; }
.bell { position: relative; color: var(--icon-default); }
.bell__dot { position: absolute; top: 0; right: 1px; width: 8px; height: 8px; border: 1.5px solid var(--bg-default); border-radius: 50%; background: var(--status-danger-solid); }
.hello { display: flex; flex-direction: column; gap: var(--space-2); margin-top: -8px; }
.secondary { color: var(--text-secondary); }
.cta { display: flex; flex-direction: column; gap: var(--space-16); padding: var(--space-20); border-radius: var(--radius-xl); background: var(--brand-primary); color: var(--text-inverse); }
.cta__head { display: flex; gap: var(--space-12); }
.cta__icon { display: grid; place-items: center; flex: none; width: 40px; height: 40px; border-radius: var(--radius-md); background: rgb(255 255 255 / 18%); }
.cta__sub { opacity: 0.85; }
.cta__input { display: flex; align-items: center; height: 44px; padding: 0 var(--space-12) 0 var(--space-16); border-radius: var(--radius-md); background: var(--bg-default); color: var(--text-primary); }
.cta__input input { flex: 1; min-width: 0; border: 0; background: none; outline: none; }
.cta__input input::placeholder { color: var(--text-secondary); }
.cta__input button { display: grid; place-items: center; border: 0; background: none; color: var(--brand-primary); }
.search { display: flex; align-items: center; gap: var(--space-8); height: 48px; padding: 0 var(--space-16); border-radius: var(--radius-md); background: var(--bg-muted); color: var(--text-tertiary); }
.search .icon { color: var(--icon-subtle); }
.section { display: flex; flex-direction: column; gap: var(--space-12); }
.section__head { display: flex; align-items: center; justify-content: space-between; }
.resv { display: flex; flex-direction: column; gap: var(--space-8); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); }
.resv__badges { display: flex; align-items: center; gap: var(--space-8); }
.resv__chev { margin-left: auto; color: var(--icon-subtle); }
.segment { display: flex; padding: var(--space-4); border-radius: var(--radius-md); background: var(--bg-muted); }
.segment__tab { flex: 1; height: 36px; border: 0; border-radius: var(--radius-sm); background: none; color: var(--text-secondary); }
.segment__tab--on { background: var(--bg-default); color: var(--text-primary); font-weight: 600; box-shadow: 0 1px 2px rgb(0 0 0 / 6%); }
.procs { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.proc { padding: var(--space-8) 14px; border: 1px solid var(--border-default); border-radius: var(--radius-full); color: var(--text-secondary); }
</style>
