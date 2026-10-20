// 「API·이벤트 명세」 2장 알림. 실시간은 STOMP /user/queue/notifications (stomp.ts)
import type { Notification, Page, PageRequest } from '@/types/contract'
import { http } from './http'

export const notificationApi = {
  /** 13-2: Page 응답, 최신순 */
  list: (q: PageRequest & { unreadOnly?: boolean } = {}) => http.get<Page<Notification>>('/notifications', { params: q }).then((r) => r.data),
  markRead: (id: number) => http.post<void>(`/notifications/${id}/read`).then(() => undefined),
  readAll: () => http.post<void>('/notifications/read-all').then(() => undefined),
}
