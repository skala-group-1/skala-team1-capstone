// 지금 보고 있는 대화가 사후관리 방이면 그 정보 (아니면 null). 대화가 바뀔 때마다 다시 확인한다
import { ref, watch, type Ref } from 'vue'
import { aftercareApi, type AftercareConversation } from '@/api/aftercare'
import type { Uuid } from '@/types/contract'

export function useAftercareRoom(conversationId: () => Uuid | null): Ref<AftercareConversation | null> {
  const room = ref<AftercareConversation | null>(null)
  watch(
    conversationId,
    async (id) => {
      room.value = null
      if (!id) return
      const found = (await aftercareApi.mine().catch(() => [])).find((c) => c.conversationId === id) ?? null
      if (conversationId() === id) room.value = found
    },
    { immediate: true },
  )
  return room
}

/** 시술 후 경과일 (시술일 = 0, 시술 전이면 null) — Asia/Seoul 날짜 기준 */
export function daysSinceProcedure(startAt: string, now = new Date()): number | null {
  const day = (d: Date) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(d)
  const diff = Math.round((Date.parse(day(now)) - Date.parse(day(new Date(startAt)))) / 86_400_000)
  return diff >= 0 ? diff : null
}
