<script setup lang="ts">
// H4-1-D 상담사 추가 모달 (Figma 초대 모달을 바로 생성으로 바꿈: 메일 발송 없음 → 초기 비밀번호를 관리자가 정함)
// 이메일 중복(409)은 부모가 Toast + emailTaken 으로 알려 줌
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '../ui/AppIcon.vue'
import AppChip from '../ui/AppChip.vue'
import AppButton from '../ui/AppButton.vue'
import TextField from '../ui/TextField.vue'
import type { CreateCounselorRequest, Locale } from '@/types/contract'

const props = defineProps<{ open: boolean; busy?: boolean; emailTaken?: boolean }>()
const emit = defineEmits<{ close: []; submit: [body: CreateCounselorRequest]; emailEdited: [] }>()
const { t } = useI18n()

const LANGS: Locale[] = ['ko', 'en', 'zh', 'ja']
const name = ref('')
const email = ref('')
const password = ref('')
const languages = ref<Locale[]>(['ko'])
const touched = ref(false)

const el = ref<HTMLDialogElement | null>(null)
watch([() => props.open, el], ([open, d]) => {
  if (!d) return
  if (open && !d.open) d.showModal()
  else if (!open && d.open) d.close()
})
watch(
  () => props.open,
  (open) => {
    if (!open) return
    name.value = ''
    email.value = ''
    password.value = ''
    languages.value = ['ko']
    touched.value = false
  },
)
// 중복 이메일 오류는 이메일을 고치면 지운다
watch(email, () => props.emailTaken && emit('emailEdited'))
function requestClose() {
  if (!props.busy) emit('close')
}

// backend 검증과 같은 규칙 (SignupRequest 비밀번호 규칙)
const emailOk = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))
const passwordOk = computed(() => /^(?=.*[A-Za-z])(?=.*\d).{8,72}$/.test(password.value))
const valid = computed(() => !!name.value.trim() && emailOk.value && passwordOk.value && languages.value.length > 0)
// 버튼은 막지 않고, 누르면 그때 잘못된 칸에 오류를 보여 준다
const emailError = computed(() => (props.emailTaken ? t('counselorAdmin.toast.emailTaken') : touched.value && !emailOk.value ? t('counselorAdmin.create.emailInvalid') : null))
const passwordError = computed(() => (touched.value && !passwordOk.value ? t('counselorAdmin.create.passwordInvalid') : null))
const nameError = computed(() => (touched.value && !name.value.trim() ? t('counselorAdmin.create.nameRequired') : null))

function toggle(l: Locale) {
  languages.value = languages.value.includes(l) ? languages.value.filter((x) => x !== l) : [...languages.value, l]
}
function submit() {
  touched.value = true
  if (!valid.value || props.busy) return
  emit('submit', { name: name.value.trim(), email: email.value.trim(), password: password.value, languages: languages.value })
}
</script>

<template>
  <dialog ref="el" class="modal" :aria-label="t('counselorAdmin.create.title')" @cancel.prevent="requestClose" @click.self="requestClose">
    <form class="inner" novalidate @submit.prevent="submit">
      <header class="head">
        <div>
          <h2 class="t-title-18">{{ t('counselorAdmin.create.title') }}</h2>
          <p class="t-caption-13 secondary">{{ t('counselorAdmin.create.sub') }}</p>
        </div>
        <button type="button" class="x" :aria-label="t('common.close')" :disabled="busy" @click="requestClose"><AppIcon name="x" /></button>
      </header>
      <div class="body">
        <TextField v-model="name" :label="t('counselorAdmin.create.name')" required autocomplete="off" :error="nameError" />
        <TextField v-model="email" :label="t('counselorAdmin.create.email')" type="email" required autocomplete="off" :error="emailError" />
        <TextField
          v-model="password"
          :label="t('counselorAdmin.create.password')"
          type="password"
          required
          autocomplete="new-password"
          :error="passwordError"
          :hint="t('counselorAdmin.create.passwordHint')"
        />
        <div class="group">
          <p class="t-caption-13">{{ t('counselorAdmin.detail.languages') }}</p>
          <div class="chips" role="group" :aria-label="t('counselorAdmin.detail.languages')">
            <AppChip v-for="l in LANGS" :key="l" :selected="languages.includes(l)" :aria-pressed="languages.includes(l)" @click="toggle(l)">
              {{ t(`domain.langName.${l}`) }}
            </AppChip>
          </div>
          <p class="t-caption-12" :class="touched && !languages.length ? 'danger' : 'muted'">{{ t('counselorAdmin.detail.languagesHint') }}</p>
        </div>
      </div>
      <footer class="foot">
        <AppButton variant="outline" :disabled="busy" @click="requestClose">{{ t('common.cancel') }}</AppButton>
        <AppButton type="submit" icon="plus" :loading="busy">{{ t('counselorAdmin.create.submit') }}</AppButton>
      </footer>
    </form>
  </dialog>
</template>

<style scoped>
.modal::backdrop { background: rgb(0 0 0 / 45%); }
.modal { width: 520px; max-width: calc(100% - 32px); max-height: 90dvh; padding: 0; border: 0; color: inherit; border-radius: var(--radius-xl); background: var(--surface-sheet); box-shadow: var(--shadow-dialog); }
.modal[open] { display: flex; flex-direction: column; }
.inner { display: flex; flex-direction: column; min-height: 0; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-12); padding: var(--space-24) var(--space-24) var(--space-8); }
.head > div { display: flex; flex-direction: column; gap: var(--space-4); }
.x { border: 0; background: none; color: var(--icon-default); }
.body { display: flex; flex-direction: column; gap: var(--space-16); padding: var(--space-8) var(--space-24) var(--space-16); overflow-y: auto; }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.danger { color: var(--status-danger); }
.group { display: flex; flex-direction: column; gap: var(--space-8); }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.foot { display: flex; justify-content: flex-end; gap: var(--space-8); padding: var(--space-12) var(--space-24) var(--space-24); }
</style>
