<script setup lang="ts">
// 04 ① 직원 데스크톱 셸 (D-32): 상단 바 56(로고·역할·병원명·알림·사용자) + 사이드 내비(232, 상담원은 접힘 72) + 본문
// 최소 폭 1024 — 좁으면 가로 스크롤
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppIcon, { type IconName } from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import { useConsultationStore } from '@/stores/consultation'
import { catalogApi } from '@/api'
import type { HospitalDetail } from '@/types/contract'

const auth = useAuthStore()
const notifications = useNotificationStore()
const consultations = useConsultationStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const hospital = ref<HospitalDetail | null>(null)
const menuOpen = ref(false)
const collapsed = computed(() => auth.role === 'COUNSELOR')

interface NavItem {
  to: string
  icon: IconName
  label: string
  exact?: boolean
  count?: number
}
const items = computed<NavItem[]>(() => {
  switch (auth.role) {
    case 'COUNSELOR':
      return [
        // 문의함 배지 = 대기 중 상담 수 (문의함이 불러온 목록 기준)
        { to: '/counselor', icon: 'message-circle', label: t('staff.nav.inbox'), count: consultations.inbox.filter((c) => c.status === 'WAITING').length },
        { to: '/me', icon: 'user', label: t('staff.nav.me') },
      ]
    case 'HOSPITAL_ADMIN':
      return [
        { to: '/hospital-admin', icon: 'home', label: t('staff.nav.dashboard'), exact: true },
        { to: '/hospital-admin/reservations', icon: 'calendar', label: t('staff.nav.reservations') },
        { to: '/hospital-admin/counselors', icon: 'headphones', label: t('counselorAdmin.nav') },
        { to: '/hospital-admin/reviews', icon: 'star', label: t('reviewAdmin.nav') },
        { to: '/hospital-admin/hospital', icon: 'hospital', label: t('staff.nav.hospital') },
      ]
    case 'OPERATOR':
      return [
        { to: '/ops', icon: 'alert-triangle', label: t('staff.nav.failedTasks'), exact: true },
        { to: '/ops/audit-logs', icon: 'file-text', label: t('staff.nav.auditLogs') },
      ]
    default:
      return []
  }
})
function onMenuFocusOut(e: FocusEvent) {
  if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node | null)) menuOpen.value = false
}
const isActive = (item: NavItem) => (item.exact ? route.path === item.to : route.path.startsWith(item.to))
const initial = computed(() => auth.user?.name?.slice(0, 1) ?? '')

onMounted(async () => {
  if (auth.user?.hospitalId) {
    hospital.value = await catalogApi.hospital(auth.user.hospitalId).catch(() => null)
  }
  await notifications.load().catch(() => undefined)
})

