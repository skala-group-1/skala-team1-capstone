<script setup lang="ts">
// 04 ② Toast (Success · Error · Info): bg/inverse, 반경 12, 그림자. 셸에 하나만 둔다 → showToast() 로 띄움
import { computed } from 'vue'
import AppIcon, { type IconName } from './AppIcon.vue'
import { hideToast, toastState } from '@/composables/useToast'

defineProps<{ placement: 'customer' | 'staff' }>()

const ICON: Record<string, IconName> = { success: 'check', error: 'alert-triangle', info: 'info' }
const toast = computed(() => toastState.current)

function runAction() {
  toast.value?.onAction?.()
  hideToast()
}
</script>

<template>
  <Transition name="toast">
    <div v-if="toast" :key="toast.id" class="toast" :class="`toast--${placement}`" role="status" aria-live="polite">
      <AppIcon :name="ICON[toast.type] ?? 'info'" :size="18" />
      <p class="toast__msg t-body-14">{{ toast.message }}</p>
      <button v-if="toast.actionLabel" type="button" class="toast__action t-caption-13" @click="runAction">
        {{ toast.actionLabel }}
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.toast {
  position: fixed;
  z-index: 60;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: var(--space-12) var(--space-16);
  border-radius: var(--radius-md);
  background: var(--bg-inverse);
  color: var(--text-inverse);
  box-shadow: var(--shadow-toast);
}
.toast--customer {
  left: 50%;
  bottom: calc(var(--tab-bar-h) + var(--space-16) + env(safe-area-inset-bottom));
  width: calc(min(100vw, var(--app-width)) - 32px);
  transform: translateX(-50%);
}
.toast--staff {
  right: var(--space-24);
  bottom: var(--space-24);
  max-width: 420px;
}
.toast__msg { flex: 1; }
.toast__action {
  border: 0;
  background: none;
  color: var(--brand-subtle-strong);
}
.toast-enter-active,
.toast-leave-active { transition: opacity 0.2s, translate 0.2s; }
.toast-enter-from,
.toast-leave-to { opacity: 0; translate: 0 8px; }
</style>
