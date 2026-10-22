<script setup lang="ts">
// 04 ② Dialog: 폭 320(데스크톱 400), 반경 20, 스크림 45%. 바깥 탭으로 닫지 않음 (세션 만료 등)
// 네이티브 <dialog> + showModal(): ESC(→ close 이벤트)·포커스 가두기·뒤 화면 비활성·닫힌 뒤 원래 버튼으로 포커스 복귀를 브라우저가 처리
import { ref, watch } from 'vue'

const props = defineProps<{ open: boolean; title: string; body?: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const el = ref<HTMLDialogElement | null>(null)
watch([() => props.open, el], ([open, d]) => {
  if (!d) return
  if (open && !d.open) d.showModal()
  else if (!open && d.open) d.close()
})
</script>

<template>
  <dialog
    ref="el"
    class="dialog"
    :class="{ 'dialog--wide': wide }"
    role="alertdialog"
    :aria-label="title"
    @cancel.prevent="emit('close')"
  >
    <div class="dialog__text">
      <h2 class="t-title-18">{{ title }}</h2>
      <p v-if="body" class="t-body-14 dialog__body">{{ body }}</p>
      <slot />
    </div>
    <div class="dialog__actions"><slot name="actions" /></div>
  </dialog>
</template>

<style scoped>
.dialog::backdrop { background: rgb(0 0 0 / 45%); }
.dialog {
  width: calc(100% - 32px);
  max-width: 320px;
  border: 0;
  color: inherit;
}
/* UA 의 display:none(닫힘)을 덮지 않도록 열렸을 때만 flex */
.dialog[open] {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
  padding: var(--space-24);
  border-radius: var(--radius-xl);
  background: var(--surface-sheet);
  box-shadow: var(--shadow-dialog);
}
.dialog--wide { max-width: 560px; }
.dialog__text { display: flex; flex-direction: column; gap: var(--space-8); }
.dialog__body { color: var(--text-secondary); }
.dialog__actions { display: flex; gap: var(--space-8); }
.dialog__actions > * { flex: 1; }
</style>