async function logout() {
  await auth.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="staff">
    <header class="top">
      <RouterLink :to="auth.home" class="brand">
        <img class="brand__mark" src="/favicon.svg" alt="" width="28" height="28" />
        <span class="logo">{{ t('app.brand') }}</span>
        <span class="role t-caption-11">{{ auth.role ? t(`staff.role.${auth.role}`) : '' }}</span>
      </RouterLink>
      <template v-if="hospital">
        <span class="sep" aria-hidden="true" />
        <span class="t-body-14 clinic-name">{{ hospital.nameKo ?? hospital.name }}</span>
      </template>
      <span class="spacer" />
      <RouterLink to="/notifications" class="bell" :aria-label="t('staff.notifications')">
        <AppIcon name="bell" />
        <span v-if="notifications.unread" class="bell__dot" />
      </RouterLink>
      <!-- 사용자 메뉴: ESC 또는 포커스가 메뉴 밖으로 나가면(바깥 클릭 포함) 닫힘 -->
      <div class="user" @keydown.esc="menuOpen = false" @focusout="onMenuFocusOut">
        <button type="button" class="user__btn" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen">
          <span class="avatar t-caption-12-sb">{{ initial }}</span>
          <span class="t-body-14-sb">{{ auth.user?.name }}</span>
          <AppIcon name="chevron-down" :size="16" />
        </button>
        <div v-if="menuOpen" class="user__menu">
          <!-- mousedown.prevent: 클릭으로 포커스가 옮겨 가며 focusout 으로 메뉴가 먼저 닫히는 것(Safari) 방지 -->
          <button type="button" class="t-body-14" @mousedown.prevent @click="logout">{{ t('auth.logout') }}</button>
        </div>
      </div>
    </header>

    <div class="body">
      <nav class="nav" :class="{ 'nav--rail': collapsed }" :aria-label="t('nav.label')">
        <RouterLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="nav__item"
          :class="{ 'nav__item--on': isActive(item) }"
          :aria-current="isActive(item) ? 'page' : undefined"
        >
          <span class="nav__icon">
            <AppIcon :name="item.icon" :size="collapsed ? 22 : 20" />
            <span v-if="collapsed && item.count" class="nav__count nav__count--rail">{{ item.count }}</span>
          </span>
          <span :class="collapsed ? 't-caption-11' : 't-body-16'">{{ item.label }}</span>
          <span v-if="!collapsed && item.count" class="nav__count">{{ item.count }}</span>
        </RouterLink>
        <div v-if="hospital && !collapsed" class="clinic">
          <p class="t-caption-13 clinic__name">{{ hospital.nameKo ?? hospital.name }}</p>
          <p class="t-caption-12 clinic__meta">{{ t('staff.verifiedAt', { date: hospital.verifiedAt ?? '—' }) }}</p>
        </div>
      </nav>
      <main class="main"><slot /></main>
    </div>
    <AppToast placement="staff" />
  </div>
</template>

<style scoped>
.staff {
  display: flex;
  flex-direction: column;
  min-width: 1024px;
  height: 100dvh;
  background: var(--bg-default);
}
.top {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  flex: none;
  height: var(--staff-top-h);
  padding: 0 var(--space-24);
  border-bottom: 1px solid var(--border-default);
}
.brand { display: flex; align-items: center; gap: var(--space-8); }
.brand__mark { display: block; flex: none; }
.logo { font: 700 22px/30px var(--font-sans); letter-spacing: -0.3px; color: var(--brand-primary); }
.role {
  padding: var(--space-2) var(--space-8);
  border-radius: var(--radius-full);
  background: var(--bg-muted);
  color: var(--text-secondary);
}
.sep { width: 1px; height: 20px; background: var(--border-default); }
.clinic-name { color: var(--text-primary); }
.spacer { flex: 1; }
.bell { position: relative; display: grid; place-items: center; color: var(--icon-default); }
.bell__dot {
  position: absolute;
  top: 0;
  right: 1px;
  width: 8px;
  height: 8px;
  border: 1.5px solid var(--bg-default);
  border-radius: 50%;
  background: var(--status-danger-solid);
}
.user { position: relative; }
.user__btn {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  border: 0;
  background: none;
  color: var(--text-primary);
}
.avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg-muted);
  color: var(--text-secondary);
}
.user__menu {
  position: absolute;
  right: 0;
  top: calc(100% + var(--space-8));
  z-index: 30;
  min-width: 140px;
  padding: var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--surface-card);
  box-shadow: var(--shadow-toast);
}
.user__menu button {
  width: 100%;
  padding: var(--space-8) var(--space-12);
  border: 0;
  border-radius: var(--radius-sm);
  background: none;
  text-align: left;
}
.user__menu button:hover { background: var(--bg-muted); }

.body { display: flex; flex: 1; min-height: 0; }
.nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  flex: none;
  width: var(--staff-nav-w);
  padding: var(--space-20) var(--space-16);
  border-right: 1px solid var(--border-default);
}
.nav__item {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  height: 44px;
  padding: 0 var(--space-12);
  border-radius: var(--radius-md);
  color: var(--text-primary);
}
.nav__item .icon { color: var(--icon-default); }
.nav__item:hover { background: var(--bg-subtle); }
.nav__item--on { background: var(--brand-subtle); color: var(--brand-text); font-weight: 600; }
.nav__item--on .icon { color: var(--brand-primary); }
.nav__icon { position: relative; display: grid; }
.nav__count {
  display: grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  margin-left: auto;
  padding: 0 var(--space-6);
  border-radius: var(--radius-full);
  background: var(--brand-primary);
  color: var(--text-inverse);
  font: 600 12px/16px var(--font-sans);
}
.nav__count--rail { position: absolute; top: -8px; right: -10px; }

.nav--rail { width: 72px; padding: var(--space-16) var(--space-8); align-items: center; }
.nav--rail .nav__item {
  flex-direction: column;
  justify-content: center;
  gap: var(--space-4);
  width: 56px;
  height: 56px;
  padding: 0;
}

.clinic {
  margin-top: auto;
  padding: var(--space-12);
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
}
.clinic__name { color: var(--text-primary); }
.clinic__meta { margin-top: var(--space-4); color: var(--text-tertiary); }

.main { flex: 1; min-width: 0; overflow: auto; background: var(--bg-subtle); }
</style>
