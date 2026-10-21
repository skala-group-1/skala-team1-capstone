/** 상담사 통역 채팅 (C4 HUMAN 모드 / S1 문의함 / S2 통역 채팅). 실시간은 STOMP, 토픽 본문 {type, data} (13-2) */
import { defineStore } from 'pinia'
import type { StompSubscription } from '@stomp/stompjs'
import {
  consultationApi,
  counselorApi,
  sendConsultationMessage,
  subscribeConsultation,
  whenStompConnected,
  isStompConnected,
  safeUnsubscribe,
  http,
} from '@/api'
import type { ChatMessage, Consultation, ConsultationStatus, ConsultationTopicEvent, Locale } from '@/types/contract'

export const useConsultationStore = defineStore('consultation', {
  state: () => ({
    current: null as Consultation | null,
    messages: [] as ChatMessage[],
    /** 상담사 문의함 (탭: 대기/진행/종료) */
    inbox: [] as Consultation[],
    sub: null as StompSubscription | null,
    cancelWait: null as (() => void) | null,
    connected: false,
  }),
  actions: {
    async open(id: number) {
      this.close()
      this.current = await consultationApi.get(id)
      this.messages = await consultationApi.messages(id)
      // 연결될 때마다(재연결 포함) 상담방을 다시 구독. 끊기면 connected=false → "재연결 중" 표시
      this.cancelWait = whenStompConnected(
        () => {
          this.connected = true
          this.sub = subscribeConsultation(id, (e) => this.applyEvent(e))
          // 끊긴 동안 놓친 메시지 채우기 (13-2 afterId)
          void this.refetch()
        },
        () => {
          this.connected = false
          this.sub = null
        },
      )
    },
    close() {
      this.cancelWait?.()
      this.cancelWait = null
      safeUnsubscribe(this.sub)
      this.sub = null
      this.connected = false
      this.current = null
      this.messages = []
    },
    async refetch() {
      if (!this.current) return
      const last = this.messages.filter((m) => m.id > 0).at(-1)
      const more = await http
        .get<ChatMessage[]>(`/consultations/${this.current.id}/messages`, { params: { afterId: last?.id } })
        .then((r) => r.data)
        .catch(() => [] as ChatMessage[])
      for (const m of more) this.upsert(m)
    },
    /** 낙관적 표시(PENDING, id<0) 후 MESSAGE_CREATED 의 clientMsgId 로 교체. STOMP 가 끊겼으면 REST 폴백 */
    async send(text: string, myRole: 'CUSTOMER' | 'COUNSELOR', myLang: Locale) {
      if (!this.current) return
      const clientMsgId = crypto.randomUUID()
      this.messages.push({
        id: -Date.now(),
        consultationId: this.current.id,
        senderRole: myRole,
        senderId: null,
        originalText: text,
        originalLang: myLang,
        translatedText: null,
        translatedLang: null,
        translationStatus: 'PENDING',
        flags: [],
        clientMsgId,
        createdAt: new Date().toISOString(),
      })
      if (isStompConnected()) sendConsultationMessage(this.current.id, { text, clientMsgId })
      else {
        const m = await http.post<ChatMessage>(`/consultations/${this.current.id}/messages`, { text, clientMsgId }).then((r) => r.data)
        this.upsert(m)
      }
    },
    upsert(m: ChatMessage) {
      const i = this.messages.findIndex((x) => x.id === m.id || (m.clientMsgId && x.clientMsgId === m.clientMsgId))
      if (i >= 0) this.messages[i] = m
      else this.messages.push(m)
    },
    applyEvent(e: ConsultationTopicEvent) {
      if (e.type === 'CONSULTATION_STATUS') {
        if (this.current) {
          this.current.status = e.data.status
          this.current.counselorId = e.data.counselorId
        }
        return
      }
      this.upsert(e.data)
    },
    async retryTranslation(msg: ChatMessage) {
      if (!this.current || msg.id < 0) return
      await consultationApi.retryTranslation(this.current.id, msg.id)
      this.upsert({ ...msg, translationStatus: 'PENDING' })
    },
    // ─── 상담사 ───
    async loadInbox(status?: ConsultationStatus) {
      this.inbox = await counselorApi.inbox(status)
    },
    async accept(id: number) {
      this.current = await counselorApi.accept(id)
    },
    async finish(id: number) {
      this.current = await counselorApi.close(id)
    },
    /** 고객 종료: 응답의 CLOSED 상태로 바꾸면 ChatView 가 병원 대화(AI)로 되돌린다 */
    async endByCustomer() {
      if (!this.current) return
      this.current = await consultationApi.close(this.current.id)
    },
  },
})
