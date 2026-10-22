<script setup lang="ts">
// Figma Hospital Card: List(358, C5 탐색 · 비교 체크박스) · Compact(264, C4 결과 가로 스크롤 · "이 병원과 대화")
// 순위·추천 표시 없음 (D-01). 값이 null 이면 "확인 필요"
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from './ui/AppIcon.vue'
import AppBadge from './ui/AppBadge.vue'
import { fmtDateTime, fmtKrw } from '@/utils/format'
import type { HospitalCard } from '@/types/contract'

const props = defineProps<{
  card: HospitalCard
  variant?: 'list' | 'compact'
  procedureName?: string | null
  compareChecked?: boolean
  compareDisabled?: boolean
}>()
const emit = defineEmits<{ open: []; chat: []; compare: [] }>()
const { t } = useI18n()

/** 고객에게 의미 있는 외국어만 (한국어는 모든 병원 기본) */
const langs = computed(() => props.card.languages.filter((l) => l !== 'ko'))
</script>

<template>
  <!-- 카드 어디를 눌러도 상세로 (키보드는 제목 버튼). 비교 체크는 .stop -->
  <article class="card" :class="`card--${variant ?? 'list'}`" @click="emit('open')">
    <div class="top">
      <button type="button" class="title" @click.stop="emit('open')">
        <h3 class="t-body-16-sb">{{ card.name }}</h3>
        <p :class="variant === 'compact' ? 't-caption-12' : 't-caption-13'" class="meta">
          {{ t(`domain.area.${card.areaCode}`) }} · {{ t(`domain.category.${card.category}`) }}
        </p>
      </button>
      <label v-if="variant !== 'compact'" class="check hit t-body-14" @click.stop :class="{ 'check--disabled': compareDisabled && !compareChecked }">
        <input type="checkbox" :checked="compareChecked" :disabled="compareDisabled && !compareChecked" @change="emit('compare')" />
        <span class="box" aria-hidden="true"><AppIcon v-if="compareChecked" name="check" :size="14" /></span>
        {{ t('explore.compare') }}
      </label>
    </div>

    <p class="rating t-caption-13">
      <AppIcon name="star" :size="14" class="star" />
      <span>{{ card.rating?.toFixed(1) ?? '—' }}</span>
      <span class="muted">{{ t('domain.reviews', { n: card.reviewCount }) }}</span>
    </p>

    <div v-if="variant !== 'compact'" class="langs">
      <AppBadge v-for="l in langs" :key="l" tag>{{ t(`domain.lang.${l}`) }}</AppBadge>
      <AppBadge v-if="card.hasInterpreter" tag>{{ t('domain.interpreter') }}</AppBadge>
    </div>
    <hr v-if="variant !== 'compact'" class="divider" />

    <p class="price">
      <span v-if="procedureName" class="t-caption-13 secondary">{{ procedureName }}</span>
      <span v-if="card.minPriceKrw != null" class="t-body-16-sb">{{ t('domain.priceFrom', { price: fmtKrw(card.minPriceKrw) }) }}</span>
      <span v-else class="t-body-14-sb warn">{{ t('common.needsCheck') }}</span>
      <span v-if="card.minPriceKrw != null && !card.priceVerified" class="t-caption-11 muted">{{ t('domain.priceUnverified') }}</span>
    </p>
    <p class="slot t-caption-13">
      <AppIcon name="clock" :size="14" />
      <span v-if="card.earliestSlotAt">{{ t('domain.earliest', { at: fmtDateTime(card.earliestSlotAt) }) }}</span>
      <span v-else>{{ t('domain.noSlot') }}</span>
    </p>

    <template v-if="variant === 'compact'">
      <div class="langs">
        <AppBadge v-for="l in langs" :key="l" tag>{{ t(`domain.lang.${l}`) }}</AppBadge>
        <AppBadge v-if="card.hasInterpreter" tag>{{ t('domain.interpreter') }}</AppBadge>
      </div>
      <div class="actions">
        <slot name="actions" />
        <span class="spacer" />
        <button type="button" class="chat-btn t-caption-13" @click.stop="emit('chat')">{{ t('chat.talkToHospital') }}</button>
      </div>
    </template>
  </article>
</template>

<style scoped>
.card {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: var(--space-16);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
}
.card--compact { width: 264px; flex: none; gap: var(--space-8); padding: 14px; }
.top { display: flex; gap: var(--space-8); align-items: flex-start; }
.title { display: flex; flex: 1; flex-direction: column; gap: var(--space-2); min-width: 0; padding: 0; border: 0; background: none; text-align: left; }
.meta, .muted { color: var(--text-tertiary); }
.secondary { color: var(--text-secondary); }
.warn { color: var(--status-warning); }
.rating, .slot { display: flex; align-items: center; gap: var(--space-4); }
.star { color: var(--rating-star); fill: var(--rating-star); }
.slot { color: var(--text-secondary); }
.slot .icon { color: var(--icon-default); }
.langs { display: flex; flex-wrap: wrap; gap: var(--space-4); }
.divider { width: 100%; height: 1px; margin: 0; border: 0; background: var(--border-default); }
.price { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--space-6); }
.actions { display: flex; align-items: center; gap: var(--space-8); }
.spacer { flex: 1; }
.chat-btn {
  height: 36px;
  padding: 0 var(--space-12);
  border: 0;
  border-radius: var(--radius-sm);
  background: var(--brand-subtle);
  color: var(--brand-text);
}
.check { position: relative; display: flex; align-items: center; gap: var(--space-8); color: var(--text-primary); cursor: pointer; }
.check input { position: absolute; opacity: 0; width: 1px; height: 1px; }
.check--disabled { opacity: 0.4; cursor: not-allowed; }
.box {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border: 1.5px solid var(--border-strong);
  border-radius: var(--radius-xs);
  background: var(--bg-default);
  color: var(--text-inverse);
}
.check input:checked + .box { border-color: var(--brand-primary); background: var(--brand-primary); }
.check input:focus-visible + .box { outline: 2px solid var(--border-focus); outline-offset: 2px; }
</style>
