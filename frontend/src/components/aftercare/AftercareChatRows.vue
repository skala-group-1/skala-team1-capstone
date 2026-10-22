<script setup lang="ts">
// 대화 목록(/chats)의 "사후관리 N" 행들. 불러온 방 ID 는 부모가 병원 대화 목록에서 빼도록 알린다
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { aftercareApi, isAftercareClosed, type AftercareConversation } from '@/api/aftercare'
import { aftercareDayLabel } from '@/composables/useAftercareRoom'
import { seoulDate } from '@/utils/format'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const emit = defineEmits<{ loaded: [ids: string[]] }>()
const { t } = useI18n()
const rooms = ref<AftercareConversation[]>([])

const md = (iso: string) => seoulDate(iso).slice(5).replace('-', '/')
function day(room: AftercareConversation) {
  return isAftercareClosed(room) ? t('aftercare.closedBadge') : aftercareDayLabel(t, room.daysFromProcedure)
}

onMounted(async () => {
  rooms.value = await aftercareApi.mine().catch(() => [])
  emit('loaded', rooms.value.map((r) => r.conversationId))
})
</script>

<template>
  <template v-if="rooms.length">
    <hr class="divider" />
    <h2 class="section t-caption-13">{{ t('aftercare.section', { n: rooms.length }) }}</h2>
    <template v-for="(c, i) in rooms" :key="c.conversationId">
      <hr v-if="i" class="divider" />
      <RouterLink :to="`/chat/${c.conversationId}`" class="row">
        <span class="avatar"><AppIcon name="file-text" :size="22" /></span>
        <span class="text">
          <span class="line1">
            <span class="name t-body-16-sb">{{ c.hospital.name }}</span>
            <span class="date t-caption-12">{{ md(c.createdAt) }}</span>
          </span>
          <span class="sub t-body-14">{{ c.procedureName ?? c.procedureCode }} · {{ day(c) }}</span>
          <span class="badges">
            <AppBadge tone="success" icon="file-text">{{ t('aftercare.badge') }}</AppBadge>
            <AppBadge v-if="c.mode === 'HUMAN'" tone="info" icon="headphones">{{ t('chat.mode.human') }}</AppBadge>
          </span>
        </span>
      </RouterLink>
    </template>
  </template>
</template>

<style scoped>
/* ConversationsView 행과 같은 모양 */
.row { display: flex; align-items: center; gap: var(--space-12); padding: var(--space-12) var(--space-16); color: var(--text-primary); text-decoration: none; }
.avatar { display: grid; flex: none; place-items: center; width: 44px; height: 44px; border-radius: 22px; background: var(--status-neutral-bg); color: var(--chat-agent-accent); }
.text { display: flex; flex: 1; flex-direction: column; gap: var(--space-4); min-width: 0; }
.line1 { display: flex; align-items: center; gap: var(--space-8); }
.name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.date { flex: none; color: var(--text-tertiary); }
.sub { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-tertiary); }
.badges { display: flex; gap: var(--space-6); }
.divider { height: 1px; margin: 0 var(--space-16); border: 0; background: var(--border-default); }
.section { padding: var(--space-16) var(--space-16) var(--space-4); color: var(--text-secondary); }
</style>
