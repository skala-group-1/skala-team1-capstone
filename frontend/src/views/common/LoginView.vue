<script setup lang="ts">
// 「화면 목록」 C2 로그인 — 골격 중 유일하게 실제 동작하는 화면 (MSW 또는 backend 로 로그인 → 역할 홈 이동)
// TODO(fe): 디자인 적용, 검증 오류 표시, 데모 계정 빠른 선택(로컬 데모용)
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { toApiError } from '@/api'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const email = ref('customer.zh1@demo.local')
const password = ref('Passw0rd!')
const errorMessage = ref<string | null>(null)
const submitting = ref(false)

async function submit() {
  submitting.value = true
  errorMessage.value = null
  try {
    await auth.login({ email: email.value, password: password.value })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    await router.replace(redirect ?? auth.home)
  } catch (e) {
    errorMessage.value = toApiError(e)?.message ?? t('auth.loginFailed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <h1>C2 · {{ t('auth.login') }}</h1>
    <form @submit.prevent="submit">
      <label>{{ t('auth.email') }} <input v-model="email" type="email" autocomplete="username" required /></label>
      <label>{{ t('auth.password') }} <input v-model="password" type="password" autocomplete="current-password" required /></label>
      <button type="submit" :disabled="submitting">{{ t('auth.login') }}</button>
    </form>
    <p v-if="errorMessage" role="alert">{{ errorMessage }}</p>
    <RouterLink to="/signup">{{ t('auth.signup') }}</RouterLink>
  </section>
</template>
