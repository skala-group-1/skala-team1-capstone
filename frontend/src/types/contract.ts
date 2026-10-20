/**
 * 「공통 계약서」 (DTO·Enum·오류·메시지) 를 TypeScript 로 옮긴 것.
 * 필드명·enum 값은 계약서와 1:1 이다. 바꾸려면 Notion 「공통 계약서」를 먼저 고치고 팀에 공지한 뒤 여기를 맞춘다.
 *
 * 공통 규칙 (「공통 계약서」 1장)
 * - JSON 필드는 camelCase
 * - 업무 ID 는 number, conversationId·taskId·traceId·idempotencyKey 는 UUID string
 * - 일시는 ISO-8601 + 오프셋 문자열(`2026-10-21T15:00:00+09:00`), 날짜는 `2026-10-21`
 * - null 허용 필드는 생략되지 않고 null 로 온다 → 화면에서는 "확인 필요" 로 표시
 */

// ─── 기본 별칭 ────────────────────────────────────────────────
export type Uuid = string
/** ISO-8601 일시 (+09:00 오프셋) */
export type IsoDateTime = string
/** YYYY-MM-DD */
export type IsoDate = string

// ─── 2. Enum ─────────────────────────────────────────────────
export type Role = 'CUSTOMER' | 'COUNSELOR' | 'HOSPITAL_ADMIN' | 'OPERATOR'
/** ko 는 스태프 전용 */
export type Locale = 'en' | 'zh' | 'ja' | 'ko'
export type Gender = 'F' | 'M' | 'X'
export type AreaCode = 'GANGNAM' | 'SINSA' | 'APGUJEONG' | 'CHEONGDAM' | 'MYEONGDONG' | 'HONGDAE' | 'JAMSIL'
export type HospitalCategory = 'DERMA' | 'PLASTIC' | 'BOTH'
export type ProcedureCategory = 'SKIN' | 'SURGERY'
export type SkinProcedureCode =
  | 'JAW_BOTOX'
  | 'FOREHEAD_BOTOX'
  | 'LIP_FILLER'
  | 'NOSE_FILLER'
  | 'REJURAN'
  | 'ULTHERAPY'
  | 'THERMAGE'
  | 'SHURINK'
  | 'PICO_TONING'
  | 'LASER_HAIR_REMOVAL'
export type SurgeryProcedureCode =
  | 'DOUBLE_EYELID_NONINCISION'
  | 'DOUBLE_EYELID_INCISION'
  | 'PTOSIS_CORRECTION'
  | 'RHINOPLASTY'
  | 'FACIAL_CONTOURING'
  | 'FAT_GRAFTING'
  | 'LIPOSUCTION'
  | 'BREAST_AUGMENTATION'
export type ProcedureCode = SkinProcedureCode | SurgeryProcedureCode
export type SortBy = 'REVIEW_COUNT' | 'RATING' | 'PRICE' | 'DISTANCE'
export type SlotStatus = 'AVAILABLE' | 'HELD' | 'BOOKED'
export type ReservationStatus = 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED'
export type ReservationSource = 'AI' | 'DIRECT'
export type ConversationMode = 'MAIN' | 'HOSPITAL' | 'HUMAN'
export type AiTaskStatus = 'QUEUED' | 'RUNNING' | 'WAITING_APPROVAL' | 'DONE' | 'FAILED'
export type ConsultationStatus = 'WAITING' | 'ACTIVE' | 'CLOSED'
export type TranslationStatus = 'PENDING' | 'DONE' | 'FAILED'
export type MessageFlag = 'NUMBER_MISMATCH' | 'MEDICAL_QUESTION'
export type SenderRole = 'CUSTOMER' | 'COUNSELOR' | 'SYSTEM'
export type NotificationType =
  | 'RESERVATION_REQUESTED'
  | 'RESERVATION_CONFIRMED'
  | 'RESERVATION_REJECTED'
  | 'RESERVATION_EXPIRED'
  | 'RESERVATION_CANCELLED'
  | 'CONSULTATION_REQUESTED'
  | 'CONSULTATION_ACCEPTED'
  | 'CONSULTATION_CLOSED'

export const AREA_CODES: readonly AreaCode[] = ['GANGNAM', 'SINSA', 'APGUJEONG', 'CHEONGDAM', 'MYEONGDONG', 'HONGDAE', 'JAMSIL']
export const SORT_BY: readonly SortBy[] = ['REVIEW_COUNT', 'RATING', 'PRICE', 'DISTANCE']

