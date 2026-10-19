// 「API·이벤트 명세」 2장 알림. 실시간은 STOMP /user/queue/notifications (stomp.ts)
import type { Notification, Page, PageRequest } from '@/types/contract'
import { http } from './http'

export const notificationApi = {
  // TODO(fe): 응답이 Page 인지 배열인지 backend BE-12 구현 시 확정
  list: (q: PageRequest = {}) => http.get<Page<Notification>>('/notifications', { params: q }).then((r) => r.data),
  // TODO(fe): 「API·이벤트 명세」에 "(+ /read)" 로만 적혀 있음 — 경로(POST /api/notifications/{id}/read 가정) BE-12 와 확정
  markRead: (id: number) => http.post<void>(`/notifications/${id}/read`).then(() => undefined),
}
