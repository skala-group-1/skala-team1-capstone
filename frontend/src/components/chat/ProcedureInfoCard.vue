<script setup lang="ts">
// Figma 02 C4-T Procedure Info Card. 시간·가격은 도구 결과(DB)에서만 — 효과·적합성 표현 금지
import { useI18n } from 'vue-i18n'
import { fmtKrw } from '@/utils/format'
import type { ProcedureInfo } from '@/types/contract'

defineProps<{ info: ProcedureInfo }>()
const { t } = useI18n()
</script>

<template>
  <article class="proc">
    <div class="proc__title">
      <h3 class="t-body-16-sb">{{ info.name }}</h3>
      <span v-if="info.concerns.length" class="proc__tag t-caption-12-sb">
        {{ info.concerns.map((c) => t(`chat.concern.items.${c}`)).join(' · ') }}
      </span>
    </div>
    <p class="proc__desc t-caption-13">{{ info.description }}</p>
    <div class="proc__facts t-caption-12">
      <p>
        {{
          t('chat.procInfo.time', {
            min: info.durationMin,
            downtime: info.downtimeDays ? t('chat.procInfo.downtime', { n: info.downtimeDays }) : t('chat.procInfo.noDowntime'),
          })
        }}
      </p>
      <p v-if="info.minPriceKrw != null">
        {{ t('chat.procInfo.price', { min: fmtKrw(info.minPriceKrw), max: fmtKrw(info.maxPriceKrw ?? info.minPriceKrw) }) }}
      </p>
    </div>
  </article>
</template>

<style scoped>
.proc { display: flex; flex-direction: column; gap: var(--space-8); width: 280px; max-width: 100%; padding: 14px; border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--surface-card); }
.proc__title { display: flex; align-items: center; gap: var(--space-6); min-width: 0; }
.proc__tag { padding: 2px var(--space-8); border-radius: var(--radius-full); background: var(--brand-subtle); color: var(--brand-text); white-space: nowrap; }
.proc__desc { color: var(--text-secondary); }
.proc__facts { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-8) 10px; border-radius: var(--radius-sm); background: var(--bg-subtle); color: var(--text-primary); }
</style>
