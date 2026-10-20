<script setup lang="ts">
// Figma Top App Bar: Default(뒤로 + 제목) 56 · Home(로고 + 알림) 56 · Chat(뒤로 + 제목 + 모드 배지 + 정보) 64
import { useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'

const props = withDefaults(defineProps<{ title?: string; back?: boolean | string; chat?: boolean }>(), { back: false })
const router = useRouter()

function goBack() {
  if (typeof props.back === 'string') void router.push(props.back)
  else if (window.history.length > 1) router.back()
  else void router.push('/')
}
</script>

<template>
  <header class="bar" :class="{ 'bar--chat': chat }">
    <button v-if="back" type="button" class="bar__icon" :aria-label="$t('common.back')" @click="goBack">
      <AppIcon name="chevron-left" />
    </button>
    <slot name="left" />
    <div class="bar__title">
      <slot name="title">
        <h1 class="t-body-16-sb ellipsis">{{ title }}</h1>
      </slot>
      <slot name="subtitle" />
    </div>
    <div class="bar__right" :class="{ 'bar__right--spacer': !chat && !$slots.right }"><slot name="right" /></div>
  </header>
</template>

<style scoped>
.bar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: var(--space-8);
  height: var(--app-bar-h);
  padding: 0 var(--space-12);
  background: var(--bg-default);
}
.bar--chat {
  height: 64px;
  border-bottom: 1px solid var(--border-default);
}
.bar__icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  margin: 0 -4px;
  border: 0;
  border-radius: var(--radius-sm);
  background: none;
  color: var(--icon-default);
}
.bar__title {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}
/* Default 타입은 제목 가운데 정렬 (오른쪽 24 spacer 로 균형) */
.bar:not(.bar--chat) .bar__title { align-items: center; text-align: center; }
.bar__right--spacer { width: 24px; }
.bar__right {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  color: var(--icon-default);
}
.ellipsis {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
