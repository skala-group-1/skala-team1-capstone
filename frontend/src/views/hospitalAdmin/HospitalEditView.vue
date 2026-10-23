<script setup lang="ts">
// H3-E 병원 정보 수정 (Figma 209:2753): 기본 정보 · 진료 시간 · 의료진 3열 + 아래 고정 저장 바
// 운영팀 검토 없이 바로 반영 (Figma 의 '변경 요청 → 검토 중'(H3-E1) 단계 없음). 의료진은 모달에서 따로 바로 저장
// 진료 시간을 바꾸면 바뀐 요일의 다가오는 승인 대기·확정 예약 중 새 시간 밖에 있는 건수를 미리 알려 준다 (예약은 그대로)
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { hospitalAdminApi } from '@/api'
import { showToast } from '@/composables/useToast'
import DoctorModal from '@/components/staff/DoctorModal.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import TextField from '@/components/ui/TextField.vue'
import type { AdminDoctor, DayHours, DoctorRequest, HospitalInfo, Locale, Reservation, UpdateHospitalRequest, Weekday } from '@/types/contract'

const router = useRouter()
const { t, locale } = useI18n()
const DAYS: Weekday[] = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
const LANGS: Locale[] = ['ko', 'en', 'zh', 'ja']
const PHONE = /^[0-9+\-() ]{7,30}$/

const info = ref<HospitalInfo | null>(null)
const failed = ref(false)
const saving = ref(false)
const upcoming = ref<Reservation[]>([])

interface Draft {
  phone: string
  addressKo: string
  addressEn: string
  descriptionKo: string
  languages: Locale[]
  hasInterpreter: boolean
  hours: Record<Weekday, { on: boolean; open: string; close: string }>
}
const draft = ref<Draft | null>(null)

function toDraft(h: HospitalInfo): Draft {
  const hours = {} as Draft['hours']
  for (const d of DAYS) {
    const v = h.openHours[d]
    hours[d] = { on: !!v, open: v?.open ?? '10:00', close: v?.close ?? '19:00' }
  }
  return {
    phone: h.phone ?? '',
    addressKo: h.addressKo ?? '',
    addressEn: h.addressEn ?? '',
    descriptionKo: h.descriptionKo ?? '',
    languages: [...h.languages],
    hasInterpreter: h.hasInterpreter,
    hours,
  }
}
const dayName = (i: number) => new Intl.DateTimeFormat(locale.value, { weekday: 'short' }).format(new Date(`2026-10-${19 + i}T12:00:00+09:00`))
const hoursOf = (d: Draft, day: Weekday): DayHours | null => (d.hours[day].on ? { open: d.hours[day].open, close: d.hours[day].close } : null)
const sameHours = (a: DayHours | null, b: DayHours | null) => (a?.open ?? '') === (b?.open ?? '') && (a?.close ?? '') === (b?.close ?? '')
const sameLangs = (a: Locale[], b: Locale[]) => a.length === b.length && a.every((l) => b.includes(l))

/** 바뀐 필드만 모은 요청 (openHours 는 하루라도 바뀌면 7일 전체) */
const changes = computed<UpdateHospitalRequest>(() => {
  const h = info.value
  const d = draft.value
  if (!h || !d) return {}
  const out: UpdateHospitalRequest = {}
  if (d.phone.trim() !== (h.phone ?? '')) out.phone = d.phone.trim()
  if (d.addressKo.trim() !== (h.addressKo ?? '')) out.addressKo = d.addressKo.trim()
  if (d.addressEn.trim() !== (h.addressEn ?? '')) out.addressEn = d.addressEn.trim()
  if (d.descriptionKo.trim() !== (h.descriptionKo ?? '')) out.descriptionKo = d.descriptionKo.trim()
  if (!sameLangs(d.languages, h.languages)) out.languages = LANGS.filter((l) => d.languages.includes(l))
  if (d.hasInterpreter !== h.hasInterpreter) out.hasInterpreter = d.hasInterpreter
  if (DAYS.some((day) => !sameHours(hoursOf(d, day), h.openHours[day]))) {
    out.openHours = Object.fromEntries(DAYS.map((day) => [day, hoursOf(d, day)])) as Record<Weekday, DayHours | null>
  }
  return out
})
const changedDays = computed(() => (info.value && draft.value ? DAYS.filter((day) => !sameHours(hoursOf(draft.value!, day), info.value!.openHours[day])) : []))
const changeCount = computed(() => Object.keys(changes.value).length - (changes.value.openHours ? 1 : 0) + changedDays.value.length)

