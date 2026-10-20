<script setup lang="ts">
// 04 ① 고객 앱 셸: 폭 390 (웹에서는 480까지 가운데 정렬, 바깥은 bg/subtle). 탭 바 64는 route.meta.tabBar 인 화면만
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppIcon, { type IconName } from '@/components/ui/AppIcon.vue'
import AppToast from '@/components/ui/AppToast.vue'

const route = useRoute()
const { t } = useI18n()

const tabs = computed<{ to: string; icon: IconName; label: string; match: (p: string) => boolean }[]>(() => [
  { to: '/', icon: 'home', label: t('nav.home'), match: (p) => p === '/' },
  { to: '/explore', icon: 'search', label: t('nav.explore'), match: (p) => p.startsWith('/explore') || p.startsWith('/compare') },
  { to: '/chats', icon: 'sparkles', label: t('nav.ai'), match: (p) => p.startsWith('/chat') },
  { to: '/reservations', icon: 'calendar', label: t('nav.reservations'), match: (p) => p.startsWith('/reservations') },
  { to: '/me', icon: 'user', label: t('nav.me'), match: (p) => p.startsWith('/me') },
])
const showTabs = computed(() => !!route.meta.tabBar)
</script>

<template>
  <div class="shell" :class="{ 'shell--tabs': showTabs }">
    <slot />
    <nav v-if="showTabs" class="tabs" :aria-label="t('nav.label')">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        class="tab t-caption-11"
        :class="{ 'tab--on': tab.match(route.path) }"
        :aria-current="tab.match(route.path) ? 'page' : undefined"
      >
        <AppIcon :name="tab.icon" />
        <span>{{ tab.label }}</span>
      </RouterLink>
    </nav>
    <AppToast placement="customer" />
  </div>
</template>

<style scoped>
.shell {
  position: relative;
  max-width: 480px;
  min-height: 100dvh;
  margin: 0 auto;
  background: var(--bg-default);
}
@media (min-width: 481px) {
  .shell { box-shadow: 0 0 0 1px var(--border-default); }
}
.shell--tabs { padding-bottom: calc(var(--tab-bar-h) + env(safe-area-inset-bottom)); }
.tabs {
  position: fixed;
  bottom: 0;
  left: 50%;
  z-index: 20;
  display: flex;
  width: 100%;
  max-width: 480px;
  height: calc(var(--tab-bar-h) + env(safe-area-inset-bottom));
  padding: 0 var(--space-8) env(safe-area-inset-bottom);
  transform: translateX(-50%);
  border-top: 1px solid var(--border-default);
  background: var(--bg-default);
}
.tab {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  color: var(--text-tertiary);
}
.tab .icon { color: var(--icon-subtle); }
.tab--on,
.tab--on .icon { color: var(--brand-text); }
</style>
