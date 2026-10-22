<script lang="ts">
import type { ProcedureCode as PC } from '@/types/contract'
/** 만료 후 다시 요청(D-37) 등에서 미리 채울 값 */
export interface BookingInitial {
  procedure?: PC
  optionId?: number
  slotId?: number
  doctorId?: number
  date?: string
  note?: string
}
</script>

<script setup lang="ts">
// C8 예약 시트 (Figma 1:3832 · 1:4016 · 1:4282) + Edge ④ 직전 마감 → 대안 시간 (1:7027)
// 1 시술·가격 옵션·의료진 → 2 날짜·시간(AVAILABLE 슬롯만) → 3 메모·확인 → POST /api/reservations (Idempotency-Key)
// initial 이 있으면(만료 후 다시 요청, D-37) 같은 조건으로 3단계부터
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BottomSheet from '../ui/BottomSheet.vue'
import AppButton from '../ui/AppButton.vue'
import AppChip from '../ui/AppChip.vue'
import AppIcon from '../ui/AppIcon.vue'
import TextField from '../ui/TextField.vue'
import { useReservationStore } from '@/stores/reservation'
import { catalogApi, toApiError } from '@/api'
import { fmtDate, fmtDateTime, fmtHm, fmtKrw, fmtMonth, seoulDate, weekdayNames } from '@/utils/format'
import type { HospitalDetail, ProcedureCode, Reservation, Slot } from '@/types/contract'

const props = defineProps<{ open: boolean; hospital: HospitalDetail; initial?: BookingInitial | null }>()
const emit = defineEmits<{ close: []; done: [r: Reservation] }>()
const { t } = useI18n()
const store = useReservationStore()

const step = ref<1 | 2 | 3>(1)
const procedure = ref<ProcedureCode | ''>('')
const optionId = ref<number | null>(null)
const doctorId = ref<number | null>(null)
const month = ref(seoulDate().slice(0, 7))
const day = ref<string | null>(null)
const slots = ref<Slot[]>([])
const slotId = ref<number | null>(null)
const note = ref('')
const submitting = ref(false)
const loadingSlots = ref(false)
const slotsFailed = ref(false)
/** loadSlots 순번 — 달을 빨리 넘길 때 늦게 온 이전 달 응답 무시 */
let slotsSeq = 0
const conflict = ref<Slot[] | null>(null)
const altSlotId = ref<number | null>(null)
const errorMsg = ref<string | null>(null)

const entry = computed(() => props.hospital.procedures.find((p) => p.procedure.code === procedure.value) ?? null)
const option = computed(() => entry.value?.options.find((o) => o.id === optionId.value) ?? null)
const doctors = computed(() => props.hospital.doctors.filter((d) => !procedure.value || d.specialties.includes(procedure.value)))
const doctor = computed(() => props.hospital.doctors.find((d) => d.id === doctorId.value) ?? null)
const slot = computed(() => slots.value.find((s) => s.id === slotId.value) ?? null)
const daySlots = computed(() => slots.value.filter((s) => seoulDate(s.startAt) === day.value))
const availableDays = computed(() => new Set(slots.value.map((s) => seoulDate(s.startAt))))

/** 달력: 월요일 시작이 아니라 일요일 시작 (Figma) */
const calendar = computed(() => {
  const [y, m] = month.value.split('-').map(Number)
  const first = new Date(Date.UTC(y, m - 1, 1))
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate()
  const cells: (string | null)[] = Array(first.getUTCDay()).fill(null)
  for (let d = 1; d <= days; d++) cells.push(`${month.value}-${String(d).padStart(2, '0')}`)
  return cells
})
const today = seoulDate()
const monthLabel = computed(() => fmtMonth(month.value))
const weekdays = computed(() => weekdayNames())

