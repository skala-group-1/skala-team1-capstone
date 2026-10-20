<script setup lang="ts">
// 04 ② Dialog: 폭 320(데스크톱 400), 반경 20, 스크림 45%. 바깥 탭으로 닫지 않음 (세션 만료 등)
defineProps<{ open: boolean; title: string; body?: string; wide?: boolean }>()
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="scrim">
      <section class="dialog" :class="{ 'dialog--wide': wide }" role="alertdialog" aria-modal="true" :aria-label="title">
        <div class="dialog__text">
          <h2 class="t-title-18">{{ title }}</h2>
          <p v-if="body" class="t-body-14 dialog__body">{{ body }}</p>
          <slot />
        </div>
        <div class="dialog__actions"><slot name="actions" /></div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.scrim {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  padding: var(--space-16);
  background: rgb(0 0 0 / 45%);
}
.dialog {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
  width: 100%;
  max-width: 320px;
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
