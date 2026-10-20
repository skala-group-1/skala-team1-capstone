<script setup lang="ts">
// 앱 셸 선택: 직원(상담사·병원관리자·운영자)은 데스크톱 1440 셸(D-32), 고객·비로그인은 390 앱 셸
import { computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { setLocale } from '@/i18n'
import CustomerLayout from '@/layouts/CustomerLayout.vue'
import StaffLayout from '@/layouts/StaffLayout.vue'

const auth = useAuthStore()
const isStaff = computed(() => !!auth.role && auth.role !== 'CUSTOMER')

// 로그인 사용자 locale 로 화면 언어 맞춤 (스태프는 ko/en)
watch(
  () => auth.user?.locale,
  (locale) => {
    if (locale) setLocale(locale)
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
