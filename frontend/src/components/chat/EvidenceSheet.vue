<script setup lang="ts">
// C4-1 근거 문서 바텀시트: 답변에 쓰인 Source 목록 → 펼치면 섹션 발췌(snippet), "원문 보기"는 GET /api/docs/{docId}?section=
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import BottomSheet from '../ui/BottomSheet.vue'
import AppIcon from '../ui/AppIcon.vue'
import AppBadge from '../ui/AppBadge.vue'
import { catalogApi } from '@/api'
import type { Source } from '@/types/contract'

defineProps<{ open: boolean; sources: Source[] }>()
defineEmits<{ close: [] }>()
const { t } = useI18n()

const expanded = ref<string | null>(null)
const bodies = reactive<Record<string, { loading: boolean; text: string | null; failed: boolean }>>({})

const key = (s: Source) => `${s.docId}#${s.section}`
function kind(s: Source): 'guide' | 'faq' | 'policy' {
  if (s.docId.startsWith('GUIDE')) return 'guide'
  if (s.docId.includes('FAQ')) return 'faq'
  return 'policy'
}
async function loadOriginal(s: Source) {
  const k = key(s)
  bodies[k] = { loading: true, text: null, failed: false }
  try {
    const doc = (await catalogApi.doc(s.docId, s.section)) as { body?: string }
    bodies[k] = { loading: false, text: doc.body ?? '', failed: false }
  } catch {
    bodies[k] = { loading: false, text: null, failed: true }
  }
}
</script>

<template>
  <BottomSheet :open="open" :title="t('chat.evidence.title', { n: sources.length })" @close="$emit('close')">
    <p class="intro t-body-14">{{ t('chat.evidence.intro') }}</p>
    <ul class="list">
      <li v-for="s in sources" :key="key(s)" class="doc" :class="{ 'doc--open': expanded === key(s) }">
        <button type="button" class="doc__head" :aria-expanded="expanded === key(s)" @click="expanded = expanded === key(s) ? null : key(s)">
          <AppIcon name="file-text" :size="20" class="doc__icon" />
          <span class="doc__title">
            <span class="t-body-14-sb">{{ s.title }}</span>
            <span class="t-caption-12 muted">§ {{ s.section }}</span>
          </span>
          <AppBadge tag>{{ t(`chat.evidence.kind.${kind(s)}`) }}</AppBadge>
          <AppIcon name="chevron-down" :size="18" class="chev" />
        </button>
        <div v-if="expanded === key(s)" class="doc__body">
          <p class="t-caption-12-sb section">§ {{ s.section }}</p>
          <blockquote class="snippet t-body-14">{{ bodies[key(s)]?.text ?? s.snippet }}</blockquote>
          <div class="doc__foot t-caption-12">
            <span class="muted">{{ s.uri }}</span>
            <button v-if="!bodies[key(s)]?.text" type="button" class="link" :disabled="bodies[key(s)]?.loading" @click="loadOriginal(s)">
              {{ bodies[key(s)]?.failed ? t('common.retry') : t('chat.evidence.original') }}
            </button>
          </div>
        </div>
      </li>
    </ul>
    <p class="disclaimer t-caption-12">
      <AppIcon name="info" :size="14" />
      {{ t('chat.evidence.disclaimer') }}
    </p>
  </BottomSheet>
</template>

<style scoped>
.intro { color: var(--text-secondary); margin-bottom: var(--space-16); }
.list { display: flex; flex-direction: column; gap: var(--space-12); margin: 0; padding: 0; list-style: none; }
.doc { border: 1px solid var(--border-default); border-radius: var(--radius-md); }
.doc--open { border-color: var(--brand-border); }
.doc__head { display: flex; align-items: center; gap: var(--space-8); width: 100%; padding: var(--space-12) var(--space-16); border: 0; background: none; text-align: left; }
.doc__icon { color: var(--icon-default); }
.doc--open .doc__icon { color: var(--brand-primary); }
.doc__title { display: flex; flex: 1; flex-direction: column; min-width: 0; }
.chev { color: var(--icon-subtle); }
.doc--open .chev { transform: rotate(180deg); }
.muted { color: var(--text-tertiary); }
.doc__body { display: flex; flex-direction: column; gap: var(--space-8); padding: 0 var(--space-16) var(--space-16); }
.section { color: var(--text-brand); }
.snippet { margin: 0; padding: var(--space-12); border-radius: var(--radius-sm); background: var(--bg-subtle); white-space: pre-wrap; }
.doc__foot { display: flex; justify-content: space-between; gap: var(--space-8); }
.link { padding: 0; border: 0; background: none; color: var(--text-brand); font-weight: 600; }
.disclaimer { display: flex; gap: var(--space-6); margin-top: var(--space-16); color: var(--text-tertiary); }
</style>
