<script setup lang="ts">
// 사후관리 채팅 상단: 시술명 · 시술 일시 · 시술 후 N일째
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AftercareConversation } from '@/api/aftercare'
import { daysSinceProcedure } from '@/composables/useAftercareRoom'
import { fmtDateTime } from '@/utils/format'
import AppIcon from '@/components/ui/AppIcon.vue'

const props = defineProps<{ room: AftercareConversation }>()
const { t } = useI18n()
const day = computed(() => {
  const n = daysSinceProcedure(props.room.startAt)
  if (n == null) return t('aftercare.before')
  return n === 0 ? t('aftercare.dayZero') : t('aftercare.day', { n })
})
</script>

<template>
  <div class="aftercare-bar">
    <AppIcon name="file-text" :size="16" />
    <strong class="t-caption-13">{{ room.procedureName ?? room.procedureCode }}</strong>
    <span class="t-caption-12 secondary">{{ fmtDateTime(room.startAt) }} · {{ day }}</span>
  </div>
</template>

<style scoped>
.aftercare-bar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-6); padding: var(--space-8) var(--space-16); border-bottom: 1px solid var(--border-default); color: var(--chat-agent-accent); }
.secondary { color: var(--text-secondary); }
</style>