// ─── 3. 오류 ─────────────────────────────────────────────────
export type ErrorCode =
  | 'VALIDATION_FAILED'
  | 'UNAUTHENTICATED'
  | 'TOKEN_EXPIRED'
  | 'INVALID_CREDENTIALS'
  | 'REFRESH_INVALID'
  | 'ACCESS_DENIED'
  | 'NOT_FOUND'
  | 'EMAIL_DUPLICATED'
  | 'SLOT_UNAVAILABLE'
  | 'CONCURRENT_UPDATE'
  | 'INVALID_STATE_TRANSITION'
  | 'CONSENT_REQUIRED'
  | 'TASK_NOT_WAITING_APPROVAL'
  | 'UNKNOWN_PROCEDURE'
  | 'INTERNAL_ERROR'
  | 'AI_UNAVAILABLE'

/** 모든 오류 응답 바디. message 는 이미 사용자 locale 문구 */
export interface ErrorResponse {
  code: ErrorCode
  message: string
  traceId: Uuid
  /** 코드별 상세: VALIDATION_FAILED → fields, SLOT_UNAVAILABLE → alternatives, INVALID_STATE_TRANSITION → from/to … */
  details: {
    fields?: { field: string; reason: string }[]
    resource?: string
    alternatives?: Slot[]
    from?: ReservationStatus
    to?: ReservationStatus
    candidates?: { code: ProcedureCode; name: string; score: number }[]
    [key: string]: unknown
  }
}

// ─── 1. 페이지 ───────────────────────────────────────────────
export interface PageRequest {
  /** 0 부터 */
  page?: number
  /** 기본 20 */
  size?: number
}
export interface Page<T> {
  items: T[]
  page: number
  size: number
  total: number
}

// ─── 5. DTO: Auth ────────────────────────────────────────────
export interface UserSummary {
  id: number
  name: string
  role: Role
  hospitalId: number | null
  locale: Locale
}
export interface LoginRequest {
  email: string
  password: string
}
export interface LoginResponse {
  accessToken: string
  /** 초 단위 (1800 = 30분) */
  expiresIn: number
  user: UserSummary
}
export interface SignupRequest {
  email: string
  password: string
  name: string
  birthDate: IsoDate
  gender: Gender
  /** ISO 3166-1 alpha-2 (CN, JP, US …) */
  nationality: string
  /** 가입은 고객만. en/zh/ja + ko (FE 추가, 공통 계약서 반영 필요) */
  locale: Locale
}

// ─── 5. DTO: 탐색·병원 ───────────────────────────────────────
export interface Procedure {
  code: ProcedureCode
  category: ProcedureCategory
  /** 요청자 locale 로 골라진 이름 */
  name: string
  durationMin: number
  downtimeDays: number
}

/** 검색 결과 카드 (AI RESULT_CARDS 공용) */
export interface HospitalCard {
  id: number
  name: string
  areaCode: AreaCode
  category: HospitalCategory
  minPriceKrw: number | null
  priceVerified: boolean
  reviewCount: number
  rating: number | null
  languages: Locale[]
  hasInterpreter: boolean
  earliestSlotAt: IsoDateTime | null
  /** lat/lng 를 보냈을 때만 값이 있음 */
  distanceKm: number | null
}

export interface OpenHour {
  open: string
  close: string
}
export type Weekday = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun'

export interface Doctor {
  id: number
  name: string
  title: string
  specialties: ProcedureCode[]
  languages: Locale[]
  careerYears: number
}

export interface PriceOption {
  id: number
  procedureCode: ProcedureCode
  product: string
  dose: string | null
  priceKrw: number
  vatIncluded: boolean
  conditions: string | null
  verifiedAt: IsoDate | null
}

export interface Slot {
  id: number
  startAt: IsoDateTime
  endAt: IsoDateTime
  doctorId: number | null
  doctorName: string | null
  status: SlotStatus
}

export interface ReviewStats {
  reviewCount: number
  avgRating: number | null
  byAgeGroup: Record<string, number>
  byGender: Partial<Record<Gender, number>>
}

export interface Review {
  id: number
  procedureCode: ProcedureCode
  rating: number
  ageGroup: string
  gender: Gender
  reviewerNationality: string
  lang: Locale
  content: string
  createdAt: IsoDateTime
}

export interface HospitalDetail {
  id: number
  name: string
  /** 스태프 화면용 한국어 이름 */
  nameKo: string
  category: HospitalCategory
  areaCode: AreaCode
  address: string | null
  phone: string | null
  description: string | null
  /** 휴무일은 null */
  openHours: Partial<Record<Weekday, OpenHour | null>>
  languages: Locale[]
  hasInterpreter: boolean
  verifiedAt: IsoDate | null
  doctors: Doctor[]
  procedures: { procedure: Procedure; options: PriceOption[] }[]
  reviewStats: ReviewStats
}

