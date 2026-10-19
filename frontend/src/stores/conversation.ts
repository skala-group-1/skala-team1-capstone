/**
 * AI 대화 (C4 채팅). SSE 이벤트를 reducer(applyEvent) 하나로 state 에 반영한다 (「API·이벤트 명세」 3장 "FE 처리" 열).
 * 대화창 = conversationId(=thread_id) 1개. 병원 선택 시 새 대화창이 열린다 (D-20)
 */
import { defineStore } from 'pinia'
import { aiApi, streamTask } from '@/api'
import type {
  AiProfile,
  Conditions,
  ConversationMessage,
  ConversationMode,
  HospitalCard,
  PendingAction,
  SseEvent,
  SseEventMap,
  Source,
  TaskAction,
  TripPlan,
  Uuid,
} from '@/types/contract'

export const useConversationStore = defineStore('conversation', {
  state: () => ({
    conversationId: null as Uuid | null,
    mode: 'MAIN' as ConversationMode,
    hospital: null as { id: number; name: string } | null,
    consultationId: null as number | null,
    messages: [] as ConversationMessage[],
    /** 조건 칩 바 (상단 고정) */
    conditions: null as Conditions | null,
    missing: [] as string[],

    // 진행 중인 작업
    taskId: null as Uuid | null,
    streaming: false,
    /** TOKEN 누적 */
    draft: '',
    /** 진행 칩 ("병원 검색 중…") */
    activeTools: [] as { tool: string; label: string }[],
    cards: [] as HospitalCard[],
    relaxOptions: [] as SseEventMap['RESULT_CARDS']['relaxOptions'],
    pendingAction: null as PendingAction | null,
    tripPlan: null as SseEventMap['TRIP_PLAN'] | null,
    memoryProposal: null as { fields: AiProfile; message: string } | null,
    error: null as SseEventMap['FAILED'] | null,
    /** CONVERSATION_OPENED 수신 시 화면이 이 값을 보고 /chat/:id 로 이동 */
    openedConversation: null as { conversationId: Uuid; hospitalId: number } | null,
    unsubscribe: null as (() => void) | null,
  }),
  actions: {
    /** 새 메인 대화 또는 병원 대화(hospitalId) 생성 */
    async open(hospitalId: number | null = null, parentConversationId: Uuid | null = null) {
      const conv = await aiApi.createConversation({ hospitalId, parentConversationId })
      this.$reset()
      this.conversationId = conv.id
      this.mode = conv.mode
      this.hospital = conv.hospital
      this.consultationId = conv.consultationId
      this.conditions = conv.conditions
      this.messages = conv.messages
      return conv
    },
    /** 기존 대화 불러오기 (/chat/:conversationId 진입) */
    async load(conversationId: Uuid) {
      // TODO(fe): GET /api/ai/conversations/{id} → state 채우기. 진행 중 작업이 있으면 GET /api/ai/tasks/{id} 후 stream 재연결
      void conversationId
    },
    /** 메시지 전송 또는 버튼 action(SELECT_HOSPITAL·RELAX·SET_SORT·SAVE_PROFILE) */
    async send(message: string | null, action: TaskAction | null = null) {
      if (!this.conversationId) throw new Error('conversation not opened')
      if (message) this.messages.push({ role: 'user', text: message, sources: [], cards: [], createdAt: new Date().toISOString() })
      const { taskId } = await aiApi.createTask({ conversationId: this.conversationId, message, action })
      this.subscribe(taskId)
    },
    /** 승인 카드 (C4-2 / C4-3): 확인·수정·취소 → 같은 taskId 스트림 계속 */
    async approve(approved: boolean, editedArgs: Record<string, unknown> | null = null, reason: string | null = null) {
      if (!this.taskId) return
      await aiApi.approve(this.taskId, { approved, editedArgs, reason })
      this.pendingAction = null
      this.subscribe(this.taskId)
    },
    subscribe(taskId: Uuid) {
      this.unsubscribe?.()
      this.taskId = taskId
      this.streaming = true
      this.draft = ''
      this.error = null
      this.unsubscribe = streamTask(taskId, {
        onEvent: (e) => this.applyEvent(e),
        onError: () => {
          // TODO(fe): 네트워크 오류 표시 + 재시도 버튼 (FAILED 이벤트와 구분)
        },
        onClose: () => {
          this.streaming = false
        },
      })
    },
    /** SSE reducer — 「공통 계약서」 6장 이벤트별 처리 */
    applyEvent(e: SseEvent) {
      switch (e.event) {
        case 'STATUS':
          // 타이핑 표시는 streaming 으로 충분. TODO(fe): QUEUED 가 길면 "대기 중" 문구
          break
        case 'TOKEN':
          this.draft += e.data.text
          break
        case 'TOOL_START':
          this.activeTools.push(e.data)
          break
        case 'TOOL_END':
          this.activeTools = this.activeTools.filter((t) => t.tool !== e.data.tool)
          break
        case 'CONDITIONS':
          this.conditions = e.data.conditions
          this.missing = e.data.missing
          break
        case 'RESULT_CARDS':
          this.cards = e.data.cards
          this.relaxOptions = e.data.relaxOptions
          break
        case 'CONVERSATION_OPENED':
          this.openedConversation = e.data
          break
        case 'MODE_CHANGED':
          this.mode = e.data.mode
          this.consultationId = e.data.consultationId
          // TODO(fe): HUMAN 이면 consultation 스토어로 STOMP 구독 시작, 상담 중에는 AI 입력 대신 상담 메시지 전송
          break
        case 'APPROVAL_REQUIRED':
          this.pendingAction = e.data
          break
        case 'TRIP_PLAN':
          // TODO(fe): 일정 카드(타임라인) 컴포넌트 (「AI Agent 설계」 9-2)
          this.tripPlan = e.data
          break
        case 'MEMORY_PROPOSAL':
          // TODO(fe): "다음에도 기억할까요?" 칩 → send(null, {type:'SAVE_PROFILE', fields})
          this.memoryProposal = e.data
          break
        case 'VERIFY':
          // 화면 표시 없음 (Critic 루프 결과, 디버그용)
          break
        case 'DONE':
          this.pushAssistant(e.data.answer, e.data.sources)
          break
        case 'FAILED':
          this.error = e.data
          break
      }
    },
    pushAssistant(text: string, sources: Source[]) {
      this.messages.push({ role: 'assistant', text: text || this.draft, sources, cards: this.cards, createdAt: new Date().toISOString() })
      this.draft = ''
      this.activeTools = []
    },
  },
})

export type { TripPlan }
