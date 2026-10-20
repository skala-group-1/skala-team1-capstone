<script setup lang="ts">
// Figma Chip: Filter(On/Off) · Condition(키+값+▼, C4 조건 칩) · Evidence(근거 n, C4-1) · Progress(진행 칩, SSE TOOL_START)
import AppIcon from './AppIcon.vue'

withDefaults(
  defineProps<{
    type?: 'filter' | 'condition' | 'evidence' | 'progress'
    selected?: boolean
    /** condition 칩의 앞쪽 이름 (예: 지역) */
    label?: string
    disabled?: boolean
  }>(),
  { type: 'filter' },
)
</script>

<template>
  <span v-if="type === 'progress'" class="chip chip--progress t-caption-12-sb" role="status">
    <span class="chip__dot" aria-hidden="true" />
    <slot />
  </span>
  <button
    v-else
    type="button"
    class="chip"
    :class="[`chip--${type}`, { 'chip--on': selected }]"
    :aria-pressed="type === 'filter' ? !!selected : undefined"
    :disabled="disabled"
  >
    <AppIcon v-if="type === 'filter' && selected" name="check" :size="16" />
    <AppIcon v-if="type === 'evidence'" name="file-text" :size="14" />
    <span v-if="type === 'condition' && label" class="chip__key t-caption-12">{{ label }}</span>
    <span class="chip__label"><slot /></span>
    <AppIcon v-if="type === 'condition'" name="chevron-down" :size="14" />
  </button>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  flex: none;
  white-space: nowrap;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
  background: var(--bg-default);
}
.chip:disabled { opacity: 0.5; cursor: default; }

.chip--filter { height: 36px; padding: 0 14px; font: 400 14px/20px var(--font-sans); color: var(--text-secondary); }
.chip--filter.chip--on { background: var(--brand-subtle); border-color: var(--brand-border); color: var(--brand-text); font-weight: 600; }

.chip--condition { height: 30px; padding: 0 10px; font: 600 12px/16px var(--font-sans); color: var(--text-primary); }
.chip--condition .icon { color: var(--icon-default); }
.chip__key { color: var(--text-tertiary); }

.chip--evidence {
  height: 26px;
  padding: 0 var(--space-8);
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  font: 600 12px/16px var(--font-sans);
  color: var(--text-secondary);
}

.chip--progress {
  height: 28px;
  padding: 0 10px;
  gap: var(--space-6);
  border: 0;
  background: var(--brand-subtle);
  color: var(--brand-text);
}
.chip__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand-primary);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  50% { opacity: 0.3; }
}
</style>
