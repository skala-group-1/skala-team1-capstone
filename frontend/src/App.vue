<script setup lang="ts">
// 앱 셸 선택: 직원(상담사·병원관리자·운영자)은 데스크톱 1440 셸(D-32), 고객·비로그인은 390 앱 셸
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { setLocale } from '@/i18n'
import { showToast } from '@/composables/useToast'
import CustomerLayout from '@/layouts/CustomerLayout.vue'
import StaffLayout from '@/layouts/StaffLayout.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const isStaff = computed(() => !!auth.role && auth.role !== 'CUSTOMER')

// 로그인 사용자 locale 로 화면 언어 맞춤 (스태프는 ko/en)
watch(
  () => auth.user?.locale,
  (locale) => {
    if (locale) setLocale(locale)
  },
)
// 사용 중 세션이 만료되면 안내하고 로그인으로 (다시 로그인하면 보던 화면으로 돌아옴)
watch(
  () => auth.sessionExpired,
  (expired) => {
    if (!expired) return
    auth.sessionExpired = false
    showToast(t('auth.sessionExpired'), 'info')
    void router.replace({ path: '/login', query: { redirect: route.fullPath } })
  },
)
</script>

<template>
  <StaffLayout v-if="isStaff">
    <RouterView />
  </StaffLayout>
  <CustomerLayout v-else>
    <RouterView />
  </CustomerLayout>
</template>