/** 07: GET /api/hospitals/search 쿼리 (공개 API 이름. 12 Conditions 와 이름이 다름에 주의) */
export interface HospitalSearchQuery extends PageRequest {
  procedure?: ProcedureCode
  areas?: AreaCode[]
  dateFrom?: IsoDate
  dateTo?: IsoDate
  priceMax?: number
  language?: Locale
  sort?: SortBy
  lat?: number
  lng?: number
}

export interface CompareRequest {
  hospitalIds: number[]
  procedureCode: ProcedureCode
}
export interface CompareResponse {
  procedureCode: ProcedureCode
  columns: {
    hospital: HospitalCard
    options: PriceOption[]
    earliestSlotAt: IsoDateTime | null
    verifiedAt: IsoDate | null
  }[]
}

// ─── 5. DTO: 예약 ────────────────────────────────────────────
/** 헤더 Idempotency-Key 필수 */
export interface CreateReservationRequest {
  hospitalId: number
  slotId: number
  procedureCode: ProcedureCode
  priceOptionId: number | null
  note: string | null
}

/** 스태프에게 보이는 고객 정보 (이름 마스킹, 연락처 없음) */
export interface MaskedCustomer {
  id: number
  name: string
  nationality: string
  locale: Locale
}

export interface Reservation {
  id: number
  status: ReservationStatus
  source: ReservationSource
  hospital: { id: number; name: string }
  slot: Slot
  procedure: Procedure
  priceOption: PriceOption | null
  holdExpiresAt: IsoDateTime | null
  rejectReason: string | null
  alternatives: Slot[]
  /** 스태프 조회 시에만 */
  customer?: MaskedCustomer
  /** 고객 메모 (13-1 §12 추가 필드) */
  note: string | null
  createdAt: IsoDateTime
  decidedAt: IsoDateTime | null
}

export interface RejectRequest {
  reason: string
  /** 최대 3 */
  alternativeSlotIds: number[]
}

// ─── 5. DTO: AI ──────────────────────────────────────────────
/** dateFrom = 입국일, dateTo = 출국일 (D-23) */
export interface Conditions {
  procedureCode: ProcedureCode | null
  areas: AreaCode[]
  dateFrom: IsoDate | null
  dateTo: IsoDate | null
  budgetMaxKrw: number | null
  consultLanguage: Locale | null
  sortBy: SortBy
}

export interface CreateConversationRequest {
  hospitalId: number | null
  parentConversationId: Uuid | null
}

export interface Source {
  docId: string
  title: string
  section: string
  /** doc://{docId}#{section} */
  uri: string
  snippet: string
}

export type MessageRole = 'user' | 'assistant' | 'counselor' | 'system'
export interface ConversationMessage {
  role: MessageRole
  text: string
  sources: Source[]
  cards: HospitalCard[]
  createdAt: IsoDateTime
}

export interface Conversation {
  id: Uuid
  mode: ConversationMode
  hospital: { id: number; name: string } | null
  parentConversationId: Uuid | null
  consultationId: number | null
  conditions: Conditions
  createdAt: IsoDateTime
  messages: ConversationMessage[]
}

export type RelaxOption = 'DATE_PLUS_MINUS_1' | string

export type TaskAction =
  | { type: 'SELECT_HOSPITAL'; hospitalId: number }
  | { type: 'RELAX'; option: RelaxOption }
  | { type: 'SET_SORT'; sortBy: SortBy }
  | { type: 'SAVE_PROFILE'; fields: AiProfile }

export interface CreateTaskRequest {
  conversationId: Uuid
  message: string | null
  action: TaskAction | null
}
/** POST /api/ai/tasks → 202 */
export interface CreateTaskResponse {
  taskId: Uuid
}

export type PendingActionType = 'CREATE_RESERVATION' | 'REQUEST_CONSULTATION' | 'CANCEL_RESERVATION'
/** APPROVAL_REQUIRED 이벤트 payload 와 동일 */
export interface PendingAction {
  action: PendingActionType
  display: { title: string; rows: { label: string; value: string }[]; notice: string }
  args: Record<string, unknown>
  /** 고객이 수정 가능한 args 키 */
  editable: string[]
}

export interface AiTask {
  id: Uuid
  conversationId: Uuid
  status: AiTaskStatus
  answer: string | null
  sources: Source[]
  pendingAction: PendingAction | null
  error: { code: ErrorCode; message: string } | null
  createdAt: IsoDateTime
  /** 13-1 §12 추가 */
  message?: string | null
  finishedAt?: IsoDateTime | null
}

/** 운영자 (13-2): GET /api/ops/audit-logs 항목 */
export interface AuditLog {
  id: number
  traceId: Uuid
  actorId: number | null
  actorRole: Role | null
  action: string
  target: string
  detail: Record<string, unknown>
  createdAt: IsoDateTime
}
/** 운영자 (13-2): GET /api/ops/ai-tasks 항목 = AiTask + userId */
export type OpsAiTask = AiTask & { userId: number }

