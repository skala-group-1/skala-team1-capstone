<script setup lang="ts">
// 고객 병원 상세 리뷰 아래 '병원 답글' (V106). 번역본이 있으면 번역본, 원문 토글
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fmtDate } from '@/utils/format'
import type { ReviewReply } from '@/types/contract'

defineProps<{ reply: ReviewReply }>()
const { t } = useI18n()
const original = ref(false)
</script>

<template>
  <div class="reply">
    <p class="row">
      <b class="t-caption-12-sb">{{ t('reviewReply.title') }}</b>
      <span class="t-caption-11 muted">{{ fmtDate(reply.updatedAt, { weekday: false, year: true }) }}</span>
    </p>
    <p class="t-body-14">{{ reply.translatedContent && !original ? reply.translatedContent : reply.content }}</p>
    <button v-if="reply.translatedContent" type="button" class="toggle t-caption-11" @click="original = !original">
      {{ original ? t('reviewReply.showTranslation') : t('reviewReply.showOriginal') }}
    </button>
  </div>
</template>

<style scoped>
.reply { display: flex; flex-direction: column; gap: var(--space-4); margin-top: var(--space-4); padding: var(--space-12); border-radius: var(--radius-md); background: var(--bg-subtle); }
.row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-8); }
.muted { color: var(--text-tertiary); }
.toggle { align-self: flex-start; padding: 0; border: 0; background: none; color: var(--brand-primary); text-decoration: underline; cursor: pointer; }
</style>
