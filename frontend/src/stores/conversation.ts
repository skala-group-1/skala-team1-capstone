/**
 * AI 대화 (C4 채팅). SSE 이벤트를 reducer(applyEvent) 하나로 state 에 반영한다 (「API·이벤트 명세」 3장 "FE 처리" 열).
 * 대화창 = conversationId(=thread_id) 1개. 병원 선택 시 새 대화창이 열린다 (D-20)
 */
import { defineStore } from 'pinia'
import { aiApi, streamTask } from '@/api'
import type {
  AiProfile,
  Conditions,
  ConsultTopic,
  ConversationMessage,
  ConversationMode,
  HospitalCard,
  PendingAction,
  ProcedureInfo,
  SseEvent,
  SseEventMap,
  Source,
  TaskAction,
  TripPlan,
  Uuid,
} from '@/types/contract'

/** load() 요청 순번 — 마지막 요청의 응답만 반영 */
let loadSeq = 0

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
    /** C4-T 상담 주제 바 */
    topic: null as ConsultTopic | null,

    // 진행 중인 작업
    taskId: null as Uuid | null,
    /** 현재 작업에서 마지막으로 받은 SSE seq (승인 후 재연결 때 Last-Event-ID 로 보냄) */
    lastSeq: null as number | null,
    streaming: false,
    /** TOKEN 누적 */
    draft: '',
    /** 진행 칩 ("병원 검색 중…") */
    activeTools: [] as { tool: string; label: string }[],
    cards: [] as HospitalCard[],
    /** C4-T 고민 관련 시술 정보 카드 (PROCEDURE_INFO) */
    procedures: [] as ProcedureInfo[],
    relaxOptions: [] as SseEventMap['RESULT_CARDS']['relaxOptions'],
    pendingAction: null as PendingAction | null,
    tripPlan: null as SseEventMap['TRIP_PLAN'] | null,
    /** 마지막 답변의 선택지 칩 (DONE.suggestions). 탭하면 문구를 message 로 보냄 */
    suggestions: [] as string[],
    memoryProposal: null as { fields: AiProfile; message: string } | null,
    error: null as SseEventMap['FAILED'] | null,
    /** CONVERSATION_OPENED 수신 시 화면이 이 값을 보고 /chat/:id 로 이동 */
    openedConversation: null as SseEventMap['CONVERSATION_OPENED'] | null,
    unsubscribe: null as (() => void) | null,
    /** 재시도용 마지막 입력 (Edge ② 응답 실패 → 같은 message 로 다시 POST) */
    lastInput: null as { message: string | null; action: TaskAction | null } | null,
    /** 승인한 변경 작업 (DONE 후 예약 요청 완료 카드 표시용) */
    approvedAction: null as PendingAction['action'] | null,
    parentConversationId: null as Uuid | null,
  }),
  actions: {
    /** 새 메인 대화 또는 병원 대화(hospitalId) 생성 */
    async open(hospitalId: number | null = null, parentConversationId: Uuid | null = null) {
      const conv = await aiApi.createConversation({ hospitalId, parentConversationId })
      this.unsubscribe?.()
      this.$reset()
      this.conversationId = conv.id
      this.mode = conv.mode
      this.hospital = conv.hospital
      this.consultationId = conv.consultationId
      this.conditions = conv.conditions
      this.topic = conv.topic ?? null
      this.messages = conv.messages ?? []
      this.parentConversationId = conv.parentConversationId
      await this.restoreActiveTask()
      return conv
    },
    /** 기존 대화 불러오기 (/chat/:conversationId 진입) */
    async load(conversationId: Uuid) {
      const seq = ++loadSeq
      const conv = await aiApi.conversation(conversationId)
      // A→B 로 빨리 넘어가면 늦게 온 A 응답은 버린다
      if (seq !== loadSeq) return conv
      this.unsubscribe?.()
      this.$reset()
      this.conversationId = conv.id
      this.mode = conv.mode
      this.hospital = conv.hospital
      this.consultationId = conv.consultationId
      this.conditions = conv.conditions
      this.topic = conv.topic ?? null
      this.messages = conv.messages ?? []
      this.parentConversationId = conv.parentConversationId
      await this.restoreActiveTask()
      return conv
    },
    /** 같은 대화로 돌아올 때: 화면 상태(결과 카드·승인 대기)는 두고 모드만 서버 기준으로 맞춤 (자리 비운 사이 상담 종료 등) */
    async refresh(conversationId: Uuid) {
      const conv = await aiApi.conversation(conversationId)
      this.mode = conv.mode
      this.consultationId = conv.consultationId
      this.hospital = conv.hospital
      if (!this.streaming && !this.pendingAction) await this.restoreActiveTask()
    },
    /** Reload the existing approval instead of creating another task. */
    async restoreActiveTask(activeTaskId?: Uuid): Promise<boolean> {
      const conversationId = this.conversationId
      if (!conversationId || this.mode === 'HUMAN') return false
      try {
        const tasks = activeTaskId ? [await aiApi.task(activeTaskId)] : await aiApi.myTasks()
        if (this.conversationId !== conversationId || (this.mode as ConversationMode) === 'HUMAN') return false
        const task = tasks.find((t) => t.conversationId === conversationId
          && ['QUEUED', 'RUNNING', 'WAITING_APPROVAL'].includes(t.status))
        if (!task) return false
        this.pendingAction = task.status === 'WAITING_APPROVAL' ? task.pendingAction : null
        this.subscribe(task.id)
        return true
      } catch {
        return false
      }
    },
    /** 메시지 전송 또는 버튼 action(SELECT_HOSPITAL·RELAX·SET_SORT·SAVE_PROFILE·SELECT_TOPIC·FIND_BY_CONCERNS) */
    async send(message: string | null, action: TaskAction | null = null, echo = true) {
      if (!this.conversationId) throw new Error('conversation not opened')
      if (this.pendingAction || this.streaming) return
      if (message && echo) this.messages.push({ role: 'user', text: message, sources: [], cards: [], createdAt: new Date().toISOString() })
      this.lastInput = { message, action }
      if (action?.type === 'SELECT_TOPIC') this.topic = action.topic
      this.error = null
      this.cards = []
      this.procedures = []
      this.relaxOptions = []
      this.tripPlan = null
      this.memoryProposal = null
      this.suggestions = []
      this.streaming = true
      try {
        const { taskId } = await aiApi.createTask({ conversationId: this.conversationId, message, action })
        this.subscribe(taskId)
      } catch (e) {
        this.streaming = false
        const err = e as { response?: { data?: SseEventMap['FAILED'] & { details?: { activeTaskId?: Uuid } } } }
        const activeTaskId = err.response?.data?.details?.activeTaskId
        if (activeTaskId && await this.restoreActiveTask(activeTaskId)) return
        this.error = err.response?.data ?? { code: 'AI_UNAVAILABLE', message: '', traceId: '' }
      }
    },
    /** Edge ② 다시 시도: 같은 입력을 다시 보냄 (사용자 말풍선은 다시 추가하지 않음) */
    retry() {
      if (this.lastInput) void this.send(this.lastInput.message, this.lastInput.action, false)
    },
    /** 승인 카드 (C4-2 / C4-3): 확인·수정·취소 → 같은 taskId 스트림 계속 */
    async approve(approved: boolean, editedArgs: Record<string, unknown> | null = null, reason: string | null = null) {
      if (!this.taskId) return
      try {
        await aiApi.approve(this.taskId, { approved, editedArgs, reason })
      } catch (e) {
        // 이미 처리됐거나 만료된 승인 → 카드를 내리고 서버 상태로 다시 맞춘다
        if ((e as { response?: { data?: { code?: string } } }).response?.data?.code === 'TASK_NOT_WAITING_APPROVAL') {
          this.pendingAction = null
          await this.restoreActiveTask()
        }
        throw e
      }
      this.approvedAction = approved ? (this.pendingAction?.action ?? null) : null
      this.pendingAction = null
      // 이미 받은 이벤트(승인 카드까지)는 다시 받지 않도록 마지막 seq 이후부터
      this.subscribe(this.taskId, this.lastSeq)
    },
    subscribe(taskId: Uuid, fromSeq: number | null = null) {
      this.unsubscribe?.()
      if (taskId !== this.taskId) this.lastSeq = null
      this.taskId = taskId
      this.streaming = true
      this.draft = ''
      this.error = null
      let cancelled = false
      const stop = streamTask(
        taskId,
        {
          onEvent: (e) => {
            if (cancelled) return
            if (e.seq != null) this.lastSeq = e.seq
            this.applyEvent(e)
          },
          onError: () => {
            if (cancelled) return
            this.error = { code: 'AI_UNAVAILABLE', message: '', traceId: '' }
          },
          onClose: () => {
            if (cancelled) return
            this.streaming = false
          },
        },
        fromSeq,
      )
      this.unsubscribe = () => { cancelled = true; stop() }
    },
    /** SSE reducer — 「공통 계약서」 6장 이벤트별 처리 */
    applyEvent(e: SseEvent) {
      switch (e.event) {
        case 'STATUS':
          // 타이핑 표시는 streaming 으로 충분
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
          this.conditions = { ...e.data.conditions, areas: e.data.conditions.areas ?? [] }
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
          // HUMAN 이면 ChatView 가 consultation 스토어로 STOMP 구독 (상담 중 AI 입력 대신 상담 메시지)
          this.mode = e.data.mode
          this.consultationId = e.data.consultationId
          break
        case 'APPROVAL_REQUIRED':
          // 종료 이벤트라 DONE 이 안 온다 → 앞서 받은 TOKEN 을 말풍선으로 남긴다
          if (this.draft) this.pushAssistant('', [])
          this.pendingAction = e.data
          break
        case 'PROCEDURE_INFO':
          this.procedures = e.data.procedures
          break
        case 'TRIP_PLAN':
          this.tripPlan = e.data
          break
        case 'MEMORY_PROPOSAL':
          this.memoryProposal = e.data
          break
        case 'VERIFY':
          // 화면 표시 없음 (Critic 루프 결과, 디버그용)
          break
        case 'DONE':
          this.pushAssistant(e.data.answer, e.data.sources)
          this.suggestions = (e.data.suggestions ?? []).slice(0, 4)
          break
        case 'FAILED':
          this.error = e.data
          this.draft = ''
          this.activeTools = []
          break
      }
    },
    pushAssistant(text: string, sources: Source[]) {
      this.messages.push({ role: 'assistant', text: text || this.draft, sources, cards: this.cards, procedures: this.procedures, createdAt: new Date().toISOString() })
      this.draft = ''
      this.activeTools = []
    },
  },
})

export type { TripPlan }
