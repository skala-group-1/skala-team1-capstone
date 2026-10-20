<script setup lang="ts">
// C4-3 상담 요청 요약: AI 가 고객과의 대화를 요약한 카드. 고객은 수정하지 않음 (D-33, editable 없음)
// collapsible: 상담사 대기 중·연결됨 화면 상단의 접힌 요약 ("상담 요청 요약 · 질문 3개")
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '../ui/AppIcon.vue'

const props = defineProps<{
  rows: { label: string; value: string }[]
  questions: string[]
  collapsible?: boolean
}>()
const { t } = useI18n()
const open = ref(!props.collapsible)
</script>

<template>
  <section class="card" :class="{ 'card--collapsed': !open }">
    <button v-if="collapsible" type="button" class="head head--toggle" :aria-expanded="open" @click="open = !open">
      <AppIcon name="file-text" :size="20" class="brand" />
      <span class="head__text">
        <!-- 잠시 숨김: 「대화에서 나온 질문」 — 다시 쓰려면 아래 줄로 되돌리기
        <span class="t-body-14-sb">{{ t('chat.summary.titleCount', { n: questions.length }) }}</span>
        -->
        <span class="t-body-14-sb">{{ t('chat.summary.title') }}</span>
        <span v-if="!open" class="t-caption-12 muted line">{{ rows.map((r) => r.value).join(' · ') }}</span>
      </span>
      <AppIcon name="chevron-down" :size="18" class="chev" />
    </button>
    <header v-else class="head">
      <AppIcon name="file-text" :size="20" class="brand" />
      <h3 class="t-body-16-sb">{{ t('chat.summary.title') }}</h3>
    </header>

    <template v-if="open">
      <dl class="rows">
        <div v-for="row in rows" :key="row.label" class="row">
          <dt class="t-caption-13">{{ row.label }}</dt>
          <dd class="t-body-14-sb">{{ row.value }}</dd>
        </div>
      </dl>
      <!-- 잠시 숨김: 「대화에서 나온 질문」
      <div v-if="questions.length" class="questions">
        <p class="t-caption-12-sb muted">{{ t('chat.summary.questions') }}</p>
        <p v-for="q in questions" :key="q" class="question t-body-14">{{ q }}</p>
      </div>
      -->
    </template>
  </section>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  padding: 14px var(--space-16);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
}
.head { display: flex; align-items: center; gap: var(--space-8); }
.head--toggle { width: 100%; padding: 0; border: 0; background: none; text-align: left; }
.head__text { display: flex; flex: 1; flex-direction: column; min-width: 0; }
.line { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chev { color: var(--icon-subtle); transition: transform 0.15s; }
.head--toggle[aria-expanded='true'] .chev { transform: rotate(180deg); }
.brand { color: var(--brand-primary); }
.muted { color: var(--text-tertiary); }
/* 라벨 열은 가장 긴 라벨 폭 (영어 'Procedure' 등) */
.rows { display: grid; grid-template-columns: auto 1fr; gap: var(--space-6) var(--space-12); margin: 0; }
.row { display: contents; }
.row dt { min-width: 44px; color: var(--text-tertiary); }
.row dd { margin: 0; }
.questions { display: flex; flex-direction: column; gap: var(--space-6); }
.question { padding: var(--space-8) var(--space-12); border-radius: var(--radius-sm); background: var(--bg-subtle); }
</style>
