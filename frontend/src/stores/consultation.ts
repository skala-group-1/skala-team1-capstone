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

/** open() 순번 — await 사이에 다른 상담을 열거나 close() 하면 늦게 끝난 open 은 구독을 등록하지 않는다 */
let openSeq = 0

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
      const seq = openSeq
      const current = await consultationApi.get(id)
      if (seq !== openSeq) return
      this.current = current
      const messages = await consultationApi.messages(id)
      if (seq !== openSeq) return
      this.messages = messages
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
      openSeq++
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
      await this.deliver(this.current.id, text, clientMsgId)
    },
    /**
     * 실제 전송. 실패하면 임시 메시지(id<0)를 FAILED 로 바꿔 "다시 보내기"를 띄운다.
     * STOMP publish 는 응답이 없으므로 10초 안에 MESSAGE_CREATED 가 안 오면 서버를 다시 조회하고, 그래도 없으면 실패 처리.
     * 같은 clientMsgId 재전송은 backend 가 기존 메시지를 돌려준다 (중복 없음)
     */
    async deliver(consultationId: number, text: string, clientMsgId: string) {
      const unsent = () => this.messages.findIndex((m) => m.clientMsgId === clientMsgId && m.id < 0)
      const markFailed = () => {
        const i = unsent()
        if (i >= 0) this.messages[i] = { ...this.messages[i], translationStatus: 'FAILED' }
      }
      try {
        if (isStompConnected()) {
          sendConsultationMessage(consultationId, { text, clientMsgId })
          setTimeout(async () => {
            if (this.current?.id !== consultationId || unsent() < 0) return
            await this.refetch()
            markFailed()
          }, 10_000)
        } else {
          const m = await http.post<ChatMessage>(`/consultations/${consultationId}/messages`, { text, clientMsgId }).then((r) => r.data)
          if (this.current?.id === consultationId) this.upsert(m)
        }
      } catch {
        markFailed()
      }
    },
    upsert(m: ChatMessage) {
      const i = this.messages.findIndex((x) => x.id === m.id || (m.clientMsgId && x.clientMsgId === m.clientMsgId))
      if (i >= 0) this.messages[i] = m
      else this.messages.push(m)
    },
    applyEvent(e: ConsultationTopicEvent) {
      // 다른 상담방 이벤트는 버린다 (구독 해제가 늦게 반영되는 경우 대비)
      if (e.data.consultationId !== this.current?.id) return
      if (e.type === 'CONSULTATION_STATUS') {
        if (this.current) {
          this.current.status = e.data.status
          this.current.counselorId = e.data.counselorId
          this.syncInbox(this.current)
        }
        return
      }
      this.upsert(e.data)
    },
    /** 실패 말풍선의 재시도: 아직 안 보내진 메시지(id<0)는 다시 보내고, 보내진 메시지는 번역만 다시 요청 */
    async retryTranslation(msg: ChatMessage) {
      if (!this.current) return
      if (msg.id < 0) {
        if (!msg.clientMsgId) return
        this.upsert({ ...msg, translationStatus: 'PENDING' })
        return this.deliver(this.current.id, msg.originalText, msg.clientMsgId)
      }
      await consultationApi.retryTranslation(this.current.id, msg.id)
      this.upsert({ ...msg, translationStatus: 'PENDING' })
    },
    // ─── 상담사 ───
    async loadInbox(status?: ConsultationStatus) {
      this.inbox = await counselorApi.inbox(status)
    },
    async accept(id: number) {
      this.current = await counselorApi.accept(id)
      this.syncInbox(this.current)
    },
    async finish(id: number) {
      this.current = await counselorApi.close(id)
      this.syncInbox(this.current)
    },
    /** 열어 둔 상담의 상태 변화를 문의함 목록에도 반영 (목록이 '진행'에 남지 않게) */
    syncInbox(c: Consultation) {
      const i = this.inbox.findIndex((x) => x.id === c.id)
      if (i >= 0) this.inbox[i] = { ...this.inbox[i], status: c.status, counselorId: c.counselorId }
    },
    /** 고객 종료: 응답의 CLOSED 상태로 바꾸면 ChatView 가 병원 대화(AI)로 되돌린다 */
    async endByCustomer() {
      if (!this.current) return
      this.current = await consultationApi.close(this.current.id)
    },
  },
})