const errors = computed(() => {
  const d = draft.value
  if (!d) return {} as Record<string, string>
  const e: Record<string, string> = {}
  if (!PHONE.test(d.phone.trim())) e.phone = t('hospitalEdit.phoneInvalid')
  if (!d.addressKo.trim()) e.addressKo = t('hospitalEdit.required')
  if (!d.addressEn.trim()) e.addressEn = t('hospitalEdit.required')
  if (!d.descriptionKo.trim()) e.descriptionKo = t('hospitalEdit.required')
  if (!d.languages.length) e.languages = t('hospitalEdit.languagesHint')
  for (const day of DAYS) {
    const h = d.hours[day]
    if (h.on && !(h.open && h.close && h.open < h.close)) e[`hours.${day}`] = t('hospitalEdit.hoursInvalid')
  }
  return e
})
const errorCount = computed(() => Object.keys(errors.value).length)

/** KST 요일 키·시각 (예약 슬롯 시작 시각 기준) */
const KST_DAY = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Seoul', weekday: 'short' })
const KST_HM = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
const affected = computed(() => {
  const d = draft.value
  if (!d || !changedDays.value.length) return 0
  return upcoming.value.filter((r) => {
    const at = new Date(r.slot.startAt)
    const day = KST_DAY.format(at).toLowerCase().slice(0, 3) as Weekday
    if (!changedDays.value.includes(day)) return false
    const h = hoursOf(d, day)
    const hm = KST_HM.format(at)
    return !h || hm < h.open || hm >= h.close
  }).length
})

async function load() {
  failed.value = false
  try {
    info.value = await hospitalAdminApi.hospital()
    draft.value = toDraft(info.value)
  } catch {
    failed.value = true
  }
}
// 진료 시간 경고용: 다가오는 승인 대기·확정 예약 (예약 관리 화면과 같은 방식으로 최대 20페이지)
async function loadUpcoming() {
  const now = Date.now()
  const items: Reservation[] = []
  try {
    for (let page = 0; page < 20; page++) {
      const res = await hospitalAdminApi.reservations({ page, size: 50 })
      items.push(...res.items)
      if (!res.items.length || items.length >= res.total) break
    }
  } catch {
    return
  }
  upcoming.value = items.filter((r) => (r.status === 'PENDING' || r.status === 'CONFIRMED') && new Date(r.slot.startAt).getTime() > now)
}
async function save() {
  if (!changeCount.value || errorCount.value || saving.value) return
  saving.value = true
  try {
    info.value = await hospitalAdminApi.updateHospital(changes.value)
    draft.value = toDraft(info.value)
    showToast(t('hospitalEdit.saved'))
  } catch {
    showToast(t('common.error'), 'error')
  } finally {
    saving.value = false
  }
}

// 의료진 모달
const doctorOpen = ref(false)
const editing = ref<AdminDoctor | null>(null)
const doctorBusy = ref(false)
function openDoctor(d: AdminDoctor | null) {
  editing.value = d
  doctorOpen.value = true
}
async function saveDoctor(body: DoctorRequest) {
  if (!info.value) return
  doctorBusy.value = true
  try {
    const target = editing.value
    const d = target ? await hospitalAdminApi.updateDoctor(target.id, body) : await hospitalAdminApi.addDoctor(body)
    const list = info.value.doctors
    const i = list.findIndex((x) => x.id === d.id)
    if (i >= 0) list[i] = d
    else list.push(d)
    doctorOpen.value = false
    showToast(t(target ? 'hospitalEdit.doctor.updated' : 'hospitalEdit.doctor.added'))
  } catch {
    showToast(t('common.error'), 'error')
  } finally {
    doctorBusy.value = false
  }
}

onMounted(() => {
  void load()
  void loadUpcoming()
})
</script>

