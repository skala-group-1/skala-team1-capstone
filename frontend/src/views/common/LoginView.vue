<script setup lang="ts">
// 「화면 목록」 C2 로그인 (Figma 1:5834, 401 상태 04 ③ 2:10919) → 역할 홈 또는 ?redirect= 경로
// 비밀번호 찾기는 API 가 없어 넣지 않음
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { toApiError } from '@/api'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import TextField from '@/components/ui/TextField.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()

// 로컬 데모용으로 개발 모드에서만 데모 계정을 채워 둔다 (계정 목록은 루트 README)
const email = ref(import.meta.env.DEV ? 'customer.zh1@demo.local' : '')
const password = ref(import.meta.env.DEV ? 'Passw0rd!' : '')
const errorMessage = ref<string | null>(null)
/** 이메일·비밀번호가 틀린 경우만 두 칸을 빨갛게 (네트워크·서버 오류는 폼 아래 안내) */
const wrongCredentials = ref(false)
const submitting = ref(false)

async function submit() {
  submitting.value = true
  errorMessage.value = null
  try {
    await auth.login({ email: email.value.trim(), password: password.value })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    await router.replace(redirect ?? auth.home)
  } catch (e) {
    const err = toApiError(e)
    wrongCredentials.value = err?.code === 'INVALID_CREDENTIALS'
    errorMessage.value = wrongCredentials.value ? t('auth.loginFailed') : err?.message || t('common.error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('auth.login')" back="/onboarding" />
    <form class="content" novalidate @submit.prevent="submit">
      <div class="title">
        <h1 class="t-title-22">{{ t('auth.loginTitle') }}</h1>
        <p class="t-body-14 sub">{{ t('auth.loginBody') }}</p>
      </div>
      <TextField v-model="email" :label="t('auth.email')" type="email" autocomplete="username" :invalid="wrongCredentials" required />
      <TextField
        v-model="password"
        :label="t('auth.password')"
        type="password"
        autocomplete="current-password"
        :error="wrongCredentials ? errorMessage : null"
        required
      >
        <template #error-icon><AppIcon name="alert-triangle" :size="14" /></template>
      </TextField>
      <p v-if="errorMessage && !wrongCredentials" class="form-error t-caption-12" role="alert">{{ errorMessage }}</p>
      <AppButton type="submit" size="l" block :loading="submitting" :disabled="!email || !password">
        {{ t('auth.login') }}
      </AppButton>
      <p class="links t-caption-13">
        <RouterLink :to="{ path: '/signup', query: route.query.redirect ? { redirect: route.query.redirect } : {} }" class="brand">{{ t('auth.signup') }}</RouterLink>
      </p>
      <p class="foot t-caption-12">{{ t('auth.loginFoot') }}</p>
    </form>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100dvh; }
.content { display: flex; flex: 1; flex-direction: column; gap: var(--space-20); padding: var(--space-24) var(--space-16); }
.title { display: flex; flex-direction: column; gap: var(--space-6); }
.sub { color: var(--text-secondary); }
.links { text-align: center; }
.brand { color: var(--text-brand); }
.form-error { color: var(--status-danger); }
.foot { margin-top: auto; color: var(--text-tertiary); }
</style>
