/**
 * 실시간 알림(STOMP /user/queue/notifications)이 오면 지금 보고 있는 목록을 다시 불러온다.
 * - 화면이 떠 있는 동안만 동작 (onBeforeUnmount 에서 정리)
 * - 알림이 몰려 와도 delay 동안 모아 1번만 호출
 * - 다시 불러오기 실패는 조용히 무시 (다음 알림·화면 진입 때 다시 받음)
 */
import { onBeforeUnmount, watch } from 'vue'
import { useNotificationStore } from '@/stores/notification'
import type { Notification, NotificationType } from '@/types/contract'

export function useNotificationRefresh(types: NotificationType[], refresh: (n: Notification) => unknown, delay = 500) {
  const store = useNotificationStore()
  let timer: ReturnType<typeof setTimeout> | undefined
  const stop = watch(
    () => store.latest,
    (n) => {
      if (!n || !types.includes(n.type)) return
      clearTimeout(timer)
      timer = setTimeout(() => {
        void Promise.resolve()
          .then(() => refresh(n))
          .catch(() => undefined)
      }, delay)
    },
  )
  onBeforeUnmount(() => {
    stop()
    clearTimeout(timer)
  })
}
