<script setup lang="ts">
// 리뷰 작성 시트: 별점(1~5) + 후기(10~1000자) → POST /api/reservations/{id}/review
// 작성 가능 여부는 backend 가 판단(Reservation.reviewable). 여기서는 입력 길이만 안내한다
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BottomSheet from '../ui/BottomSheet.vue'
import AppButton from '../ui/AppButton.vue'
import AppIcon from '../ui/AppIcon.vue'
import { reservationApi, toApiError } from '@/api'
import type { Reservation, Review } from '@/types/contract'

const MIN = 10
const MAX = 1000

const props = defineProps<{ open: boolean; reservation: Reservation }>()
const emit = defineEmits<{ close: []; done: [review: Review] }>()
const { t } = useI18n()

const rating = ref(0)
const content = ref('')
const submitting = ref(false)
const errorMsg = ref<string | null>(null)

const length = computed(() => content.value.trim().length)
const valid = computed(() => rating.value >= 1 && length.value >= MIN && length.value <= MAX)

watch(
  () => props.open,
  (open) => {
    if (!open) return
    rating.value = 0
    content.value = ''
    errorMsg.value = null
  },
)

async function submit() {
  if (!valid.value) return
  submitting.value = true
  errorMsg.value = null
  try {
    const review = await reservationApi.writeReview(props.reservation.id, { rating: rating.value, content: content.value.trim() })
    emit('done', review)
  } catch (e) {
    const err = toApiError(e)
    errorMsg.value = err?.code === 'REVIEW_ALREADY_EXISTS' ? t('reservations.review.already') : (err?.message ?? t('common.error'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <BottomSheet :open="open" :title="t('reservations.review.sheetTitle')" @close="emit('close')">
    <p class="t-body-14 secondary">{{ reservation.hospital.name }} · {{ reservation.procedure.name }}</p>

    <fieldset class="rating">
      <legend class="t-caption-13 label">{{ t('reservations.review.rating') }}</legend>
      <div class="stars" role="radiogroup">
        <button
          v-for="n in 5"
          :key="n"
          type="button"
          role="radio"
          class="star"
          :class="{ 'star--on': n <= rating }"
          :aria-checked="n === rating"
          :aria-label="t('reservations.review.star', { n })"
          @click="rating = n"
        >
          <AppIcon name="star" :size="32" />
        </button>
      </div>
    </fieldset>

    <label class="memo">
      <span class="t-caption-13 label">{{ t('reservations.review.content') }}</span>
      <textarea v-model="content" class="t-body-15" rows="5" :maxlength="MAX" :placeholder="t('reservations.review.placeholder')" />
      <span class="t-caption-12" :class="length > 0 && length < MIN ? 'error' : 'muted'">
        <template v-if="length > 0 && length < MIN">{{ t('reservations.review.minLength') }} · </template>{{ length }} / {{ MAX }}
      </span>
    </label>
    <p v-if="errorMsg" class="error t-caption-12" role="alert">{{ errorMsg }}</p>

    <template #footer>
      <AppButton size="l" block :disabled="!valid" :loading="submitting" @click="submit">{{ t('reservations.review.submit') }}</AppButton>
    </template>
  </BottomSheet>
</template>

<style scoped>
.secondary { color: var(--text-secondary); }
.label { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.error { color: var(--status-danger); }
.rating { display: flex; flex-direction: column; gap: var(--space-8); margin: var(--space-16) 0 0; padding: 0; border: 0; }
.rating legend { padding: 0; margin-bottom: var(--space-8); }
.stars { display: flex; gap: var(--space-4); }
.star { display: grid; place-items: center; width: 44px; height: 44px; padding: 0; border: 0; background: none; color: var(--border-strong); cursor: pointer; }
.star--on { color: var(--rating-star); }
.star--on .icon { fill: var(--rating-star); }
.memo { display: flex; flex-direction: column; gap: var(--space-6); margin-top: var(--space-16); }
.memo textarea { padding: var(--space-12) 14px; border: 1px solid var(--border-default); border-radius: var(--radius-md); resize: vertical; }
</style>
