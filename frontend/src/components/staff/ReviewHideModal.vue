<script setup lang="ts">
// H5-1-D 리뷰 숨기기 모달 (Figma '숨김 요청'을 바로 숨김으로 바꿈: 운영팀 검토 없음)
// 사유 필수, 기타는 자세한 내용 필수 (backend 와 같은 규칙)
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '../ui/AppIcon.vue'
import AppButton from '../ui/AppButton.vue'
import { fmtDate } from '@/utils/format'
import type { AdminReview, HideReason, HideRequest } from '@/types/contract'

const props = defineProps<{ open: boolean; review: AdminReview | null; busy?: boolean }>()
const emit = defineEmits<{ close: []; submit: [body: HideRequest] }>()
const { t } = useI18n()

const REASONS: HideReason[] = ['PRIVACY', 'ABUSE', 'FALSE_INFO', 'SPAM', 'OTHER']
const reason = ref<HideReason | null>(null)
const detail = ref('')

const el = ref<HTMLDialogElement | null>(null)
watch([() => props.open && !!props.review, el], ([open, d]) => {
  if (!d) return
  if (open && !d.open) d.showModal()
  else if (!open && d.open) d.close()
})
watch(
  () => props.open,
  (open) => {
    if (!open) return
    reason.value = props.review?.hidden?.reason ?? null
    detail.value = props.review?.hidden?.detail ?? ''
  },
)
function requestClose() {
  if (!props.busy) emit('close')
}
const canSubmit = computed(() => !!reason.value && (reason.value !== 'OTHER' || !!detail.value.trim()))
function submit() {
  if (!canSubmit.value || !reason.value) return
  emit('submit', { reason: reason.value, detail: detail.value.trim() || undefined })
}
</script>

<template>
  <dialog ref="el" class="modal" :aria-label="t('reviewAdmin.hide.title')" @cancel.prevent="requestClose" @click.self="requestClose">
    <template v-if="review">
      <header class="head">
        <div>
          <h2 class="t-title-18">{{ t('reviewAdmin.hide.title') }}</h2>
          <p class="t-caption-13 secondary">{{ t('reviewAdmin.hide.sub') }}</p>
        </div>
        <button type="button" class="x" :aria-label="t('common.close')" :disabled="busy" @click="requestClose"><AppIcon name="x" /></button>
      </header>
      <div class="body">
        <div class="quote">
          <p class="t-caption-12 muted">
            <span class="stars" aria-hidden="true"><AppIcon v-for="i in 5" :key="i" name="star" :size="12" :class="{ on: i <= review.rating }" /></span>
            {{ review.procedureName }} · {{ fmtDate(review.createdAt, { weekday: false }) }}
          </p>
          <p class="t-body-14 clamp">{{ review.translatedContent ?? review.content }}</p>
        </div>
        <fieldset class="group">
          <legend class="t-caption-13">{{ t('reviewAdmin.hide.reason') }} <span class="req">*</span></legend>
          <label v-for="r in REASONS" :key="r" class="radio t-body-14">
            <input v-model="reason" type="radio" name="hide-reason" :value="r" />
            {{ t(`reviewAdmin.hide.reasons.${r}`) }}
          </label>
        </fieldset>
        <label class="group">
          <span class="t-caption-13">{{ t('reviewAdmin.hide.detail') }}<span v-if="reason === 'OTHER'" class="req"> *</span></span>
          <textarea v-model="detail" class="t-body-14" rows="3" maxlength="300" :placeholder="t('reviewAdmin.hide.detailPlaceholder')" />
          <span class="t-caption-12 muted">{{ t('reviewAdmin.hide.detailCount', { n: detail.length }) }}</span>
        </label>
        <p class="notice t-caption-13"><AppIcon name="alert-triangle" :size="16" />{{ t('reviewAdmin.hide.notice') }}</p>
      </div>
      <footer class="foot">
        <AppButton variant="outline" :disabled="busy" @click="requestClose">{{ t('common.cancel') }}</AppButton>
        <AppButton variant="danger" :disabled="!canSubmit" :loading="busy" @click="submit">{{ t('reviewAdmin.hide.submit') }}</AppButton>
      </footer>
    </template>
  </dialog>
</template>

<style scoped>
.modal::backdrop { background: rgb(0 0 0 / 45%); }
.modal { width: 520px; max-width: calc(100% - 32px); max-height: 90dvh; padding: 0; border: 0; color: inherit; border-radius: var(--radius-xl); background: var(--surface-sheet); box-shadow: var(--shadow-dialog); }
.modal[open] { display: flex; flex-direction: column; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-12); padding: var(--space-24) var(--space-24) var(--space-8); }
.head > div { display: flex; flex-direction: column; gap: var(--space-4); }
.x { border: 0; background: none; color: var(--icon-default); }
.body { display: flex; flex-direction: column; gap: var(--space-16); padding: var(--space-8) var(--space-24) var(--space-16); overflow-y: auto; }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.req { color: var(--status-danger); }
.quote { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-12); border-radius: var(--radius-md); background: var(--bg-subtle); }
.clamp { display: -webkit-box; overflow: hidden; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
.stars { display: inline-flex; gap: 1px; margin-right: var(--space-4); vertical-align: -2px; color: var(--border-strong); }
.stars .on { color: var(--rating-star); fill: var(--rating-star); }
.group { display: flex; flex-direction: column; gap: var(--space-8); margin: 0; padding: 0; border: 0; }
.radio { display: flex; align-items: center; gap: var(--space-8); cursor: pointer; }
.radio input { width: 18px; height: 18px; accent-color: var(--brand-primary); }
textarea { padding: var(--space-12); border: 1px solid var(--border-default); border-radius: var(--radius-md); resize: vertical; }
.notice { display: flex; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); background: var(--status-warning-bg); color: var(--status-warning); }
.foot { display: flex; justify-content: flex-end; gap: var(--space-8); padding: var(--space-12) var(--space-24) var(--space-24); }
</style>
