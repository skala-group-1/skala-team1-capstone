<script setup lang="ts">
// 병원 정보 수정 — 의료진 추가·수정 모달. 저장하면 바로 반영 (병원 정보 저장과 따로)
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '../ui/AppIcon.vue'
import AppChip from '../ui/AppChip.vue'
import AppButton from '../ui/AppButton.vue'
import TextField from '../ui/TextField.vue'
import type { AdminDoctor, DoctorRequest, Locale, ProcedureCode } from '@/types/contract'

const props = defineProps<{ open: boolean; doctor: AdminDoctor | null; procedures: { code: ProcedureCode; name: string }[]; busy?: boolean }>()
const emit = defineEmits<{ close: []; submit: [body: DoctorRequest] }>()
const { t } = useI18n()

const LANGS: Locale[] = ['ko', 'en', 'zh', 'ja']
const TITLES = ['대표원장', '원장', '부원장']
const nameKo = ref('')
const nameEn = ref('')
const title = ref('원장')
const years = ref('')
const languages = ref<Locale[]>(['ko'])
const specialties = ref<ProcedureCode[]>([])
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
    const d = props.doctor
    nameKo.value = d?.nameKo ?? ''
    nameEn.value = d?.nameEn ?? ''
    title.value = d?.title ?? '원장'
    years.value = d?.careerYears != null ? String(d.careerYears) : ''
    languages.value = d ? [...d.languages] : ['ko']
    specialties.value = d ? [...d.specialties] : []
    touched.value = false
  },
)
function requestClose() {
  if (!props.busy) emit('close')
}
const yearsOk = computed(() => years.value === '' || (/^\d{1,2}$/.test(years.value) && Number(years.value) <= 60))
const valid = computed(() => !!nameKo.value.trim() && yearsOk.value && languages.value.length > 0)
const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v])
function submit() {
  touched.value = true
  if (!valid.value || props.busy) return
  emit('submit', {
    nameKo: nameKo.value.trim(),
    nameEn: nameEn.value.trim() || null,
    title: title.value,
    careerYears: years.value === '' ? null : Number(years.value),
    languages: LANGS.filter((l) => languages.value.includes(l)),
    specialties: specialties.value,
  })
}
</script>

<template>
  <dialog ref="el" class="modal" :aria-label="t(doctor ? 'hospitalEdit.doctor.editTitle' : 'hospitalEdit.doctor.addTitle')" @cancel.prevent="requestClose" @click.self="requestClose">
    <form class="inner" novalidate @submit.prevent="submit">
      <header class="head">
        <h2 class="t-title-18">{{ t(doctor ? 'hospitalEdit.doctor.editTitle' : 'hospitalEdit.doctor.addTitle') }}</h2>
        <button type="button" class="x" :aria-label="t('common.close')" :disabled="busy" @click="requestClose"><AppIcon name="x" /></button>
      </header>
      <div class="body">
        <div class="row">
          <TextField v-model="nameKo" :label="t('hospitalEdit.doctor.nameKo')" required :error="touched && !nameKo.trim() ? t('hospitalEdit.required') : null" />
          <TextField v-model="nameEn" :label="t('hospitalEdit.doctor.nameEn')" placeholder="Dr. Kim Seoyeon" />
        </div>
        <div class="row">
          <TextField v-model="title" :label="t('hospitalEdit.doctor.title')" :options="TITLES.map((v) => ({ value: v, label: v }))" />
          <TextField v-model="years" :label="t('hospitalEdit.doctor.careerYears')" type="number" :error="touched && !yearsOk ? '0 ~ 60' : null" />
        </div>
        <div class="group">
          <p class="t-caption-13">{{ t('hospitalEdit.doctor.languages') }}</p>
          <div class="chips">
            <AppChip v-for="l in LANGS" :key="l" :selected="languages.includes(l)" :aria-pressed="languages.includes(l)" @click="languages = toggle(languages, l)">
              {{ t(`domain.langName.${l}`) }}
            </AppChip>
          </div>
          <p v-if="touched && !languages.length" class="t-caption-12 danger">{{ t('hospitalEdit.languagesHint') }}</p>
        </div>
        <div class="group">
          <p class="t-caption-13">{{ t('hospitalEdit.doctor.specialties') }}</p>
          <div class="chips">
            <AppChip v-for="p in procedures" :key="p.code" :selected="specialties.includes(p.code)" :aria-pressed="specialties.includes(p.code)" @click="specialties = toggle(specialties, p.code)">
              {{ p.name }}
            </AppChip>
          </div>
        </div>
      </div>
      <footer class="foot">
        <AppButton variant="outline" :disabled="busy" @click="requestClose">{{ t('common.cancel') }}</AppButton>
        <AppButton type="submit" :loading="busy">{{ t('hospitalEdit.doctor.submit') }}</AppButton>
      </footer>
    </form>
  </dialog>
</template>

<style scoped>
.modal::backdrop { background: rgb(0 0 0 / 45%); }
.modal { width: 560px; max-width: calc(100% - 32px); max-height: 90dvh; padding: 0; border: 0; color: inherit; border-radius: var(--radius-xl); background: var(--surface-sheet); box-shadow: var(--shadow-dialog); }
.modal[open] { display: flex; flex-direction: column; }
.inner { display: flex; flex-direction: column; min-height: 0; }
.head { display: flex; align-items: center; justify-content: space-between; padding: var(--space-24) var(--space-24) var(--space-8); }
.x { border: 0; background: none; color: var(--icon-default); }
.body { display: flex; flex-direction: column; gap: var(--space-16); padding: var(--space-8) var(--space-24) var(--space-16); overflow-y: auto; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-12); }
.group { display: flex; flex-direction: column; gap: var(--space-8); }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.danger { color: var(--status-danger); }
.foot { display: flex; justify-content: flex-end; gap: var(--space-8); padding: var(--space-12) var(--space-24) var(--space-24); }
</style>
