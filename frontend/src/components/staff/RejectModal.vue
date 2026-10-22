<script setup lang="ts">
// H2-1-D 반려 모달: 사유(필수) + 덧붙이기 + 대안 시간 ≤3 → RejectRequest {reason, alternativeSlotIds}
// 사유는 고른 칩 + 덧붙인 글을 합쳐 한 문자열로 보냄. 번역 없이 그대로 고객에게 보임 (13-2)
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '../ui/AppIcon.vue'
import AppChip from '../ui/AppChip.vue'
import AppButton from '../ui/AppButton.vue'
import { catalogApi } from '@/api'
import { fmtDateTime, seoulDate } from '@/utils/format'
import type { RejectRequest, Reservation, Slot } from '@/types/contract'

const props = defineProps<{ open: boolean; reservation: Reservation | null; busy?: boolean }>()
const emit = defineEmits<{ close: []; submit: [body: RejectRequest] }>()
const { t } = useI18n()

// 네이티브 <dialog> + showModal(): ESC·포커스 가두기·뒤 화면 비활성·포커스 복귀. 제출 중(busy)에는 닫지 않음
const el = ref<HTMLDialogElement | null>(null)
watch([() => props.open && !!props.reservation, el], ([open, d]) => {
  if (!d) return
  if (open && !d.open) d.showModal()
  else if (!open && d.open) d.close()
})
function requestClose() {
  if (!props.busy) emit('close')
}

const PRESETS = ['slotTaken', 'doctorChange', 'needsConsult', 'other'] as const
const preset = ref<(typeof PRESETS)[number] | null>(null)
const detail = ref('')
const picked = ref<Slot[]>([])
const pool = ref<Slot[]>([])
const picking = ref(false)
const poolLoading = ref(false)

watch(
  () => props.open,
  async (open) => {
    if (!open || !props.reservation) return
    // 사유를 미리 골라 두지 않는다 (확인 없이 '슬롯 마감'으로 나가던 문제)
    preset.value = null
    detail.value = ''
    picked.value = []
    picking.value = false
    const r = props.reservation
    const from = seoulDate()
    const to = seoulDate(new Date(Date.now() + 14 * 86400000))
    poolLoading.value = true
    pool.value = (await catalogApi.slots(r.hospital.id, { procedure: r.procedure.code, dateFrom: from, dateTo: to, limit: 60 }).catch(() => [])).filter(
      (s) => s.id !== r.slot.id,
    )
    poolLoading.value = false
  },
)
// '기타'는 상세 사유가 있어야 고객이 이해할 수 있다
const canSubmit = computed(() => (preset.value && preset.value !== 'other') || !!detail.value.trim())
const reason = computed(() => [preset.value ? t(`staff.reject.presets.${preset.value}`) : '', detail.value.trim()].filter(Boolean).join(' — '))
const candidates = computed(() => pool.value.filter((s) => !picked.value.some((p) => p.id === s.id)).slice(0, 12))

function add(s: Slot) {
  if (picked.value.length < 3) picked.value.push(s)
  picking.value = false
}
function submit() {
  if (!canSubmit.value) return
  emit('submit', { reason: reason.value.slice(0, 500), alternativeSlotIds: picked.value.map((s) => s.id) })
}
</script>

