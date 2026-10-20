/** 인앱 알림 (C10). 목록은 REST, 실시간은 STOMP /user/queue/notifications */
import { defineStore } from 'pinia'
import type { StompSubscription } from '@stomp/stompjs'
import { notificationApi, safeUnsubscribe, subscribeNotifications, whenStompConnected } from '@/api'
import type { Notification } from '@/types/contract'

export const useNotificationStore = defineStore('notification', {
  state: () => ({
    items: [] as Notification[],
    sub: null as StompSubscription | null,
    stopWait: null as (() => void) | null,
  }),
  getters: {
    unread: (s) => s.items.filter((n) => !n.readAt).length,
  },
  actions: {
    async load() {
      const page = await notificationApi.list({ size: 50 })
      this.items = page.items
    },
    /** 로그인 직후 auth 스토어가 1번 호출. 연결(재연결 포함)될 때마다 /user/queue/notifications 를 다시 구독 */
    listen() {
      this.stopListening()
      this.stopWait = whenStompConnected(
        () => {
          this.sub = subscribeNotifications((n) => {
            if (!this.items.some((x) => x.id === n.id)) this.items.unshift(n)
          })
          // 끊겨 있던 동안 온 알림은 목록을 다시 받아 채운다
          void this.load().catch(() => undefined)
        },
        () => {
          this.sub = null
        },
      )
    },
    stopListening() {
      this.stopWait?.()
      this.stopWait = null
      safeUnsubscribe(this.sub)
      this.sub = null
    },
    async markRead(id: number) {
      await notificationApi.markRead(id)
      const n = this.items.find((x) => x.id === id)
      if (n) n.readAt = new Date().toISOString()
    },
    async readAll() {
      await notificationApi.readAll()
      const now = new Date().toISOString()
      this.items.forEach((n) => (n.readAt ??= now))
    },
  },
})
