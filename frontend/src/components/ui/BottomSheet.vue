<script setup lang="ts">
// Figma Bottom Sheet: 손잡이 + 제목/닫기 + 내용 + (선택) 하단 버튼. 위쪽 반경 20, 스크림 45% (04 ① 셀 수치)
// C4-1 근거 · C5-1 필터 · C8 예약 시트 · Edge ④ 대안 시간에서 사용
import { onBeforeUnmount, watch } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ open: boolean; title?: string }>()
const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
watch(
  () => props.open,
  (open) => {
    document.body.style.overflow = open ? 'hidden' : ''
    if (open) window.addEventListener('keydown', onKey)
    else window.removeEventListener('keydown', onKey)
  },
)
onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="open" class="scrim" @click.self="emit('close')">
        <section class="sheet" role="dialog" aria-modal="true" :aria-label="title">
          <div class="sheet__handle" aria-hidden="true" />
          <header v-if="title || $slots.header" class="sheet__header">
            <slot name="header">
              <h2 class="t-title-18">{{ title }}</h2>
            </slot>
            <button type="button" class="sheet__close" :aria-label="$t('common.close')" @click="emit('close')">
              <AppIcon name="x" />
            </button>
          </header>
          <div class="sheet__body"><slot /></div>
          <footer v-if="$slots.footer" class="sheet__footer"><slot name="footer" /></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.scrim {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgb(0 0 0 / 45%);
}
.sheet {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: var(--app-width);
  max-height: 90dvh;
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  background: var(--surface-sheet);
  box-shadow: var(--shadow-sheet);
}
.sheet__handle {
  width: 36px;
  height: 4px;
  margin: var(--space-8) auto;
  border-radius: 2px;
  background: var(--border-strong);
}
.sheet__header {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-8) var(--space-20);
}
.sheet__header > :first-child { flex: 1; }
.sheet__close {
  display: grid;
  place-items: center;
  border: 0;
  background: none;
  color: var(--icon-default);
}
.sheet__body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-8) var(--space-20) var(--space-20);
}
.sheet__footer {
  display: flex;
  gap: var(--space-8);
  padding: var(--space-12) var(--space-20) calc(var(--space-12) + env(safe-area-inset-bottom));
  border-top: 1px solid var(--border-default);
}
.sheet-enter-active,
.sheet-leave-active { transition: opacity 0.2s; }
.sheet-enter-active .sheet,
.sheet-leave-active .sheet { transition: transform 0.2s; }
.sheet-enter-from,
.sheet-leave-to { opacity: 0; }
.sheet-enter-from .sheet,
.sheet-leave-to .sheet { transform: translateY(100%); }
</style>