watch(
  () => props.open,
  (open) => {
    if (!open) return
    store.startBooking()
    conflict.value = null
    errorMsg.value = null
    const init = props.initial
    procedure.value = init?.procedure ?? props.hospital.procedures[0]?.procedure.code ?? ''
    optionId.value = init?.optionId ?? entry.value?.options[0]?.id ?? null
    doctorId.value = init?.doctorId ?? null
    note.value = init?.note ?? ''
    day.value = init?.date ?? null
    month.value = (init?.date ?? today).slice(0, 7)
    slotId.value = init?.slotId ?? null
    step.value = init?.slotId ? 3 : 1
    if (init?.slotId) void loadSlots()
  },
  { immediate: true },
)
watch(procedure, () => {
  if (!entry.value?.options.some((o) => o.id === optionId.value)) optionId.value = entry.value?.options[0]?.id ?? null
  if (doctorId.value && !doctors.value.some((d) => d.id === doctorId.value)) doctorId.value = null
})

async function loadSlots() {
  if (!procedure.value) return
  const seq = ++slotsSeq
  loadingSlots.value = true
  slotsFailed.value = false
  slots.value = []
  const [y, m] = month.value.split('-').map(Number)
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate()
  const from = month.value === today.slice(0, 7) ? today : `${month.value}-01`
  try {
    const list = await catalogApi.slots(props.hospital.id, {
      procedure: procedure.value,
      dateFrom: from,
      dateTo: `${month.value}-${last}`,
      doctorId: doctorId.value ?? undefined,
      limit: 500,
    })
    if (seq !== slotsSeq) return
    // 오늘 이미 지난 시간은 고를 수 없게
    slots.value = list.filter((s) => new Date(s.startAt).getTime() > Date.now())
  } catch {
    if (seq === slotsSeq) slotsFailed.value = true
    return
  } finally {
    if (seq === slotsSeq) loadingSlots.value = false
  }
  if (!day.value || !availableDays.value.has(day.value)) day.value = [...availableDays.value].sort()[0] ?? null
}
function goStep2() {
  step.value = 2
  slotId.value = null
  void loadSlots()
}
function shiftMonth(delta: number) {
  const [y, m] = month.value.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1 + delta, 1))
  month.value = d.toISOString().slice(0, 7)
  day.value = null
  void loadSlots()
}

async function submit(targetSlotId = slotId.value) {
  if (!targetSlotId || !procedure.value) return
  submitting.value = true
  errorMsg.value = null
  try {
    const r = await store.create({
      hospitalId: props.hospital.id,
      slotId: targetSlotId,
      procedureCode: procedure.value,
      priceOptionId: optionId.value,
      note: note.value.trim() || null,
    })
    emit('done', r)
  } catch (e) {
    const err = toApiError(e)
    if (err?.code === 'SLOT_UNAVAILABLE') {
      conflict.value = store.alternatives
      altSlotId.value = store.alternatives[0]?.id ?? null
    } else errorMsg.value = err?.message ?? t('common.error')
  } finally {
    submitting.value = false
  }
}
/** Edge ④ 대안 시간으로 요청: 다른 슬롯이므로 새 요청 (새 Idempotency-Key) */
async function submitAlternative() {
  if (!altSlotId.value) return
  store.startBooking()
  const alt = conflict.value?.find((s) => s.id === altSlotId.value)
  conflict.value = null
  slots.value = alt ? [alt, ...slots.value] : slots.value
  slotId.value = altSlotId.value
  await submit(altSlotId.value)
}
</script>

