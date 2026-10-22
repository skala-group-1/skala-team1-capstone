// 지금 보고 있는 대화가 사후관리 방이면 그 정보 (아니면 null). 대화가 바뀔 때마다 다시 확인한다.
// 방에 들어오면 그날 안내를 요청하고(backend 가 하루 한 번만 만든다), 새 안내 작업이 생기면 그 스트림을 이어 받는다.
import { ref, watch, type Ref } from 'vue'
import { aftercareApi, isAftercareClosed, type AftercareConversation } from '@/api/aftercare'
import { useConversationStore } from '@/stores/conversation'
import type { Uuid } from '@/types/contract'

export function useAftercareRoom(conversationId: () => Uuid | null): Ref<AftercareConversation | null> {
  const room = ref<AftercareConversation | null>(null)
  const conv = useConversationStore()
  watch(
    conversationId,
    async (id) => {
      room.value = null
      if (!id) return
      let found = (await aftercareApi.mine().catch(() => [])).find((c) => c.conversationId === id) ?? null
      if (found && !isAftercareClosed(found) && found.mode === 'AFTERCARE') {
        found = await aftercareApi.open(found.reservationId).catch(() => found)
      }
      if (conversationId() !== id) return
      room.value = found
      const task = found?.activeTaskId
      if (task && conv.conversationId === id && conv.taskId !== task && !conv.pendingAction) {
        await conv.restoreActiveTask(task)
      }
    },
    { immediate: true },
  )
  return room
}

/** 헤더·목록용 날짜 표시: 시술 D-n / 내일 시술 / 시술 당일 / 시술 후 n일째 */
export function aftercareDayLabel(t: (key: string, values?: Record<string, unknown>) => string, days: number): string {
  if (days === 0) return t('aftercare.dayZero')
  if (days === -1) return t('aftercare.tomorrow')
  return days < 0 ? t('aftercare.before', { n: -days }) : t('aftercare.day', { n: days })
}