export interface ApprovalRequest {
  approved: boolean
  editedArgs: Record<string, unknown> | null
  reason: string | null
}

// Agentic v2 (D-22~D-25)
export type TripPlanReason = 'OK' | 'RECOVERY_AFTER_DEPARTURE' | 'NO_SLOT_BEFORE_DEPARTURE'
export interface TripPlan {
  hospitalId: number
  hospitalName: string
  slot: Slot | null
  procedureCode: ProcedureCode
  downtimeDays: number
  recoveryEndDate: IsoDate | null
  bufferDays: number | null
  feasible: boolean
  reason: TripPlanReason
}

/** 장기 기억 프로필 (동의 후 저장) */
export interface AiProfile {
  preferredAreas: AreaCode[]
  budgetMaxKrw: number | null
  interestedProcedures: ProcedureCode[]
  consultLanguage: Locale | null
  /** 민감정보 */
  skinConcerns: string | null
  updatedAt: IsoDateTime | null
}

// ─── 5. DTO: 상담·채팅·알림 ──────────────────────────────────
/** 고객용은 고객 언어, 상담사용은 ko */
export interface SummaryCard {
  procedure: string
  preferredDates: string
  stayDays: number | null
  budget: string | null
  questions: string[]
  customerLocale: Locale
}

export interface Consultation {
  id: number
  status: ConsultationStatus
  hospital: { id: number; name: string }
  customer: MaskedCustomer
  counselorId: number | null
  conversationId: Uuid
  summaryCard: SummaryCard
  createdAt: IsoDateTime
}

/** REST 히스토리·STOMP 공용 */
export interface ChatMessage {
  id: number
  consultationId: number
  senderRole: SenderRole
  senderId: number | null
  originalText: string
  originalLang: Locale
  translatedText: string | null
  translatedLang: Locale | null
  translationStatus: TranslationStatus
  flags: MessageFlag[]
  clientMsgId: Uuid | null
  createdAt: IsoDateTime
}

export interface Notification {
  id: number
  type: NotificationType
  payload: Record<string, unknown>
  readAt: IsoDateTime | null
  createdAt: IsoDateTime
}

export interface HospitalDashboard {
  todayReservations: number
  pendingReservations: number
  activeConsultations: number
  recentRequests: Reservation[]
}

// ─── 6. SSE 이벤트 payload ───────────────────────────────────
/** event 이름 → data 타입. SSE `id:` = seq (재연결 시 Last-Event-ID) */
export interface SseEventMap {
  STATUS: { status: AiTaskStatus }
  TOKEN: { text: string }
  TOOL_START: { tool: string; label: string }
  TOOL_END: { tool: string; ok: boolean }
  CONDITIONS: { conditions: Conditions; missing: (keyof Conditions)[] }
  RESULT_CARDS: {
    cards: HospitalCard[]
    relaxOptions: { option: RelaxOption; label: string; expectedCount: number }[]
  }
  CONVERSATION_OPENED: { conversationId: Uuid; hospitalId: number }
  MODE_CHANGED: { mode: ConversationMode; consultationId: number | null }
  APPROVAL_REQUIRED: PendingAction
  TRIP_PLAN: { arrivalDate: IsoDate; departureDate: IsoDate; plans: TripPlan[]; summary: string }
  MEMORY_PROPOSAL: { fields: AiProfile; message: string }
  VERIFY: { passed: boolean; attempts: number }
  DONE: { answer: string; sources: Source[] }
  FAILED: { code: ErrorCode; message: string; traceId: Uuid }
}
export type SseEventName = keyof SseEventMap
/** 판별 유니온: switch (e.event) 로 data 타입이 좁혀진다 */
export type SseEvent = { [K in SseEventName]: { event: K; data: SseEventMap[K]; seq: number | null } }[SseEventName]
/** 스트림이 끝나는 이벤트 (12-7: 마지막은 반드시 이 셋 중 하나) */
export const TERMINAL_SSE_EVENTS: readonly SseEventName[] = ['DONE', 'FAILED', 'APPROVAL_REQUIRED']

// ─── STOMP 이벤트 (13-2 "상담·채팅": 토픽 본문 {type, data}) ───────────────
export type ConsultationTopicEvent =
  | { type: 'MESSAGE_CREATED' | 'MESSAGE_TRANSLATED' | 'TRANSLATION_FAILED'; data: ChatMessage }
  | { type: 'CONSULTATION_STATUS'; data: { consultationId: number; status: ConsultationStatus; counselorId: number | null } }
export interface SendChatMessage {
  text: string
  clientMsgId: Uuid
}