<template>
  <BottomSheet :open="open && !conflict" :title="t('booking.title')" @close="emit('close')">
    <div class="progress" aria-hidden="true"><span v-for="i in 3" :key="i" :class="{ on: i <= step }" /></div>
    <p class="step t-caption-12-sb">{{ t('booking.step', { n: step }) }} · {{ t(`booking.steps.${step}`) }}</p>

    <!-- 1 시술 · 가격 옵션 · 의료진 -->
    <template v-if="step === 1">
      <TextField
        v-model="procedure"
        :label="t('booking.procedure')"
        :options="hospital.procedures.map((p) => ({ value: p.procedure.code, label: p.procedure.name }))"
      />
      <fieldset class="group">
        <legend class="t-caption-13 label">{{ t('booking.option') }}</legend>
        <label v-for="o in entry?.options ?? []" :key="o.id" class="radio" :class="{ 'radio--on': optionId === o.id }">
          <input v-model="optionId" type="radio" name="option" :value="o.id" />
          <span class="dot" aria-hidden="true" />
          <span class="radio__text">
            <span class="t-body-14-sb">{{ o.product }}<template v-if="o.dose"> · {{ o.dose }}</template></span>
            <span class="t-caption-12 muted">{{ o.vatIncluded ? t('compare.vatIn') : t('compare.vatEx') }}<template v-if="o.conditions"> · {{ o.conditions }}</template></span>
          </span>
          <span class="t-body-14-sb">{{ fmtKrw(o.priceKrw) }}</span>
        </label>
      </fieldset>
      <div class="group">
        <span class="t-caption-13 label">{{ t('booking.doctor') }}</span>
        <div class="chips">
          <AppChip :selected="doctorId === null" @click="doctorId = null">{{ t('booking.anyDoctor') }}</AppChip>
          <AppChip v-for="d in doctors" :key="d.id" :selected="doctorId === d.id" @click="doctorId = d.id">{{ d.name }} {{ d.title }}</AppChip>
        </div>
        <p class="t-caption-12 muted">{{ t('booking.doctorNote') }}</p>
      </div>
    </template>

    <!-- 2 날짜 · 시간 -->
    <template v-else-if="step === 2">
      <p class="summary t-caption-13">
        <span>{{ entry?.procedure.name }}<template v-if="option"> · {{ option.product }}</template><template v-if="doctor"> · {{ doctor.name }}</template></span>
        <button type="button" class="link" @click="step = 1">{{ t('booking.change') }}</button>
      </p>
      <div class="cal-head">
        <button type="button" :aria-label="t('booking.prevMonth')" :disabled="month <= today.slice(0, 7)" @click="shiftMonth(-1)"><AppIcon name="chevron-left" :size="20" /></button>
        <span class="t-body-16-sb">{{ monthLabel }}</span>
        <button type="button" :aria-label="t('booking.nextMonth')" @click="shiftMonth(1)"><AppIcon name="chevron-right" :size="20" /></button>
      </div>
      <div class="cal" role="grid">
        <span v-for="(w, i) in weekdays" :key="`w${i}`" class="cal__w t-caption-12" :class="{ sun: i === 0 }">{{ w }}</span>
        <template v-for="(d, i) in calendar" :key="i">
          <span v-if="!d" />
          <button
            v-else
            type="button"
            class="cal__d t-body-14"
            :class="{ 'cal__d--today': d === today, 'cal__d--on': d === day }"
            :disabled="!availableDays.has(d)"
            @click="(day = d), (slotId = null)"
          >
            {{ Number(d.slice(8)) }}
          </button>
        </template>
      </div>
      <div v-if="day" class="times-head t-caption-13">
        <span class="label">{{ t('booking.timesOn', { date: fmtDate(day) }) }}</span>
        <span class="muted">{{ t('booking.duration', { n: entry?.procedure.durationMin ?? 30 }) }}</span>
      </div>
      <p v-if="loadingSlots" class="t-caption-13 muted">{{ t('common.loading') }}</p>
      <div v-else-if="slotsFailed" class="center" role="alert">
        <p class="t-body-14 muted">{{ t('booking.slotsFailed') }}</p>
        <AppButton variant="secondary" size="s" icon="refresh-cw" @click="loadSlots">{{ t('common.retry') }}</AppButton>
      </div>
      <p v-else-if="!availableDays.size" class="t-body-14 muted center">{{ t('booking.noSlots') }}</p>
      <div v-else class="times">
        <button
          v-for="s in daySlots"
          :key="s.id"
          type="button"
          class="time t-body-14"
          :class="{ 'time--on': slotId === s.id }"
          :aria-pressed="slotId === s.id"
          @click="slotId = s.id"
        >
          {{ fmtHm(s.startAt) }}
        </button>
      </div>
    </template>

    <!-- 3 메모 · 확인 -->
    <template v-else>
      <dl class="confirm">
        <div><dt>{{ t('booking.hospital') }}</dt><dd>{{ hospital.name }}</dd></div>
        <div><dt>{{ t('booking.when') }}</dt><dd>{{ slot ? fmtDateTime(slot.startAt) : '—' }}</dd></div>
        <div><dt>{{ t('booking.doctor') }}</dt><dd>{{ slot?.doctorName ?? doctor?.name ?? '—' }}</dd></div>
        <div><dt>{{ t('booking.procedure') }}</dt><dd>{{ entry?.procedure.name }}<template v-if="option"> · {{ option.product }}</template></dd></div>
        <div>
          <dt>{{ t('booking.price') }}</dt>
          <dd>{{ option ? `${fmtKrw(option.priceKrw)} · ${option.vatIncluded ? t('compare.vatIn') : t('compare.vatEx')}` : t('common.needsCheck') }}</dd>
        </div>
      </dl>
      <label class="memo">
        <span class="t-caption-13 label">{{ t('booking.memo') }}</span>
        <textarea v-model="note" class="t-body-15" rows="3" maxlength="200" :placeholder="t('chat.approval.notePlaceholder')" />
        <span class="t-caption-12 muted">{{ note.length }} / 200</span>
      </label>
      <p class="notice t-caption-13"><AppIcon name="clock" :size="16" />{{ t('booking.notice') }}</p>
      <p v-if="errorMsg" class="error t-caption-12" role="alert">{{ errorMsg }}</p>
    </template>

    <template #footer>
      <AppButton v-if="step === 1" size="l" block :disabled="!procedure" @click="goStep2">{{ t('booking.next') }}</AppButton>
      <template v-else>
        <AppButton variant="outline" size="l" @click="step = step === 3 ? 2 : 1">{{ t('booking.prev') }}</AppButton>
        <AppButton v-if="step === 2" size="l" block :disabled="!slotId" @click="step = 3">{{ t('booking.next') }}</AppButton>
        <AppButton v-else size="l" block :loading="submitting" @click="submit()">{{ t('booking.submit') }}</AppButton>
      </template>
    </template>
  </BottomSheet>

  <!-- Edge ④ 방금 마감 → 대안 시간 (409 details.alternatives, 최대 3) -->
  <BottomSheet :open="!!conflict" :title="t('booking.conflict.title')" @close="conflict = null">
    <p class="gone t-body-14"><AppIcon name="clock" :size="16" /><s>{{ slot ? `${fmtDateTime(slot.startAt)} · ${slot.doctorName}` : '' }}</s></p>
    <p class="t-body-14 secondary">{{ t('booking.conflict.body') }}</p>
    <div class="group">
      <label v-for="s in conflict ?? []" :key="s.id" class="radio" :class="{ 'radio--on': altSlotId === s.id }">
        <input v-model="altSlotId" type="radio" name="alt" :value="s.id" />
        <span class="dot" aria-hidden="true" />
        <span class="radio__text">
          <span class="t-body-14-sb">{{ fmtDateTime(s.startAt) }}</span>
          <span class="t-caption-12 muted">{{ s.doctorName }}</span>
        </span>
      </label>
      <p v-if="!conflict?.length" class="t-body-14 muted">{{ t('booking.noSlots') }}</p>
    </div>
    <p class="notice t-caption-13"><AppIcon name="info" :size="16" />{{ t('booking.conflict.notice') }}</p>
    <template #footer>
      <AppButton variant="outline" size="l" @click="(conflict = null), goStep2()">{{ t('booking.conflict.otherDate') }}</AppButton>
      <AppButton size="l" block :disabled="!altSlotId" :loading="submitting" @click="submitAlternative">{{ t('booking.conflict.request') }}</AppButton>
    </template>
  </BottomSheet>
