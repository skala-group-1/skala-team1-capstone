<script setup lang="ts">
// 04 ② Empty State: 56 원형 아이콘 + 제목(Title 18) + 설명(Body 14) + (선택) 버튼. 0건 · 403 · 서버 오류 공용
import AppIcon, { type IconName } from './AppIcon.vue'

withDefaults(defineProps<{ icon?: IconName; title: string; description?: string; tone?: 'default' | 'danger' }>(), {
  icon: 'info',
  tone: 'default',
})
</script>

<template>
  <div class="empty" :class="`empty--${tone}`">
    <span class="empty__icon"><AppIcon :name="icon" /></span>
    <p class="t-title-18">{{ title }}</p>
    <p v-if="description" class="empty__desc t-body-14">{{ description }}</p>
    <div v-if="$slots.default" class="empty__actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-12);
  padding: var(--space-32) var(--space-24);
  text-align: center;
}
.empty__icon {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--bg-muted);
  color: var(--icon-default);
}
.empty--danger .empty__icon { background: var(--status-danger-bg); color: var(--status-danger); }
.empty__desc { color: var(--text-secondary); white-space: pre-line; }
.empty__actions { display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-8); }
</style>
