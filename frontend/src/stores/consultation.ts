/** 상담사 통역 채팅 (C4 HUMAN 모드 / S1 문의함 / S2 통역 채팅). 실시간은 STOMP */
import { defineStore } from 'pinia'
import type { StompSubscription } from '@stomp/stompjs'
import { consultationApi, counselorApi, sendConsultationMessage, subscribeConsultation } from '@/api'
import type { ChatMessage, Consultation, ConsultationStatus, ConsultationTopicEvent } from '@/types/contract'

export const useConsultationStore = defineStore('consultation', {
  state: () => ({
    current: null as Consultation | null,
    messages: [] as ChatMessage[],
    /** 상담사 문의함 (탭: 대기/진행/종료) */
    inbox: [] as Consultation[],
    sub: null as StompSubscription | null,
  }),
  actions: {
    async open(id: number) {
      this.current = await consultationApi.get(id)
      this.messages = await consultationApi.messages(id)
      this.sub?.unsubscribe()
      this.sub = subscribeConsultation(id, (e) => this.applyEvent(e))
    },
    close() {
      this.sub?.unsubscribe()
      this.sub = null
      this.current = null
      this.messages = []
    },
    send(text: string) {
      if (!this.current) return
      const clientMsgId = crypto.randomUUID()
      // TODO(fe): 낙관적 표시(PENDING) 후 MESSAGE_CREATED 의 clientMsgId 로 교체
      sendConsultationMessage(this.current.id, { text, clientMsgId })
    },
    applyEvent(e: ConsultationTopicEvent) {
      switch (e.type) {
        case 'MESSAGE_CREATED':
          this.messages.push(e.message)
          break
        case 'MESSAGE_TRANSLATED': {
          const i = this.messages.findIndex((m) => m.id === e.message.id)
          if (i >= 0) this.messages[i] = e.message
          break
        }
        case 'TRANSLATION_FAILED':
          // TODO(fe): 해당 메시지에 "번역 실패 · 재시도" (consultationApi.retryTranslation)
          break
        case 'CONSULTATION_STATUS':
          if (this.current) this.current.status = e.status
          break
      }
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
    // TODO(fe): ⚠️ 플래그(NUMBER_MISMATCH·MEDICAL_QUESTION) 표시, 번역문 우선 + 원문 토글 (S2)
  },
})
