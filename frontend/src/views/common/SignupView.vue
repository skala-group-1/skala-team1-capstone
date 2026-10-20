<script setup lang="ts">
// 「화면 목록」 C2 회원가입 (Figma 1:5873, 고객만). 가입 성공 → 같은 계정으로 로그인 → 홈
// 검증: 이메일 형식, 비밀번호 8자 이상 + 영문·숫자. 서버 오류 EMAIL_DUPLICATED(409) · VALIDATION_FAILED(details.fields)
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { toApiError } from '@/api'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import TextField from '@/components/ui/TextField.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppChip from '@/components/ui/AppChip.vue'
import type { Gender, Locale } from '@/types/contract'

const auth = useAuthStore()
const router = useRouter()
const { t, locale } = useI18n()

const form = reactive({
  email: '',
  password: '',
  name: '',
  birthDate: '',
  gender: '' as Gender | '',
  nationality: '',
  locale: locale.value as Locale,
})
const touched = reactive<Record<string, boolean>>({})
const serverErrors = ref<Record<string, string>>({})
const submitting = ref(false)

// ISO 3166-1 alpha-2. 국가명은 브라우저 Intl 로 현재 언어에 맞춰 표시
const NATIONALITIES = ['US', 'GB', 'CA', 'AU', 'CN', 'TW', 'HK', 'JP', 'SG', 'MY', 'TH', 'VN', 'ID', 'PH', 'FR', 'DE'] as const
const nationalityOptions = computed(() => {
  const names = new Intl.DisplayNames([locale.value], { type: 'region' })
  return NATIONALITIES.map((c) => ({ value: c, label: names.of(c) ?? c }))
})
const localeOptions = [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '简体中文' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
]
const genders: Gender[] = ['F', 'M', 'X']

const clientErrors = computed(() => ({
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? null : t('signup.errors.email'),
  password: form.password.length >= 8 && /[A-Za-z]/.test(form.password) && /\d/.test(form.password) ? null : t('signup.errors.password'),
}))
const valid = computed(
  () => !clientErrors.value.email && !clientErrors.value.password && form.name.trim() && form.birthDate && form.gender && form.nationality,
)
function errorOf(field: 'email' | 'password' | 'name' | 'birthDate' | 'nationality') {
  if (serverErrors.value[field]) return serverErrors.value[field]
  if (!touched[field]) return null
  return field === 'email' || field === 'password' ? clientErrors.value[field] : null
}

async function submit() {
  Object.assign(touched, { email: true, password: true })
  if (!valid.value) return
  submitting.value = true
  serverErrors.value = {}
  try {
    await auth.signup({ ...form, email: form.email.trim(), name: form.name.trim(), gender: form.gender as Gender })
    await auth.login({ email: form.email.trim(), password: form.password })
    await router.replace(auth.home)
  } catch (e) {
    const err = toApiError(e)
    if (err?.code === 'EMAIL_DUPLICATED') serverErrors.value = { email: t('signup.errors.duplicated') }
    else if (err?.details.fields?.length) serverErrors.value = Object.fromEntries(err.details.fields.map((f) => [f.field, f.reason]))
    else serverErrors.value = { email: err?.message ?? t('common.error') }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('auth.signup')" back="/login" />
    <form id="signup" class="content" novalidate @submit.prevent="submit">
      <TextField
        v-model="form.email"
        :label="t('auth.email')"
        type="email"
        autocomplete="email"
        placeholder="name@example.com"
        :error="errorOf('email')"
        @focusout="touched.email = true"
      />
      <TextField
        v-model="form.password"
        :label="t('auth.password')"
        type="password"
        autocomplete="new-password"
        :error="errorOf('password')"
        @focusout="touched.password = true"
      />
      <TextField v-model="form.name" :label="t('signup.name')" autocomplete="name" :error="errorOf('name')" />
      <TextField v-model="form.birthDate" :label="t('signup.birthDate')" type="date" :error="errorOf('birthDate')" />
      <div class="group">
        <span class="t-caption-13 label">{{ t('signup.gender') }}</span>
        <div class="chips" role="radiogroup" :aria-label="t('signup.gender')">
          <AppChip v-for="g in genders" :key="g" :selected="form.gender === g" role="radio" :aria-checked="form.gender === g" @click="form.gender = g">
            {{ t(`signup.genders.${g}`) }}
          </AppChip>
        </div>
      </div>
      <TextField
        v-model="form.nationality"
        :label="t('signup.nationality')"
        :options="nationalityOptions"
        :placeholder="t('signup.choose')"
        :error="errorOf('nationality')"
      />
      <TextField v-model="form.locale" :label="t('signup.locale')" :options="localeOptions" :hint="t('signup.localeHint')" />
    </form>
    <footer class="bottom">
      <AppButton type="submit" form="signup" size="l" block :loading="submitting" :disabled="!valid">{{ t('signup.submit') }}</AppButton>
    </footer>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100dvh; }
.content { display: flex; flex: 1; flex-direction: column; gap: 14px; padding: var(--space-16); }
.group { display: flex; flex-direction: column; gap: var(--space-6); }
.label { color: var(--text-secondary); }
.chips { display: flex; gap: var(--space-8); }
.bottom {
  position: sticky;
  bottom: 0;
  padding: var(--space-12) var(--space-16) calc(var(--space-12) + env(safe-area-inset-bottom));
  border-top: 1px solid var(--border-default);
  background: var(--bg-default);
}
</style>
