/** 인앱 알림 (C10). 목록은 REST, 실시간은 STOMP /user/queue/notifications */
import { defineStore } from 'pinia'
import type { StompSubscription } from '@stomp/stompjs'
import { notificationApi, subscribeNotifications } from '@/api'
import type { Notification } from '@/types/contract'

export const useNotificationStore = defineStore('notification', {
  state: () => ({
    items: [] as Notification[],
    sub: null as StompSubscription | null,
  }),
  getters: {
    unread: (s) => s.items.filter((n) => !n.readAt).length,
  },
  actions: {
    async load() {
      const page = await notificationApi.list()
      this.items = page.items
    },
    listen() {
      // TODO(fe): STOMP 연결 완료(onConnect) 이후에 호출되도록 연결 상태와 묶기
      this.sub?.unsubscribe()
      this.sub = subscribeNotifications((n) => this.items.unshift(n))
    },
    async markRead(id: number) {
      await notificationApi.markRead(id)
      const n = this.items.find((x) => x.id === id)
      if (n) n.readAt = new Date().toISOString()
    },
    // TODO(fe): type 별 이동 (RESERVATION_* → /reservations, CONSULTATION_* → 상담 화면) + 문구 i18n
  },
})
