<script setup lang="ts">
// 「화면 목록」 C2 회원가입 (Figma 1:5873, 고객만). 가입 성공 → 같은 계정으로 로그인 → 홈
// 검증: 이메일 형식, 비밀번호 8자 이상 + 영문·숫자. 서버 오류 EMAIL_DUPLICATED(409) · VALIDATION_FAILED(details.fields)
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { toApiError } from '@/api'
import { setLocale } from '@/i18n'
import { seoulDate } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import TextField from '@/components/ui/TextField.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppChip from '@/components/ui/AppChip.vue'
import type { Gender, Locale } from '@/types/contract'
import { storage } from '@/utils/storage'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
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
/** 표시할 칸이 없는 서버 오류(locale 등) → 폼 위에 서버 문구 */
const formError = ref<string | null>(null)
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
// 고른 언어를 화면에도 바로 반영
watch(() => form.locale, (l) => setLocale(l))

const clientErrors = computed(() => ({
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? null : t('signup.errors.email'),
  password: form.password.length >= 8 && /[A-Za-z]/.test(form.password) && /\d/.test(form.password) ? null : t('signup.errors.password'),
}))
const valid = computed(
  () => !clientErrors.value.email && !clientErrors.value.password && form.name.trim() && form.birthDate && form.gender && form.nationality,
)
type Field = 'email' | 'password' | 'name' | 'birthDate' | 'gender' | 'nationality'
const FIELDS: Field[] = ['email', 'password', 'name', 'birthDate', 'gender', 'nationality']
function errorOf(field: Field) {
  if (serverErrors.value[field]) return serverErrors.value[field]
  if (!touched[field]) return null
  if (field === 'email' || field === 'password') return clientErrors.value[field]
  return String(form[field]).trim() ? null : t('signup.errors.required')
}

async function submit() {
  // 버튼을 막아 두는 대신, 누르면 빈 칸·잘못된 칸을 모두 보여 준다
  for (const f of FIELDS) touched[f] = true
  if (!valid.value) return
  submitting.value = true
  serverErrors.value = {}
  formError.value = null
  try {
    await auth.signup({ ...form, email: form.email.trim(), name: form.name.trim(), gender: form.gender as Gender })
    // 가입 때 고른 언어가 계정 언어 → 온보딩에서 고른 언어(localePicked)로 덮어쓰지 않게 지운다
    storage.remove('localePicked')
    await auth.login({ email: form.email.trim(), password: form.password })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    await router.replace(redirect ?? auth.home)
  } catch (e) {
    const err = toApiError(e)
    if (err?.code === 'EMAIL_DUPLICATED') serverErrors.value = { email: t('signup.errors.duplicated') }
    else if (err?.details.fields?.length) {
      // reason 은 backend 영어 원문 → 칸별 번역 문구로. 칸이 없는 필드(locale 등)는 서버 메시지(사용자 locale)를 폼 위에
      const shown = err.details.fields.filter((f) => FIELDS.includes(f.field as Field))
      serverErrors.value = Object.fromEntries(
        shown.map((f) => [f.field, f.field === 'email' || f.field === 'password' ? t(`signup.errors.${f.field}`) : t('signup.errors.invalid')]),
      )
      if (shown.length < err.details.fields.length) formError.value = err.message
    } else formError.value = err?.message || t('common.error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('auth.signup')" back="/login" />
    <form id="signup" class="content" novalidate @submit.prevent="submit">
      <p v-if="formError" class="form-error t-caption-12" role="alert">{{ formError }}</p>
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
      <TextField v-model="form.birthDate" :label="t('signup.birthDate')" type="date" :max="seoulDate()" autocomplete="bday" :error="errorOf('birthDate')" />
      <div class="group">
        <span class="t-caption-13 label">{{ t('signup.gender') }}</span>
        <div class="chips" role="radiogroup" :aria-label="t('signup.gender')">
          <AppChip v-for="g in genders" :key="g" :selected="form.gender === g" role="radio" :aria-checked="form.gender === g" @click="form.gender = g">
            {{ t(`signup.genders.${g}`) }}
          </AppChip>
        </div>
        <p v-if="errorOf('gender')" class="form-error t-caption-12" role="alert">{{ errorOf('gender') }}</p>
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
      <AppButton type="submit" form="signup" size="l" block :loading="submitting">{{ t('signup.submit') }}</AppButton>
    </footer>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100dvh; }
.content { display: flex; flex: 1; flex-direction: column; gap: 14px; padding: var(--space-16); }
.group { display: flex; flex-direction: column; gap: var(--space-6); }
.label { color: var(--text-secondary); }
.chips { display: flex; gap: var(--space-8); }
.form-error { color: var(--status-danger); }
.bottom {
  position: sticky;
  bottom: 0;
  padding: var(--space-12) var(--space-16) calc(var(--space-12) + env(safe-area-inset-bottom));
  border-top: 1px solid var(--border-default);
  background: var(--bg-default);
}
</style>
