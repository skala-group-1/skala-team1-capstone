<script setup lang="ts">
// 앱 셸. 기준 폭 390px (앱 사이즈 반응형, D-04).
// TODO(fe): 디자인 확정 후 하단 탭(홈·탐색·AI·예약·내정보, C3)·역할별 레이아웃 컴포넌트로 교체
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()
const isCustomer = computed(() => auth.role === 'CUSTOMER')

async function logout() {
  await auth.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="app">
    <header v-if="auth.isLoggedIn">
      <span>{{ auth.user?.name }} ({{ auth.role }})</span>
      <button type="button" @click="logout">{{ t('auth.logout') }}</button>
    </header>
    <main>
      <RouterView />
    </main>
    <nav v-if="isCustomer">
      <RouterLink to="/">{{ t('nav.home') }}</RouterLink> |
      <RouterLink to="/explore">{{ t('nav.explore') }}</RouterLink> |
      <RouterLink to="/chat">{{ t('nav.ai') }}</RouterLink> |
      <RouterLink to="/reservations">{{ t('nav.reservations') }}</RouterLink> |
      <RouterLink to="/me">{{ t('nav.me') }}</RouterLink>
    </nav>
  </div>
</template>

<style>
/* 디자인 전 최소 스타일: 앱 폭만 고정 */
.app {
  max-width: 390px;
  margin: 0 auto;
  font-family: system-ui, sans-serif;
}
</style>
