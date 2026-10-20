<script setup lang="ts">
// Figma Button: Variant(Primary·Secondary·Outline·Ghost·Danger) × Size(L 52·M 44·S 36) × State(Default·Disabled) + Loading(04 ②)
// 로딩 중에는 다시 누를 수 없음 (04 ⑤ "버튼 로딩")
import AppIcon, { type IconName } from './AppIcon.vue'

withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
    size?: 'l' | 'm' | 's'
    type?: 'button' | 'submit'
    disabled?: boolean
    loading?: boolean
    block?: boolean
    icon?: IconName
  }>(),
  { variant: 'primary', size: 'm', type: 'button' },
)
</script>

<template>
  <button
    :type="type"
    class="btn"
    :class="[`btn--${variant}`, `btn--${size}`, { 'btn--block': block, 'btn--loading': loading }]"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <AppIcon v-if="icon && !loading" :name="icon" :size="size === 's' ? 16 : 18" />
    <span class="btn__label"><slot /></span>
    <span v-if="loading" class="btn__spinner" aria-hidden="true" />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-6);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  white-space: nowrap;
  transition: background-color 0.15s;
}
.btn--l { height: 52px; padding: 0 var(--space-20); font: 600 16px/24px var(--font-sans); }
.btn--m { height: 44px; padding: 0 var(--space-16); font: 600 14px/20px var(--font-sans); }
.btn--s { height: 36px; padding: 0 var(--space-12); font: 500 13px/18px var(--font-sans); border-radius: var(--radius-sm); }
.btn--block { width: 100%; }

.btn--primary { background: var(--brand-primary); color: var(--text-inverse); }
.btn--primary:hover:not(:disabled) { background: var(--brand-primary-pressed); }
.btn--secondary { background: var(--brand-subtle); color: var(--brand-text); }
.btn--secondary:hover:not(:disabled) { background: var(--brand-subtle-strong); }
.btn--outline { background: var(--bg-default); border-color: var(--border-strong); color: var(--text-primary); }
.btn--outline:hover:not(:disabled) { background: var(--bg-subtle); }
.btn--ghost { background: transparent; color: var(--text-secondary); }
.btn--ghost:hover:not(:disabled) { background: var(--bg-muted); }
.btn--danger { background: var(--status-danger-bg); color: var(--status-danger); }

.btn:disabled:not(.btn--loading) {
  background: var(--bg-muted);
  border-color: transparent;
  color: var(--text-disabled);
  cursor: not-allowed;
}
.btn--loading { cursor: progress; }

.btn__spinner {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
