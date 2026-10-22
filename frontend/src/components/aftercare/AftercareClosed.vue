<script setup lang="ts">
// 반려·취소·만료된 예약의 사후관리 방: 입력창 대신 안내 종료 문구 (기록은 위에 그대로 보인다)
import { useI18n } from 'vue-i18n'
import AppIcon from '@/components/ui/AppIcon.vue'

const { t } = useI18n()
</script>

<template>
  <footer class="closed t-caption-13">
    <AppIcon name="info" :size="16" />
    <span>{{ t('aftercare.closed') }}</span>
  </footer>
</template>

<style scoped>
.closed { display: flex; flex: none; align-items: center; gap: var(--space-8); padding: var(--space-16); padding-bottom: calc(var(--space-16) + env(safe-area-inset-bottom)); border-top: 1px solid var(--border-default); background: var(--bg-muted); color: var(--text-secondary); }
</style>