</template>

<style scoped>
.progress { display: flex; gap: var(--space-4); margin-bottom: var(--space-8); }
.progress span { flex: 1; height: 4px; border-radius: 2px; background: var(--bg-muted); }
.progress span.on { background: var(--brand-primary); }
.step { margin-bottom: var(--space-16); color: var(--text-brand); }
.group { display: flex; flex-direction: column; gap: var(--space-8); margin: var(--space-16) 0 0; padding: 0; border: 0; }
.label { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.secondary { color: var(--text-secondary); }
.center { text-align: center; }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.radio { position: relative; display: flex; align-items: center; gap: var(--space-12); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-md); cursor: pointer; }
.radio input { position: absolute; opacity: 0; }
.radio--on { border: 1.5px solid var(--brand-primary); background: var(--brand-subtle); }
.radio__text { display: flex; flex: 1; flex-direction: column; gap: var(--space-2); }
.dot { flex: none; width: 20px; height: 20px; border: 1.5px solid var(--border-strong); border-radius: 50%; background: var(--bg-default); }
.radio--on .dot { border: 6px solid var(--brand-primary); }
.radio input:focus-visible ~ .dot { outline: 2px solid var(--border-focus); outline-offset: 2px; }
.summary { display: flex; justify-content: space-between; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-sm); background: var(--bg-subtle); color: var(--text-secondary); }
.link { padding: 0; border: 0; background: none; color: var(--text-brand); font-weight: 600; }
.cal-head { display: flex; align-items: center; justify-content: space-between; margin: var(--space-16) 0 var(--space-8); }
.cal-head button { display: grid; place-items: center; border: 0; background: none; color: var(--icon-default); }
.cal-head button:disabled { color: var(--icon-subtle); }
.cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: var(--space-4); text-align: center; }
.cal__w { padding: var(--space-4) 0; color: var(--text-tertiary); }
.cal__w.sun { color: var(--status-danger); }
.cal__d { justify-self: center; width: 40px; height: 40px; border: 0; border-radius: 50%; background: none; color: var(--text-primary); }
.cal__d:disabled { color: var(--text-disabled); }
.cal__d--today { box-shadow: inset 0 0 0 1px var(--border-strong); }
.cal__d--on { background: var(--brand-primary); color: var(--text-inverse); font-weight: 600; box-shadow: none; }
.times-head { display: flex; justify-content: space-between; margin: var(--space-16) 0 var(--space-8); }
.times { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-8); }
.time { height: 44px; border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--bg-default); }
.time--on { border: 1.5px solid var(--brand-primary); background: var(--brand-subtle); color: var(--brand-text); font-weight: 600; }
.confirm { display: flex; flex-direction: column; gap: 10px; margin: 0; padding: var(--space-16); border-radius: var(--radius-md); background: var(--bg-subtle); }
.confirm div { display: flex; gap: var(--space-12); }
.confirm dt { flex: none; width: 48px; font: 500 13px/18px var(--font-sans); color: var(--text-tertiary); }
.confirm dd { margin: 0; font: 600 14px/20px var(--font-sans); }
.memo { display: flex; flex-direction: column; gap: var(--space-6); margin-top: var(--space-16); }
.memo textarea { padding: var(--space-12) 14px; border: 1px solid var(--border-default); border-radius: var(--radius-md); resize: vertical; }
.notice { display: flex; gap: var(--space-8); margin-top: var(--space-16); padding: var(--space-12); border-radius: var(--radius-md); background: var(--status-info-bg); color: var(--status-info); }
.notice .icon { flex: none; margin-top: 1px; }
.error { margin-top: var(--space-8); color: var(--status-danger); }
.gone { display: flex; align-items: center; gap: var(--space-8); margin-bottom: var(--space-12); padding: var(--space-12); border-radius: var(--radius-md); background: var(--status-danger-bg); color: var(--status-danger); }
</style>