<template>
  <!-- 바깥(::backdrop) 클릭은 dialog 자신이 target -->
  <dialog ref="el" class="modal" :aria-label="t('staff.reject.title')" @cancel.prevent="requestClose" @click.self="requestClose">
    <template v-if="reservation">
        <header class="head">
          <h2 class="t-title-18">{{ t('staff.reject.title') }}</h2>
          <button type="button" class="x" :aria-label="t('common.close')" :disabled="busy" @click="requestClose"><AppIcon name="x" /></button>
        </header>
        <div class="body">
          <p class="t-caption-13 secondary">{{ reservation.customer?.name }} · {{ reservation.procedure.name }} · {{ fmtDateTime(reservation.slot.startAt) }}</p>
          <div class="group">
            <span class="t-body-14-sb">{{ t('staff.reject.reason') }}</span>
            <div class="chips">
              <AppChip v-for="p in PRESETS" :key="p" :selected="preset === p" @click="preset = preset === p ? null : p">{{ t(`staff.reject.presets.${p}`) }}</AppChip>
            </div>
          </div>
          <label class="group">
            <span class="t-caption-13 secondary">{{ t('staff.reject.detail') }}</span>
            <textarea v-model="detail" class="t-body-14" rows="2" maxlength="400" />
            <span class="t-caption-12 muted">{{ t('staff.reject.detailNote') }}</span>
          </label>
          <div class="group">
            <div class="row-between">
              <span class="t-body-14-sb">{{ t('staff.reject.alternatives') }}</span>
              <span class="t-caption-12 muted">{{ picked.length }} / 3</span>
            </div>
            <div v-for="s in picked" :key="s.id" class="alt t-body-14-sb">
              <AppIcon name="calendar" :size="16" />
              <span>{{ fmtDateTime(s.startAt) }} · {{ s.doctorName }}</span>
              <button type="button" :aria-label="t('compare.remove')" @click="picked = picked.filter((x) => x.id !== s.id)"><AppIcon name="x" :size="16" /></button>
            </div>
            <button v-if="picked.length < 3 && !picking" type="button" class="add t-caption-13" @click="picking = true">
              <AppIcon name="plus" :size="16" />{{ t('staff.reject.addSlot') }}
            </button>
            <div v-if="picking" class="pool">
              <button v-for="s in candidates" :key="s.id" type="button" class="slot t-caption-13" @click="add(s)">{{ fmtDateTime(s.startAt) }} · {{ s.doctorName }}</button>
              <p v-if="poolLoading" class="t-caption-12 muted">{{ t('common.loading') }}</p>
              <p v-else-if="!candidates.length" class="t-caption-12 muted">{{ t('booking.noSlots') }}</p>
            </div>
          </div>
          <p class="notice t-caption-13"><AppIcon name="info" :size="16" />{{ t('staff.reject.notice') }}</p>
        </div>
        <footer class="foot">
          <AppButton variant="ghost" :disabled="busy" @click="requestClose">{{ t('common.cancel') }}</AppButton>
          <AppButton variant="danger" block :disabled="!canSubmit" :loading="busy" @click="submit">{{ t('staff.reject.submit') }}</AppButton>
        </footer>
    </template>
  </dialog>
</template>

<style scoped>
.modal::backdrop { background: rgb(0 0 0 / 45%); }
.modal { width: 560px; max-width: calc(100% - 32px); max-height: 90dvh; padding: 0; border: 0; color: inherit; border-radius: var(--radius-xl); background: var(--surface-sheet); box-shadow: var(--shadow-dialog); }
.modal[open] { display: flex; flex-direction: column; }
.head { display: flex; align-items: center; justify-content: space-between; padding: var(--space-20) var(--space-20) var(--space-8); }
.x { border: 0; background: none; color: var(--icon-default); }
.body { display: flex; flex-direction: column; gap: var(--space-16); padding: var(--space-8) var(--space-20) var(--space-16); overflow-y: auto; }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.group { display: flex; flex-direction: column; gap: var(--space-8); }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
textarea { padding: var(--space-12); border: 1px solid var(--border-default); border-radius: var(--radius-md); resize: vertical; }
.row-between { display: flex; justify-content: space-between; }
.alt { display: flex; align-items: center; gap: var(--space-8); padding: var(--space-8) var(--space-12); border: 1px solid var(--brand-border); border-radius: var(--radius-md); background: var(--brand-subtle); color: var(--brand-text); }
.alt span { flex: 1; }
.alt button { border: 0; background: none; color: var(--icon-subtle); }
.add { display: flex; align-items: center; justify-content: center; gap: var(--space-4); height: 36px; border: 1px dashed var(--border-strong); border-radius: var(--radius-md); background: none; color: var(--text-secondary); }
.pool { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-6); max-height: 180px; overflow-y: auto; }
.slot { padding: var(--space-8); border: 1px solid var(--border-default); border-radius: var(--radius-sm); background: var(--bg-default); text-align: left; }
.slot:hover { border-color: var(--brand-border); }
.notice { display: flex; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); background: var(--status-info-bg); color: var(--status-info); }
.foot { display: flex; gap: var(--space-8); padding: var(--space-12) var(--space-20) var(--space-20); border-top: 1px solid var(--border-default); }
</style>