<template>
  <div class="page">
    <header class="title">
      <h1 class="t-title-22">{{ t('hospitalEdit.title') }}</h1>
      <p class="t-body-14 secondary">{{ t('hospitalEdit.sub') }}</p>
    </header>
    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('staff.loadFailed')">
      <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
    </EmptyState>
    <div v-else-if="info && draft" class="cols">
      <!-- 기본 정보 -->
      <section class="card">
        <h2 class="t-title-18">{{ t('hospitalEdit.basic') }}</h2>
        <TextField v-model="draft.phone" :label="t('hospitalEdit.phone')" required :error="errors.phone" />
        <TextField v-model="draft.addressKo" :label="t('hospitalEdit.addressKo')" required :error="errors.addressKo" />
        <TextField v-model="draft.addressEn" :label="t('hospitalEdit.addressEn')" required :error="errors.addressEn" />
        <label class="group">
          <span class="t-caption-13 label">
            {{ t('hospitalEdit.description') }}
            <AppBadge v-if="changes.descriptionKo !== undefined" tone="brand">{{ t('hospitalEdit.changed') }}</AppBadge>
          </span>
          <textarea v-model="draft.descriptionKo" class="t-body-14" :class="{ invalid: errors.descriptionKo }" rows="5" maxlength="500" />
          <span class="t-caption-12" :class="errors.descriptionKo ? 'danger' : 'muted'">{{ errors.descriptionKo ?? t('hospitalEdit.descriptionHint', { n: draft.descriptionKo.length }) }}</span>
        </label>
        <div class="group">
          <p class="t-caption-13 label">{{ t('hospitalEdit.languages') }}</p>
          <div class="chips">
            <AppChip
              v-for="l in LANGS"
              :key="l"
              :selected="draft.languages.includes(l)"
              :aria-pressed="draft.languages.includes(l)"
              @click="draft.languages = draft.languages.includes(l) ? draft.languages.filter((x) => x !== l) : [...draft.languages, l]"
            >
              {{ t(`domain.langName.${l}`) }}
            </AppChip>
          </div>
          <p v-if="errors.languages" class="t-caption-12 danger">{{ errors.languages }}</p>
        </div>
        <label class="switch">
          <span>
            <span class="t-body-14-sb">{{ t('hospitalEdit.interpreter') }}</span>
            <span class="t-caption-12 muted">{{ t('hospitalEdit.interpreterHint') }}</span>
          </span>
          <input v-model="draft.hasInterpreter" type="checkbox" role="switch" />
          <span class="track" aria-hidden="true" />
        </label>
      </section>

      <!-- 진료 시간 -->
      <section class="card">
        <div>
          <h2 class="t-title-18">{{ t('hospitalEdit.hours') }}</h2>
          <p class="t-caption-12 muted">{{ t('hospitalEdit.hoursHint') }}</p>
        </div>
        <div v-for="(day, i) in DAYS" :key="day" class="day">
          <!-- 바뀐 요일은 이름 옆 점으로 표시 (배지는 줄이 넘쳐서) -->
          <span class="t-body-14-sb dayname" :class="{ muted: !draft.hours[day].on, 'dayname--changed': changedDays.includes(day) }" :title="changedDays.includes(day) ? t('hospitalEdit.changed') : undefined">{{ dayName(i) }}</span>
          <template v-if="draft.hours[day].on">
            <input v-model="draft.hours[day].open" type="time" class="time t-body-14" :class="{ invalid: errors[`hours.${day}`] }" :aria-label="`${dayName(i)} open`" />
            <span class="muted">~</span>
            <input v-model="draft.hours[day].close" type="time" class="time t-body-14" :class="{ invalid: errors[`hours.${day}`] }" :aria-label="`${dayName(i)} close`" />
          </template>
          <span v-else class="t-body-14 muted closed">{{ t('hospitalEdit.closed') }}</span>
          <label class="switch switch--bare">
            <input v-model="draft.hours[day].on" type="checkbox" role="switch" :aria-label="dayName(i)" />
            <span class="track" aria-hidden="true" />
          </label>
        </div>
        <p v-if="Object.keys(errors).some((k) => k.startsWith('hours.'))" class="t-caption-12 danger">{{ t('hospitalEdit.hoursInvalid') }}</p>
        <p v-if="affected" class="notice notice--warn t-caption-13"><AppIcon name="alert-triangle" :size="16" />{{ t('hospitalEdit.affected', { n: affected }) }}</p>
        <p v-if="changedDays.length" class="t-caption-12 muted">{{ t('hospitalEdit.slotsNote') }}</p>
      </section>

      <!-- 의료진 -->
      <section class="card">
        <div class="row-between">
          <h2 class="t-title-18">{{ t('hospitalEdit.doctors', { n: info.doctors.length }) }}</h2>
          <AppButton variant="outline" size="s" icon="plus" @click="openDoctor(null)">{{ t('hospitalEdit.addDoctor') }}</AppButton>
        </div>
        <ul class="doctors">
          <li v-for="d in info.doctors" :key="d.id" class="doctor">
            <span class="avatar t-caption-12-sb">{{ d.nameKo.slice(0, 1) }}</span>
            <span class="doctor__text">
              <span class="t-body-14-sb">{{ d.nameKo }}</span>
              <span class="t-caption-12 muted">
                {{ [d.title, d.careerYears != null ? t('hospitalEdit.career', { n: d.careerYears }) : null, d.languages.map((l) => l.toUpperCase()).join(' ')].filter(Boolean).join(' · ') }}
              </span>
            </span>
            <button type="button" class="link t-body-14" @click="openDoctor(d)">{{ t('hospitalEdit.editDoctor') }}</button>
          </li>
        </ul>
        <p class="t-caption-12 muted">{{ t('hospitalEdit.doctorsNote') }}</p>
      </section>
    </div>

    <footer v-if="info && draft" class="bar">
      <div>
        <p class="t-body-14-sb">{{ changeCount ? t('hospitalEdit.summary', { changes: changeCount, errors: errorCount }) : t('hospitalEdit.noChanges') }}</p>
        <p v-if="errorCount" class="t-caption-12 danger">{{ t('hospitalEdit.fixErrors') }}</p>
      </div>
      <span class="spacer" />
      <AppButton variant="outline" size="l" :disabled="saving" @click="router.push('/hospital-admin/hospital')">{{ t('common.cancel') }}</AppButton>
      <AppButton size="l" icon="send" :disabled="!changeCount || !!errorCount" :loading="saving" @click="save">{{ t('hospitalEdit.save') }}</AppButton>
    </footer>

    <DoctorModal :open="doctorOpen" :doctor="editing" :procedures="info?.procedures ?? []" :busy="doctorBusy" @close="doctorOpen = false" @submit="saveDoctor" />
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: var(--space-20); min-height: 100%; padding: var(--space-32) var(--space-32) 0; }
.title { display: flex; flex-direction: column; gap: var(--space-4); }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.danger { color: var(--status-danger); }
.spacer { flex: 1; }
.cols { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr) minmax(0, 1fr); gap: var(--space-16); align-items: start; }
.card { display: flex; flex-direction: column; gap: var(--space-16); padding: var(--space-20); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.group { display: flex; flex-direction: column; gap: var(--space-8); }
.label { display: flex; align-items: center; gap: var(--space-6); color: var(--text-secondary); }
textarea { padding: var(--space-12); border: 1px solid var(--border-default); border-radius: var(--radius-md); resize: vertical; }
textarea:focus { border-color: var(--brand-primary); outline: none; }
.invalid { border-color: var(--status-danger) !important; }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.switch { position: relative; display: flex; align-items: center; justify-content: space-between; gap: var(--space-12); cursor: pointer; }
.switch > span:first-child { display: flex; flex-direction: column; gap: var(--space-2); }
.switch--bare { flex: none; margin-left: auto; }
.switch input { position: absolute; opacity: 0; }
.track { position: relative; flex: none; width: 36px; height: 20px; border-radius: 10px; background: var(--border-strong); transition: background 0.15s; }
.track::after { content: ''; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: var(--bg-default); transition: transform 0.15s; }
.switch input:checked + .track { background: var(--brand-primary); }
.switch input:checked + .track::after { transform: translateX(16px); }
.switch input:focus-visible + .track { outline: 2px solid var(--border-focus); outline-offset: 2px; }
.day { display: flex; align-items: center; gap: var(--space-6); min-height: 40px; }
.dayname { position: relative; flex: none; width: 24px; }
.dayname--changed::after { content: ''; position: absolute; top: 0; right: 2px; width: 6px; height: 6px; border-radius: 50%; background: var(--brand-primary); }
.time { flex: 1 1 0; min-width: 0; max-width: 140px; height: 40px; padding: 0 var(--space-4); border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--bg-default); color: var(--text-primary); }
.closed { flex: 1; }
.notice { display: flex; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); }
.notice--warn { background: var(--status-warning-bg); color: var(--status-warning); }
.row-between { display: flex; align-items: center; justify-content: space-between; }
.doctors { display: flex; flex-direction: column; gap: var(--space-4); margin: 0; padding: 0; list-style: none; }
.doctor { display: flex; align-items: center; gap: var(--space-12); padding: var(--space-8) 0; }
.doctor__text { display: flex; flex: 1; flex-direction: column; min-width: 0; }
.avatar { display: grid; place-items: center; flex: none; width: 36px; height: 36px; border-radius: 50%; background: var(--bg-muted); color: var(--text-secondary); }
.link { padding: 0; border: 0; background: none; color: var(--text-secondary); cursor: pointer; }
.link:hover { color: var(--brand-primary); }
.bar { position: sticky; bottom: 0; display: flex; align-items: center; gap: var(--space-8); margin: auto calc(-1 * var(--space-32)) 0; padding: var(--space-16) var(--space-32); border-top: 1px solid var(--border-default); background: var(--bg-default); }
</style>
