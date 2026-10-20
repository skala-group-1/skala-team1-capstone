<script setup lang="ts">
// 04 ② Banner: Offline(경고) · Reconnecting(정보, SSE·STOMP 재연결) · Error. 앱 바 바로 아래
import AppIcon from './AppIcon.vue'

defineProps<{ type: 'offline' | 'reconnecting' | 'error' }>()
</script>

<template>
  <div class="banner t-caption-13" :class="`banner--${type}`" role="status">
    <AppIcon :name="type === 'reconnecting' ? 'refresh-cw' : 'alert-triangle'" :size="16" />
    <span><slot /></span>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: 10px var(--space-16);
}
.banner--offline { background: var(--status-warning-bg); color: var(--status-warning); }
.banner--reconnecting { background: var(--status-info-bg); color: var(--status-info); }
.banner--error { background: var(--status-danger-bg); color: var(--status-danger); }
.banner--reconnecting .icon { animation: spin 1.2s linear infinite; }
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
