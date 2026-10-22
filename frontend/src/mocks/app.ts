/**
 * MSW 핸들러 (나머지 화면용) — 예약 · 알림 · 상담/채팅 · 병원관리자 · 운영자 · 회원가입 · 비교 · 리뷰 · 근거 문서 · AI 시나리오.
 * mock JSON 을 메모리로 복사해 쓰므로 새로고침하면 초기화된다. 경로·DTO 는 13-2 「API 요청·응답 예시」와 같다.
 * AI 는 메시지 내용으로 갈래를 나눈 가짜 SSE (실제 agent 동작이 아니라 화면 흐름 확인용):
 *   메인: 기본 → 조건·결과 카드 / "50만"·"500k" → 0건 완화 / "일정"·"trip" → 일정 카드 + 기억 제안 / "실패"·"fail" → FAILED
 *   병원: "예약"·"book" → 예약 승인 카드 / "상담원"·"counselor" → 상담 요약 + 동의 / 그 외 → 안내 답변
 */
import { delay, http, HttpResponse } from 'msw'
import reservationsJson from '@mock/reservations.json'
import consultationsJson from '@mock/consultations.json'
import chatMessagesJson from '@mock/chat_messages.json'
import conversationsJson from '@mock/conversations.json'
import type {
  AuditLog,
  ChatMessage,
  Consultation,
  ConsultTopic,
  Conversation,
  ConversationMessage,
  ErrorResponse,
  Locale,
  MessageFlag,
  Notification,
  NotificationType,
  OpsAiTask,
  PendingAction,
  ProcedureCode,
  ProcedureInfo,
  Reservation,
  ReservationStatus,
  SkinConcern,
  SseEventName,
  SummaryCard,
} from '@/types/contract'
import {
  addReview,
  hideReviewOf,
  doctors,
  hospitals,
  pickName,
  priceOptions,
  procedures,
  reviews,
  slots,
  toHospitalCard,
  toPriceOption,
  toProcedure,
  toReview,
  toSlot,
  toUserSummary,
  users,
} from './db'

const API = '/api'
const ragDocs = import.meta.glob('../../../data/mock/rag_docs/**/*.md', { query: '?raw', import: 'default', eager: true }) as Record<string, string>

// ─── 공통 ────────────────────────────────────────────────────
function error(status: number, code: ErrorResponse['code'], message: string, details: ErrorResponse['details'] = {}) {
  return HttpResponse.json<ErrorResponse>({ code, message, traceId: crypto.randomUUID(), details }, { status })
}
function me(request: Request) {
  const token = request.headers.get('Authorization')?.replace('Bearer ', '')
  const id = token?.startsWith('mock.') ? Number(token.slice(5)) : NaN
  return users.find((u) => u.id === id) ?? null
}
function localeOf(request: Request): Locale {
  const l = request.headers.get('Accept-Language')?.slice(0, 2)
  return l === 'zh' || l === 'ja' || l === 'ko' ? l : 'en'
}
const nowIso = () => new Date(Date.now() + 9 * 3600_000).toISOString().replace('Z', '+09:00').replace(/\.\d{3}/, '')
const mask = (name: string) => (/[぀-ヿ一-鿿]/.test(name) ? `${name[0]}**` : name.split(' ').map((w) => `${w[0]}**`).join(' '))
const page = <T>(items: T[], url: URL) => {
  const p = Number(url.searchParams.get('page') ?? 0)
  const size = Number(url.searchParams.get('size') ?? 20)
  return { items: items.slice(p * size, p * size + size), page: p, size, total: items.length }
}
type Row = Record<string, unknown>

// ─── 메모리 상태 ──────────────────────────────────────────────
type ResRow = {
  id: number
  user_id: number
  hospital_id: number
  slot_id: number
  procedure_code: string
  status: ReservationStatus
  source: 'AI' | 'DIRECT'
  customer_note: string | null
  reject_reason: string | null
  alternative_slot_ids: number[]
  hold_expires_at: string | null
  created_at: string
  decided_at: string | null
  price_option_id?: number | null
  idempotency_key?: string
}
const resRows: ResRow[] = (reservationsJson as unknown as ResRow[]).map((r) => ({ ...r }))
// 데모용: 승인 대기 건의 홀드를 지금 기준 3~28분 남게. 첫 건은 만료(EXPIRED) 화면 확인용
resRows
  .filter((r) => r.status === 'PENDING')
  .forEach((r, i) => {
    const ms = Date.now() + (i === 0 ? -2 : 3 + ((i * 7) % 26)) * 60_000
    r.hold_expires_at = new Date(ms + 9 * 3600_000).toISOString().replace('Z', '+09:00').replace(/\.\d{3}/, '')
    if (i === 0) r.status = 'EXPIRED'
  })

type ConsRow = {
  id: number
  user_id: number
  hospital_id: number
  counselor_id: number | null
  conversation_id: string
  status: 'WAITING' | 'ACTIVE' | 'CLOSED'
  customer_locale: Locale
  summary_card: Row
  summary_card_ko: Row
  created_at: string
}
const consRows: ConsRow[] = (consultationsJson as unknown as ConsRow[]).map((c) => ({ ...c }))
type MsgRow = {
  id: number
  consultation_id: number
  sender_id: number | null
  sender_role: 'CUSTOMER' | 'COUNSELOR' | 'SYSTEM'
  original_text: string
  original_lang: Locale
  translated_text: string | null
  translated_lang: Locale | null
  translation_status: 'PENDING' | 'DONE' | 'FAILED'
  flags: Row | string[]
  client_msg_id?: string | null
  created_at: string
}
const msgRows: MsgRow[] = (chatMessagesJson as unknown as MsgRow[]).map((m) => ({ ...m }))
type ConvRow = {
  id: string
  user_id: number
  parent_conversation_id: string | null
  mode: 'MAIN' | 'HOSPITAL' | 'HUMAN'
  selected_hospital_id: number | null
  consultation_id: number | null
  created_at: string
  conditions?: Conversation['conditions']
  topic?: ConsultTopic | null
  messages?: ConversationMessage[]
}
const convRows: ConvRow[] = (conversationsJson as unknown as ConvRow[]).map((c) => ({ ...c, messages: [] }))
const notifs: (Notification & { userId: number })[] = []
const audits: AuditLog[] = []
type TaskRow = OpsAiTask & { action: unknown; phase: 'initial' | 'resume'; approved?: boolean; editedArgs?: Row | null }
const tasks: TaskRow[] = []

let seq = 1000
const nextId = () => ++seq
function audit(actor: { id: number; role: string } | null, action: string, target: string) {
  audits.unshift({ id: nextId(), traceId: crypto.randomUUID(), actorId: actor?.id ?? null, actorRole: (actor?.role ?? null) as AuditLog['actorRole'], action, target, detail: {}, createdAt: nowIso() })
}
function notify(userIds: number[], type: NotificationType, payload: Row, at = nowIso()) {
  for (const userId of userIds) notifs.unshift({ id: nextId(), userId, type, payload, readAt: null, createdAt: at })
}
const adminsOf = (hospitalId: number) => users.filter((u) => u.role === 'HOSPITAL_ADMIN' && u.hospital_id === hospitalId).map((u) => u.id)
const counselorsOf = (hospitalId: number) => users.filter((u) => u.role === 'COUNSELOR' && u.hospital_id === hospitalId).map((u) => u.id)

// 초기 알림: 예약 상태를 알림으로 (최근 것이 위)
for (const r of [...resRows].sort((a, b) => a.created_at.localeCompare(b.created_at))) {
  const type = ({ CONFIRMED: 'RESERVATION_CONFIRMED', REJECTED: 'RESERVATION_REJECTED', EXPIRED: 'RESERVATION_EXPIRED', CANCELLED: 'RESERVATION_CANCELLED' } as const)[
    r.status as 'CONFIRMED'
  ]
  if (type) notify([r.user_id], type, { reservationId: r.id }, r.decided_at ?? r.created_at)
  if (r.status === 'PENDING') notify(adminsOf(r.hospital_id), 'RESERVATION_REQUESTED', { reservationId: r.id }, r.created_at)
}
for (const c of consRows) if (c.status === 'ACTIVE') notify([c.user_id], 'CONSULTATION_ACCEPTED', { consultationId: c.id, conversationId: c.conversation_id }, c.created_at)
audit({ id: 8, role: 'HOSPITAL_ADMIN' }, 'RESERVATION_APPROVED', 'reservation 1')
audit({ id: 3, role: 'CUSTOMER' }, 'RESERVATION_CREATED', 'reservation 2')
audit({ id: 7, role: 'COUNSELOR' }, 'ACCESS_DENIED', 'GET /api/reservations/2')
tasks.push(
  ...[
    { message: '도담솔 10/21 오후 자리 있어요?', error: 'business-mcp no response (30s)' },
    { message: '강남 리프팅 가격 비교해 줘', error: 'no progress for 5 minutes' },
    { message: '중국어 상담 되는 병원 찾아 줘', error: 'rag-mcp 503' },
  ].map((x, i) => ({
    id: crypto.randomUUID(),
    conversationId: crypto.randomUUID(),
    status: 'FAILED' as const,
    answer: null,
    sources: [],
    pendingAction: null,
    error: { code: 'AI_UNAVAILABLE' as const, message: x.error },
    createdAt: nowIso(),
    message: x.message,
    finishedAt: nowIso(),
    userId: [3, 5, 3][i],
    action: null,
    phase: 'initial' as const,
  })),
)

// ─── DTO 변환 ────────────────────────────────────────────────
function toReservation(r: ResRow, locale: Locale, staff: boolean): Reservation {
  const h = hospitals.find((x) => x.id === r.hospital_id)!
  const p = procedures.find((x) => x.code === r.procedure_code)!
  const opt =
    priceOptions.find((o) => o.id === r.price_option_id) ??
    priceOptions.find((o) => o.hospital_id === r.hospital_id && o.procedure_code === r.procedure_code) ??
    null
  const slotRow = slots.find((s) => s.id === r.slot_id)!
  const u = users.find((x) => x.id === r.user_id)!
  const raw = u as unknown as { nationality?: string }
  const reviewId = reviews.find((x) => x.reservation_id === r.id)?.id ?? null
  return {
    id: r.id,
    status: r.status,
    source: r.source,
    hospital: { id: h.id, name: staff ? h.name_ko : pickName(h, locale) },
    slot: toSlot(slotRow),
    procedure: toProcedure(p, staff ? 'ko' : locale),
    priceOption: opt ? toPriceOption(opt, staff ? 'ko' : locale) : null,
    holdExpiresAt: r.status === 'PENDING' ? r.hold_expires_at : null,
    rejectReason: r.reject_reason,
    alternatives: r.status === 'REJECTED' ? r.alternative_slot_ids.map((id) => toSlot(slots.find((s) => s.id === id)!)).filter(Boolean) : [],
    customer: staff ? { id: u.id, name: mask(u.name), nationality: raw.nationality ?? '', locale: u.locale as Locale } : undefined,
    note: r.customer_note,
    createdAt: r.created_at,
    decidedAt: r.decided_at,
    reviewable: r.status === 'CONFIRMED' && reviewId === null,
    reviewId,
  }
}
function toSummary(card: Row, locale: Locale): SummaryCard {
  const dates = (card.preferred_dates as string[] | undefined) ?? []
  return {
    procedure: String(card.procedure_name ?? card.procedure ?? ''),
    preferredDates: [...new Set(dates)].join(' ~ '),
    stayDays: (card.stay_days as number | undefined) ?? null,
    budget: (card.budget as string | undefined) ?? null,
    questions: ((card.concerns ?? card.questions) as string[] | undefined) ?? [],
    customerLocale: (card.language as Locale | undefined) ?? locale,
  }
}
function toConsultation(c: ConsRow, forCounselor: boolean): Consultation {
  const u = users.find((x) => x.id === c.user_id)!
  const h = hospitals.find((x) => x.id === c.hospital_id)!
  const raw = u as unknown as { nationality?: string }
  return {
    id: c.id,
    status: c.status,
    hospital: { id: h.id, name: forCounselor ? h.name_ko : pickName(h, c.customer_locale) },
    customer: { id: u.id, name: forCounselor ? mask(u.name) : u.name, nationality: raw.nationality ?? '', locale: c.customer_locale },
    counselorId: c.counselor_id,
    conversationId: c.conversation_id,
    summaryCard: toSummary(forCounselor ? c.summary_card_ko : c.summary_card, c.customer_locale),
    createdAt: c.created_at,
  }
}
function toMessage(m: MsgRow): ChatMessage {
  const flags: MessageFlag[] = Array.isArray(m.flags)
    ? (m.flags as MessageFlag[])
    : [...((m.flags as Row).medical_content ? ['MEDICAL_QUESTION' as const] : []), ...((m.flags as Row).number_mismatch ? ['NUMBER_MISMATCH' as const] : [])]
  return {
    id: m.id,
    consultationId: m.consultation_id,
    senderRole: m.sender_role,
    senderId: m.sender_id,
    originalText: m.original_text,
    originalLang: m.original_lang,
    translatedText: m.translated_text,
    translatedLang: m.translated_lang,
    translationStatus: m.translation_status,
    flags,
    clientMsgId: m.client_msg_id ?? null,
    createdAt: m.created_at,
  }
}
const emptyConditions = (): Conversation['conditions'] => ({
  procedureCode: null,
  areas: [],
  dateFrom: null,
  dateTo: null,
  budgetMaxKrw: null,
  consultLanguage: null,
  sortBy: 'REVIEW_COUNT',
})
function toConversation(c: ConvRow, locale: Locale, withMessages = true): Conversation {
  const h = c.selected_hospital_id ? hospitals.find((x) => x.id === c.selected_hospital_id) : null
  return {
    id: c.id,
    mode: c.mode,
    hospital: h ? { id: h.id, name: pickName(h, locale) } : null,
    parentConversationId: c.parent_conversation_id,
    consultationId: c.consultation_id,
    conditions: c.conditions ?? emptyConditions(),
    topic: c.topic ?? null,
    createdAt: c.created_at,
    messages: withMessages ? (c.messages ?? []) : (null as unknown as ConversationMessage[]),
  }
}

// ─── AI 시나리오 문구 (en/zh/ja/ko) ───────────────────────────
const L = (loc: Locale, m: Record<'en' | 'ko' | 'zh' | 'ja', string>) => m[loc] ?? m.en
const TXT = {
  found: { en: 'I found clinics that match. Sorted by number of reviews.', ko: '조건에 맞는 병원을 찾았어요. 리뷰가 많은 순서로 보여 드릴게요.', zh: '找到了符合条件的医院，按评价数量排序。', ja: '条件に合う病院が見つかりました。口コミが多い順に表示します。' },
  none: { en: 'No clinics match these conditions. Changing one condition gives results.', ko: '조건에 맞는 병원을 찾지 못했어요. 조건을 하나 바꾸면 결과가 있어요.', zh: '没有找到符合条件的医院。修改一个条件就会有结果。', ja: '条件に合う病院が見つかりませんでした。条件を1つ変えると結果があります。' },
  relaxBudget: { en: 'Budget up to ₩900k', ko: '예산 ~90만 원으로', zh: '预算放宽到 90 万韩元', ja: '予算を90万ウォンまでに' },
  relaxArea: { en: 'Budget ₩1M · add Sinsa', ko: '예산 ~100만 원 · 지역에 신사 추가', zh: '预算 100 万 · 增加新沙', ja: '予算100万 · 新沙を追加' },
  trip: { en: 'If you have the procedure on 10/21, expected recovery is the same day as your departure (10/26). Want me to look for earlier times?', ko: '10/21에 시술하면 회복 예상일이 출국일(10/26)과 같아 여유가 없어요. 더 이른 시간도 찾아볼까요?', zh: '如果 10/21 做手术，预计恢复日与出境日（10/26）相同，没有富余。要不要找更早的时间？', ja: '10/21に施術すると回復予定日が出国日（10/26）と同じで余裕がありません。もっと早い時間も探しましょうか？' },
  memory: { en: 'Should I remember your preferred area Gangnam · Myeongdong for next time?', ko: '선호 지역 강남·명동을 기억해 둘까요? 다음 상담에서 다시 묻지 않아요', zh: '要记住您偏好的地区江南·明洞吗？下次咨询就不用再问了', ja: '希望エリアの江南・明洞を覚えておきましょうか？次回の相談で聞き直しません' },
  agent: { en: 'Hello! Ask me about doctors, prices or available times at this clinic.', ko: '안녕하세요! 이 병원의 의료진·가격·예약 가능 시간을 물어보세요.', zh: '您好！可以询问本院的医生、价格和可约时间。', ja: 'こんにちは！この病院の医師・価格・予約可能な時間について聞いてください。' },
  askBook: { en: 'Shall I request this booking with the clinic?', ko: '아래 내용으로 병원에 예약을 요청할까요?', zh: '要按以下内容向医院提交预约吗？', ja: '以下の内容で病院に予約をリクエストしますか？' },
  booked: { en: 'I sent your request to the clinic. Feel free to ask more while you wait.', ko: '병원에 요청을 전달했어요. 기다리는 동안 궁금한 점을 더 물어보셔도 돼요.', zh: '已将请求转达给医院。等待期间可以继续提问。', ja: '病院にリクエストを送りました。お待ちの間、ほかの質問もどうぞ。' },
  summary: { en: 'I summarized our conversation. This summary goes to the counselor.', ko: '지금까지 나눈 대화를 요약했어요. 이 요약이 상담원에게 전달돼요.', zh: '已总结目前的对话，这份摘要会转给咨询师。', ja: 'これまでの会話を要約しました。この要約が相談員に届きます。' },
  handoff: { en: 'A counselor will join shortly. The AI pauses until then.', ko: '상담원 연결을 요청했어요. 상담원이 들어올 때까지 AI 답변은 멈춰요.', zh: '已请求连接咨询师，在咨询师加入前 AI 将暂停回答。', ja: '相談員への接続をリクエストしました。相談員が入室するまでAIは回答を止めます。' },
  cancelled: { en: 'Okay, I did not send it.', ko: '알겠어요. 요청하지 않았어요.', zh: '好的，没有提交。', ja: 'わかりました。リクエストしていません。' },
  opened: { en: 'Opening a chat with this clinic.', ko: '이 병원과의 대화창을 열었어요.', zh: '已打开与这家医院的对话。', ja: 'この病院とのチャットを開きました。' },
  askConcern: { en: 'What skin concerns do you have? Pick all that apply.\nI will share info on related procedures.', ko: '어떤 피부 고민이 있으세요? 해당하는 걸 모두 골라주세요.\n고른 고민과 관련된 시술 정보를 알려드려요.', zh: '您有哪些皮肤困扰？请选择所有符合的项。\n我会介绍相关项目的信息。', ja: 'どんな肌の悩みがありますか？当てはまるものをすべて選んでください。\n関連する施術の情報をお伝えします。' },
  askArea: { en: 'Which area would you like to visit: Gangnam, Myeongdong or Hongdae?', ko: '어느 지역이 편하세요? 강남, 명동, 홍대 중에서 골라 주세요.', zh: '您想去哪个区域？江南、明洞还是弘大？', ja: 'どのエリアがご希望ですか？江南・明洞・弘大から選んでください。' },
  areaChoices: { en: 'Gangnam|Myeongdong|Hongdae', ko: '강남|명동|홍대', zh: '江南|明洞|弘大', ja: '江南|明洞|弘大' },
  topic: { en: 'Sure. Tell me what you would like to know.', ko: '좋아요. 궁금한 점을 말씀해 주세요.', zh: '好的，请告诉我您想了解的内容。', ja: 'わかりました。知りたいことを教えてください。' },
  procs: { en: 'Here are {n} related procedures.\nTimes and prices are based on registered clinic info.', ko: '관련 시술 {n}가지예요.\n시간·가격은 등록된 병원 정보 기준이에요.', zh: '相关项目共 {n} 个。\n时间·价格以医院登记的信息为准。', ja: '関連する施術は{n}つです。\n時間・価格は登録された病院情報に基づきます。' },
  saved: { en: 'Saved. I will use it next time.', ko: '기억해 둘게요. 다음 상담부터 반영할게요.', zh: '已保存，下次咨询会使用。', ja: '保存しました。次回から反映します。' },
}
const SOURCES = [
  { docId: 'GUIDE_DOUBLE_EYELID_NONINCISION', title: 'Non-incisional Double Eyelid — Patient Guide', section: 'Recovery & downtime', uri: 'doc://GUIDE_DOUBLE_EYELID_NONINCISION#recovery-downtime', snippet: 'Swelling usually settles within about a week; most people return to daily activities in a few days.' },
  { docId: 'COMMON_PAYMENT_VAT', title: 'Payment and VAT for international patients', section: 'VAT refund', uri: 'doc://COMMON_PAYMENT_VAT#vat-refund', snippet: 'Some cosmetic procedures qualify for a VAT refund for foreign patients when conditions are met.' },
]
const PROC_WORDS: [ProcedureCode, RegExp][] = [
  ['DOUBLE_EYELID_INCISION', /절개|incision|全切|切開/i],
  ['DOUBLE_EYELID_NONINCISION', /쌍꺼풀|매몰|eyelid|双眼皮|二重/i],
  ['RHINOPLASTY', /코|rhino|nose|隆鼻|鼻/i],
  ['JAW_BOTOX', /보톡스|botox|瘦脸|ボトックス/i],
  ['ULTHERAPY', /울쎄라|ulthera|リフト|超声刀/i],
  ['PICO_TONING', /피코|pico|皮秒|ピコ/i],
  ['REJURAN', /리쥬란|rejuran|丽珠兰|リジュラン/i],
]
// ponytail: 고민→시술 매핑은 mock 전용 하드코딩. 실제는 backend procedure_concerns 테이블 (docs/api/c4t-topic-concern.md)
const CONCERN_PROCS: Record<SkinConcern, ProcedureCode[]> = {
  PIGMENTATION: ['PICO_TONING'],
  PORES: ['REJURAN'],
  ACNE_SCAR: ['REJURAN'],
  WRINKLE_FIRMNESS: ['ULTHERAPY', 'THERMAGE', 'FOREHEAD_BOTOX'],
  TONE_TEXTURE: ['PICO_TONING', 'REJURAN'],
  REDNESS: ['PICO_TONING'],
  FACE_CONTOUR: ['SHURINK', 'JAW_BOTOX'],
}
const CONCERN_WORDS: [SkinConcern, RegExp][] = [
  ['PIGMENTATION', /기미|잡티|melasma|spot|色斑|シミ/i],
  ['PORES', /모공|pore|毛孔|毛穴/i],
  ['ACNE_SCAR', /여드름|흉터|acne|scar|痘|ニキビ/i],
  ['WRINKLE_FIRMNESS', /주름|탄력|wrinkle|firm|皱纹|シワ/i],
  ['TONE_TEXTURE', /피부톤|피부결|tone|texture|肤色|キメ/i],
  ['REDNESS', /홍조|redness|泛红|赤み/i],
  ['FACE_CONTOUR', /얼굴 ?라인|face ?line|轮廓|フェイスライン/i],
]
function procedureInfos(concerns: SkinConcern[], loc: Locale): ProcedureInfo[] {
  const codes = [...new Set(concerns.flatMap((c) => CONCERN_PROCS[c]))]
  return codes.map((code) => {
    const p = procedures.find((x) => x.code === code)!
    const prices = priceOptions.filter((o) => o.procedure_code === code).map((o) => o.price_krw)
    return {
      procedureCode: code,
      name: pickName(p, loc),
      description: loc === 'ko' ? p.description_ko : p.description_en,
      concerns: concerns.filter((c) => CONCERN_PROCS[c].includes(code)),
      durationMin: p.duration_min,
      downtimeDays: p.downtime_days,
      minPriceKrw: prices.length ? Math.min(...prices) : null,
      maxPriceKrw: prices.length ? Math.max(...prices) : null,
    }
  })
}

function sse(events: [SseEventName, unknown][]) {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      for (let i = 0; i < events.length; i++) {
        await delay(events[i][0] === 'TOKEN' ? 60 : 380)
        controller.enqueue(encoder.encode(`id: ${i + 1}\nevent: ${events[i][0]}\ndata: ${JSON.stringify(events[i][1])}\n\n`))
      }
      controller.close()
    },
  })
  return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' } })
}
const tokens = (text: string): [SseEventName, unknown][] => text.match(/.{1,6}/gsu)!.map((t) => ['TOKEN', { text: t }])
/** 승인 대기 앞의 안내 문구: DONE 없이 대화 기록에만 남긴다 (APPROVAL_REQUIRED 가 종료 이벤트) */
function record(conv: ConvRow, text: string) {
  conv.messages!.push({ role: 'assistant', text, sources: [], cards: [], createdAt: nowIso() })
}
function done(conv: ConvRow, answer: string, extra: Partial<ConversationMessage> & { suggestions?: string[] } = {}): [SseEventName, unknown] {
  conv.messages!.push({ role: 'assistant', text: answer, sources: extra.sources ?? [], cards: extra.cards ?? [], procedures: extra.procedures, createdAt: nowIso() })
  return ['DONE', { answer, sources: extra.sources ?? [], suggestions: extra.suggestions ?? [] }]
}

function aiStream(task: TaskRow, request: Request) {
  const loc = localeOf(request)
  const user = users.find((u) => u.id === task.userId)!
  const conv = convRows.find((c) => c.id === task.conversationId)!
  const text = task.message ?? ''
  const action = task.action as { type: string; hospitalId?: number; fields?: unknown; topic?: ConsultTopic; concerns?: SkinConcern[] } | null
  const ev: [SseEventName, unknown][] = [['STATUS', { status: 'RUNNING' }]]

  // 승인 후 재개
  if (task.phase === 'resume') {
    const pending = task.pendingAction!
    if (!task.approved) return sse([...ev, ...tokens(L(loc, TXT.cancelled)), done(conv, L(loc, TXT.cancelled))])
    if (pending.action === 'CREATE_RESERVATION') {
      const a = pending.args as { slotId: number; procedureCode: string; priceOptionId: number }
      const r: ResRow = {
        id: nextId(),
        user_id: user.id,
        hospital_id: conv.selected_hospital_id!,
        slot_id: a.slotId,
        procedure_code: a.procedureCode,
        status: 'PENDING',
        source: 'AI',
        customer_note: (task.editedArgs?.note as string | undefined) ?? null,
        reject_reason: null,
        alternative_slot_ids: [],
        hold_expires_at: new Date(Date.now() + 30 * 60_000 + 9 * 3600_000).toISOString().replace('Z', '+09:00').replace(/\.\d{3}/, ''),
        created_at: nowIso(),
        decided_at: null,
        price_option_id: a.priceOptionId,
      }
      resRows.push(r)
      notify(adminsOf(r.hospital_id), 'RESERVATION_REQUESTED', { reservationId: r.id })
      audit({ id: user.id, role: 'CUSTOMER' }, 'RESERVATION_CREATED', `reservation ${r.id}`)
      return sse([...ev, ['TOOL_START', { tool: 'business_create_reservation_request', label: '…' }], ['TOOL_END', { tool: 'business_create_reservation_request', ok: true }], ...tokens(L(loc, TXT.booked)), done(conv, L(loc, TXT.booked))])
    }
    // REQUEST_CONSULTATION
    const card = pending.args.summaryCard as Row
    const c: ConsRow = {
      id: nextId(),
      user_id: user.id,
      hospital_id: conv.selected_hospital_id!,
      counselor_id: null,
      conversation_id: conv.id,
      status: 'WAITING',
      customer_locale: user.locale as Locale,
      summary_card: card,
      summary_card_ko: { ...card, procedure_name: card.procedure_name, language: user.locale },
      created_at: nowIso(),
    }
    consRows.push(c)
    conv.mode = 'HUMAN'
    conv.consultation_id = c.id
    notify(counselorsOf(c.hospital_id), 'CONSULTATION_REQUESTED', { consultationId: c.id })
    return sse([...ev, ...tokens(L(loc, TXT.handoff)), ['MODE_CHANGED', { mode: 'HUMAN', consultationId: c.id }], done(conv, L(loc, TXT.handoff))])
  }

  if (action?.type === 'SELECT_HOSPITAL') {
    const child: ConvRow = {
      id: crypto.randomUUID(),
      user_id: user.id,
      parent_conversation_id: conv.id,
      mode: 'HOSPITAL',
      selected_hospital_id: action.hospitalId!,
      consultation_id: null,
      created_at: nowIso(),
      conditions: conv.conditions,
      messages: [{ role: 'assistant', text: L(loc, TXT.agent), sources: [], cards: [], createdAt: nowIso() }],
    }
    convRows.push(child)
    return sse([...ev, ...tokens(L(loc, TXT.opened)), ['CONVERSATION_OPENED', { conversationId: child.id, hospitalId: action.hospitalId }], done(conv, L(loc, TXT.opened))])
  }
  if (action?.type === 'SAVE_PROFILE') return sse([...ev, ...tokens(L(loc, TXT.saved)), done(conv, L(loc, TXT.saved))])
  // C4-T 상담 주제 선택 · 피부 고민 → 관련 시술 정보
  if (action?.type === 'SELECT_TOPIC') {
    conv.topic = action.topic!
    // 병원 찾기는 지역을 되묻고 선택지 칩(DONE.suggestions)을 함께 보낸다
    if (action.topic === 'HOSPITAL_SEARCH') {
      const answer = L(loc, TXT.askArea)
      return sse([...ev, ...tokens(answer), done(conv, answer, { suggestions: L(loc, TXT.areaChoices).split('|') })])
    }
    const answer = L(loc, action.topic === 'SKIN_CONCERN' ? TXT.askConcern : TXT.topic)
    return sse([...ev, ...tokens(answer), done(conv, answer)])
  }
  const concerns = action?.type === 'FIND_BY_CONCERNS' ? action.concerns! : conv.topic === 'SKIN_CONCERN' ? CONCERN_WORDS.filter(([, re]) => re.test(text)).map(([c]) => c) : []
  if (concerns.length) {
    const procs = procedureInfos(concerns, loc)
    const answer = L(loc, TXT.procs).replace('{n}', String(procs.length))
    ev.push(['TOOL_START', { tool: 'business_find_procedures_by_concern', label: '…' }], ['TOOL_END', { tool: 'business_find_procedures_by_concern', ok: true }])
    return sse([...ev, ['PROCEDURE_INFO', { procedures: procs }], ...tokens(answer), done(conv, answer, { procedures: procs })])
  }
  if (/실패|fail|失败|失敗/i.test(text)) {
    Object.assign(task, { status: 'FAILED', error: { code: 'AI_UNAVAILABLE', message: 'agent unavailable (mock)' }, finishedAt: nowIso() })
    return sse([...ev, ['FAILED', { code: 'AI_UNAVAILABLE', message: 'agent unavailable', traceId: task.id }]])
  }

  // 병원 대화
  if (conv.mode === 'HOSPITAL') {
    const h = hospitals.find((x) => x.id === conv.selected_hospital_id)!
    if (/예약|book|预约|予約/i.test(text)) {
      const code = (conv.conditions?.procedureCode ?? priceOptions.find((o) => o.hospital_id === h.id)!.procedure_code) as ProcedureCode
      const opt = priceOptions.find((o) => o.hospital_id === h.id && o.procedure_code === code) ?? priceOptions.find((o) => o.hospital_id === h.id)!
      const slot = slots.find((s) => s.hospital_id === h.id && s.status === 'AVAILABLE' && new Date(s.start_at).getTime() > Date.now() + 86400_000)!
      const doc = doctors.find((d) => d.id === slot.doctor_id)
      const proc = procedures.find((p) => p.code === opt.procedure_code)!
      const when = new Intl.DateTimeFormat(loc, { timeZone: 'Asia/Seoul', month: 'short', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(slot.start_at))
      const price = loc === 'ko' ? `${opt.price_krw.toLocaleString('ko-KR')}원` : new Intl.NumberFormat(loc, { style: 'currency', currency: 'KRW' }).format(opt.price_krw)
      const label = (m: Record<string, string>) => L(loc, m as never)
      const pending: PendingAction = {
        action: 'CREATE_RESERVATION',
        display: {
          title: label({ en: 'Confirm booking request', ko: '예약 요청 확인', zh: '确认预约请求', ja: '予約リクエストの確認' }),
          rows: [
            { label: label({ en: 'Clinic', ko: '병원', zh: '医院', ja: '病院' }), value: pickName(h, loc) },
            { label: label({ en: 'Date', ko: '일시', zh: '时间', ja: '日時' }), value: when },
            { label: label({ en: 'Doctor', ko: '의료진', zh: '医生', ja: '医師' }), value: doc ? (loc === 'ko' ? doc.name_ko : doc.name_en) : '—' },
            { label: label({ en: 'Procedure', ko: '시술', zh: '项目', ja: '施術' }), value: `${pickName(proc, loc)} · ${opt.product}` },
            { label: label({ en: 'Price', ko: '가격', zh: '价格', ja: '価格' }), value: `${price} · ${opt.vat_included ? 'VAT ✓' : 'VAT ✗'}` },
          ],
          notice: label({
            en: 'The booking is confirmed once the clinic approves. We hold this time for 30 minutes. No payment needed.',
            ko: '병원이 승인하면 예약이 확정돼요. 요청 후 30분 동안 이 시간을 잡아두고, 결제는 필요 없어요.',
            zh: '医院确认后预约生效。提交后为您保留该时段 30 分钟，无需付款。',
            ja: '病院が承認すると予約が確定します。30分間この時間を確保します。お支払いは不要です。',
          }),
        },
        args: { slotId: slot.id, procedureCode: opt.procedure_code, priceOptionId: opt.id, note: null },
        editable: ['note'],
      }
      task.pendingAction = pending
      task.status = 'WAITING_APPROVAL'
      record(conv, L(loc, TXT.askBook))
      return sse([...ev, ...tokens(L(loc, TXT.askBook)), ['APPROVAL_REQUIRED', pending]])
    }
    if (/상담원|상담사|counselor|human|咨询师|相談員/i.test(text)) {
      const proc = procedures.find((p) => p.code === (conv.conditions?.procedureCode ?? 'DOUBLE_EYELID_NONINCISION'))!
      const qs = L(loc, {
        en: 'Is anesthesia included in the price?|How many days does swelling last?|Can I get aftercare before I fly home?',
        ko: '마취비도 가격에 포함되나요?|붓기는 며칠 정도 가나요?|출국 전에 사후 관리를 받을 수 있나요?',
        zh: '价格包含麻醉费吗？|肿胀大概持续几天？|回国前能做术后护理吗？',
        ja: '麻酔代も価格に含まれますか？|腫れは何日くらい続きますか？|帰国前にアフターケアを受けられますか？',
      }).split('|')
      const label = (m: Record<string, string>) => L(loc, m as never)
      const pending: PendingAction = {
        action: 'REQUEST_CONSULTATION',
        display: {
          title: label({ en: 'Consultation summary', ko: '상담 요청 요약', zh: '咨询请求摘要', ja: '相談リクエストの要約' }),
          rows: [
            { label: label({ en: 'Procedure', ko: '시술', zh: '项目', ja: '施術' }), value: pickName(proc, loc) },
            { label: label({ en: 'Dates', ko: '희망일', zh: '希望日期', ja: '希望日' }), value: '10/21 – 10/23' },
            { label: label({ en: 'Stay', ko: '체류', zh: '停留', ja: '滞在' }), value: '10/20 – 10/26 · 7' },
            { label: label({ en: 'Budget', ko: '예산', zh: '预算', ja: '予算' }), value: '≤ 2,000,000 KRW' },
            { label: label({ en: 'Language', ko: '언어', zh: '语言', ja: '言語' }), value: label({ en: 'English', ko: '한국어', zh: '中文', ja: '日本語' }) },
          ],
          notice: '',
        },
        args: { summaryCard: { procedure_name: pickName(proc, loc), preferred_dates: ['2026-10-21', '2026-10-23'], concerns: qs, questions: qs, stay_days: 7, budget: '≤ 2,000,000 KRW', language: user.locale } },
        editable: [],
      }
      task.pendingAction = pending
      task.status = 'WAITING_APPROVAL'
      record(conv, L(loc, TXT.summary))
      return sse([...ev, ...tokens(L(loc, TXT.summary)), ['APPROVAL_REQUIRED', pending]])
    }
    const answer = L(loc, TXT.agent)
    return sse([...ev, ['TOOL_START', { tool: 'business_list_doctors', label: '…' }], ['TOOL_END', { tool: 'business_list_doctors', ok: true }], ...tokens(answer), done(conv, answer, { sources: [SOURCES[0]] })])
  }

  // 메인 대화
  const code = (PROC_WORDS.find(([, re]) => re.test(text))?.[0] ?? conv.conditions?.procedureCode ?? 'DOUBLE_EYELID_NONINCISION') as ProcedureCode
  const conditions = {
    ...(conv.conditions ?? emptyConditions()),
    procedureCode: code,
    areas: /명동|myeongdong|明洞/i.test(text) ? ['GANGNAM', 'MYEONGDONG'] : (conv.conditions?.areas.length ? conv.conditions.areas : ['GANGNAM']),
    dateFrom: '2026-10-20',
    dateTo: '2026-10-26',
    budgetMaxKrw: /50만|500k|500,000/i.test(text) ? 500000 : 2000000,
    consultLanguage: (user.locale === 'ko' ? 'en' : user.locale) as Locale,
  } as Conversation['conditions']
  conv.conditions = conditions
  ev.push(['CONDITIONS', { conditions, missing: [] }])
  const searching = L(loc, { en: 'Searching clinics…', ko: '조건에 맞는 병원 찾는 중…', zh: '正在搜索医院…', ja: '病院を検索中…' })
  ev.push(['TOOL_START', { tool: 'business_search_hospitals', label: searching }], ['TOOL_END', { tool: 'business_search_hospitals', ok: true }])

  if (conditions.budgetMaxKrw === 500000) {
    ev.push(['RESULT_CARDS', { cards: [], relaxOptions: [
      { option: 'BUDGET_900K', label: L(loc, TXT.relaxBudget), expectedCount: 1 },
      { option: 'BUDGET_1M_SINSA', label: L(loc, TXT.relaxArea), expectedCount: 3 },
    ] }])
    return sse([...ev, ...tokens(L(loc, TXT.none)), done(conv, L(loc, TXT.none))])
  }
  if (/일정|trip|schedule|行程|日程/i.test(text)) {
    const h = hospitals[0]
    const slot = slots.find((s) => s.hospital_id === h.id && s.status === 'AVAILABLE' && s.start_at.startsWith('2026-10-21'))!
    ev.push(['TOOL_START', { tool: 'business_plan_trip', label: '…' }], ['TOOL_END', { tool: 'business_plan_trip', ok: true }])
    ev.push(['TRIP_PLAN', { arrivalDate: '2026-10-20', departureDate: '2026-10-26', summary: '', plans: [{ hospitalId: h.id, hospitalName: pickName(h, loc), slot: toSlot(slot), procedureCode: code, downtimeDays: 5, recoveryEndDate: '2026-10-26', bufferDays: 0, feasible: false, reason: 'RECOVERY_AFTER_DEPARTURE' }] }])
    ev.push(['MEMORY_PROPOSAL', { fields: { preferredAreas: ['GANGNAM', 'MYEONGDONG'], budgetMaxKrw: null, interestedProcedures: [code], consultLanguage: null, skinConcerns: null, updatedAt: null }, message: L(loc, TXT.memory) }])
    return sse([...ev, ...tokens(L(loc, TXT.trip)), done(conv, L(loc, TXT.trip))])
  }
  const cards = hospitals
    .filter((h) => conditions.areas.includes(h.area_code as never))
    .map((h) => toHospitalCard(h, loc, code))
    .filter((c) => c.minPriceKrw != null && c.minPriceKrw <= conditions.budgetMaxKrw!)
    .sort((a, b) => b.reviewCount - a.reviewCount)
    .slice(0, 4)
  ev.push(['RESULT_CARDS', { cards, relaxOptions: [] }])
  return sse([...ev, ...tokens(L(loc, TXT.found)), done(conv, L(loc, TXT.found), { sources: SOURCES, cards })])
}

// ─── 핸들러 ──────────────────────────────────────────────────
const auth = (request: Request) => me(request) ?? null
const deny = () => error(401, 'UNAUTHENTICATED', 'Login required')

export const appHandlers = [
  // 인증 · 내 정보
  http.post(`${API}/auth/signup`, async ({ request }) => {
    const b = (await request.json()) as Row
    if (users.some((u) => u.email === b.email)) return error(409, 'EMAIL_DUPLICATED', 'This email is already registered')
    const u = { id: nextId(), email: String(b.email), password: String(b.password), name: String(b.name), locale: String(b.locale), role: 'CUSTOMER', hospital_id: null, nationality: b.nationality }
    users.push(u as never)
    return HttpResponse.json(toUserSummary(u as never), { status: 201 })
  }),
  http.get(`${API}/me`, ({ request }) => {
    const u = auth(request)
    return u ? HttpResponse.json({ ...toUserSummary(u), email: u.email }) : deny()
  }),
  http.patch(`${API}/me`, async ({ request }) => {
    const u = auth(request)
    if (!u) return deny()
    u.locale = String(((await request.json()) as Row).locale)
    return HttpResponse.json({ ...toUserSummary(u), email: u.email })
  }),

  // 탐색 보조
  http.get(`${API}/hospitals/:id/reviews`, ({ request, params }) => {
    if (!auth(request)) return deny()
    const url = new URL(request.url)
    return HttpResponse.json(page(reviews.filter((r) => r.hospital_id === Number(params.id) && !r.hidden).map((r) => toReview(r, localeOf(request))), url))
  }),
  http.post(`${API}/hospitals/compare`, async ({ request }) => {
    if (!auth(request)) return deny()
    const b = (await request.json()) as { hospitalIds: number[]; procedureCode: ProcedureCode }
    const loc = localeOf(request)
    const columns = b.hospitalIds.flatMap((id) => {
      const h = hospitals.find((x) => x.id === id)
      if (!h) return []
      const opts = priceOptions.filter((o) => o.hospital_id === id && o.procedure_code === b.procedureCode)
      const card = toHospitalCard(h, loc, b.procedureCode)
      return [{ hospital: card, options: opts.map((o) => toPriceOption(o, loc)), earliestSlotAt: card.earliestSlotAt, verifiedAt: opts.find((o) => o.verified_at)?.verified_at ?? null }]
    })
    return HttpResponse.json({ procedureCode: b.procedureCode, columns })
  }),
  http.get(`${API}/docs/:docId`, ({ params, request }) => {
    const entry = Object.entries(ragDocs).find(([path]) => path.endsWith(`/${params.docId}.md`))
    if (!entry) return error(404, 'NOT_FOUND', 'Document not found', { resource: 'doc' })
    const raw = entry[1]
    const title = raw.match(/^title:\s*"?(.+?)"?$/m)?.[1] ?? String(params.docId)
    const want = new URL(request.url).searchParams.get('section')?.toLowerCase().replace(/[^a-z]/g, '') ?? ''
    const parts = raw.split(/^## /m).slice(1)
    const sec = parts.find((p) => p.split('\n')[0].toLowerCase().replace(/[^a-z]/g, '').startsWith(want.slice(0, 8))) ?? parts[0] ?? ''
    return HttpResponse.json({ uri: `doc://${params.docId}`, docId: params.docId, title, section: sec.split('\n')[0], body: sec.split('\n').slice(1).join('\n').trim(), meta: {} })
  }),

  // 예약 (고객)
  http.get(`${API}/reservations/me`, ({ request }) => {
    const u = auth(request)
    if (!u) return deny()
    const loc = localeOf(request)
    return HttpResponse.json(resRows.filter((r) => r.user_id === u.id).sort((a, b) => b.created_at.localeCompare(a.created_at)).map((r) => toReservation(r, loc, false)))
  }),
  http.get(`${API}/reservations/:id`, ({ request, params }) => {
    const u = auth(request)
    if (!u) return deny()
    const r = resRows.find((x) => x.id === Number(params.id))
    if (!r) return error(404, 'NOT_FOUND', 'Reservation not found', { resource: 'reservation' })
    const staff = u.role !== 'CUSTOMER'
    if ((!staff && r.user_id !== u.id) || (u.role === 'HOSPITAL_ADMIN' && u.hospital_id !== r.hospital_id)) return error(403, 'ACCESS_DENIED', 'Access denied')
    return HttpResponse.json(toReservation(r, localeOf(request), staff))
  }),
  http.post(`${API}/reservations`, async ({ request }) => {
    const u = auth(request)
    if (!u) return deny()
    const key = request.headers.get('Idempotency-Key')
    if (!key) return error(400, 'VALIDATION_FAILED', 'Idempotency-Key required')
    const dup = resRows.find((r) => r.idempotency_key === key)
    if (dup) return HttpResponse.json(toReservation(dup, localeOf(request), false))
    const b = (await request.json()) as { hospitalId: number; slotId: number; procedureCode: string; priceOptionId: number | null; note: string | null }
    const slot = slots.find((s) => s.id === b.slotId)
    const taken = resRows.some((r) => r.slot_id === b.slotId && (r.status === 'PENDING' || r.status === 'CONFIRMED'))
    if (!slot || slot.status !== 'AVAILABLE' || taken) {
      const alts = slots.filter((s) => s.hospital_id === b.hospitalId && s.status === 'AVAILABLE' && s.id !== b.slotId && s.start_at >= (slot?.start_at ?? '')).slice(0, 3).map(toSlot)
      return error(409, 'SLOT_UNAVAILABLE', 'This time was just taken', { alternatives: alts })
    }
    const r: ResRow = {
      id: nextId(),
      user_id: u.id,
      hospital_id: b.hospitalId,
      slot_id: b.slotId,
      procedure_code: b.procedureCode,
      status: 'PENDING',
      source: 'DIRECT',
      customer_note: b.note,
      reject_reason: null,
      alternative_slot_ids: [],
      hold_expires_at: new Date(Date.now() + 30 * 60_000 + 9 * 3600_000).toISOString().replace('Z', '+09:00').replace(/\.\d{3}/, ''),
      created_at: nowIso(),
      decided_at: null,
      price_option_id: b.priceOptionId,
      idempotency_key: key,
    }
    resRows.push(r)
    notify(adminsOf(r.hospital_id), 'RESERVATION_REQUESTED', { reservationId: r.id })
    audit({ id: u.id, role: u.role }, 'RESERVATION_CREATED', `reservation ${r.id}`)
    return HttpResponse.json(toReservation(r, localeOf(request), false), { status: 201 })
  }),
  http.post(`${API}/reservations/:id/cancel`, ({ request, params }) => {
    const u = auth(request)
    if (!u) return deny()
    const r = resRows.find((x) => x.id === Number(params.id) && x.user_id === u.id)
    if (!r) return error(403, 'ACCESS_DENIED', 'Access denied')
    if (r.status !== 'PENDING' && r.status !== 'CONFIRMED') return error(409, 'INVALID_STATE_TRANSITION', 'Cannot cancel', { from: r.status, to: 'CANCELLED' })
    r.status = 'CANCELLED'
    hideReviewOf(r.id)
    notify(adminsOf(r.hospital_id), 'RESERVATION_CANCELLED', { reservationId: r.id })
    return HttpResponse.json(toReservation(r, localeOf(request), false))
  }),
  http.post(`${API}/reservations/:id/accept-alternative`, async ({ request, params }) => {
    const u = auth(request)
    if (!u) return deny()
    const r = resRows.find((x) => x.id === Number(params.id) && x.user_id === u.id)
    const { slotId } = (await request.json()) as { slotId: number }
    if (!r || r.status !== 'REJECTED' || !r.alternative_slot_ids.includes(slotId)) return error(409, 'INVALID_STATE_TRANSITION', 'Not allowed')
    const n: ResRow = { ...r, id: nextId(), slot_id: slotId, status: 'PENDING', reject_reason: null, alternative_slot_ids: [], created_at: nowIso(), decided_at: null, hold_expires_at: new Date(Date.now() + 30 * 60_000 + 9 * 3600_000).toISOString().replace('Z', '+09:00').replace(/\.\d{3}/, '') }
    resRows.push(n)
    notify(adminsOf(n.hospital_id), 'RESERVATION_REQUESTED', { reservationId: n.id })
    return HttpResponse.json(toReservation(n, localeOf(request), false), { status: 201 })
  }),
  http.post(`${API}/reservations/:id/review`, async ({ request, params }) => {
    const u = auth(request)
    if (!u) return deny()
    const r = resRows.find((x) => x.id === Number(params.id) && x.user_id === u.id)
    if (!r) return error(403, 'ACCESS_DENIED', 'Access denied')
    if (r.status !== 'CONFIRMED') return error(409, 'REVIEW_NOT_ALLOWED', 'Reviews can be written only for confirmed reservations.', { status: r.status })
    if (reviews.some((x) => x.reservation_id === r.id)) return error(409, 'REVIEW_ALREADY_EXISTS', 'You have already written a review for this reservation.')
    const { rating, content } = (await request.json()) as { rating: number; content: string }
    const text = (content ?? '').trim()
    if (!(rating >= 1 && rating <= 5) || text.length < 10 || text.length > 1000) {
      return error(400, 'VALIDATION_FAILED', 'Invalid review', { fields: [{ field: 'content', reason: 'size must be between 10 and 1000' }] })
    }
    const raw = u as unknown as { birth_date?: string; gender?: string; nationality?: string }
    const age = raw.birth_date ? new Date().getFullYear() - Number(raw.birth_date.slice(0, 4)) : 0
    const row = {
      id: Math.max(...reviews.map((x) => x.id)) + 1,
      hospital_id: r.hospital_id,
      procedure_code: r.procedure_code,
      rating,
      age_group: age >= 20 && age < 60 ? `${Math.floor(age / 10) * 10}s` : '',
      gender: raw.gender ?? '',
      reviewer_nationality: raw.nationality ?? null,
      lang: localeOf(request),
      content: text,
      created_at: nowIso(),
      reservation_id: r.id,
    }
    addReview(row)
    return HttpResponse.json(toReview(row), { status: 201 })
  }),

  // 알림
  http.get(`${API}/notifications`, ({ request }) => {
    const u = auth(request)
    if (!u) return deny()
    return HttpResponse.json(page(notifs.filter((n) => n.userId === u.id).map(({ userId: _u, ...n }) => n), new URL(request.url)))
  }),
  http.post(`${API}/notifications/read-all`, ({ request }) => {
    const u = auth(request)
    if (!u) return deny()
    notifs.filter((n) => n.userId === u.id).forEach((n) => (n.readAt ??= nowIso()))
    return new HttpResponse(null, { status: 204 })
  }),
  http.post(`${API}/notifications/:id/read`, ({ request, params }) => {
    const u = auth(request)
    const n = notifs.find((x) => x.id === Number(params.id))
    if (!u || !n || n.userId !== u.id) return error(403, 'ACCESS_DENIED', 'Access denied')
    n.readAt = nowIso()
    return new HttpResponse(null, { status: 204 })
  }),

  // 상담 · 채팅 (STOMP 대신 REST 폴백)
  http.get(`${API}/consultations/:id`, ({ request, params }) => {
    const u = auth(request)
    const c = consRows.find((x) => x.id === Number(params.id))
    if (!u || !c) return error(404, 'NOT_FOUND', 'Not found')
    return HttpResponse.json(toConsultation(c, u.role === 'COUNSELOR'))
  }),
  http.get(`${API}/consultations/:id/messages`, ({ request, params }) => {
    if (!auth(request)) return deny()
    const after = Number(new URL(request.url).searchParams.get('afterId') ?? 0)
    return HttpResponse.json(msgRows.filter((m) => m.consultation_id === Number(params.id) && m.id > after).map(toMessage))
  }),
  http.post(`${API}/consultations/:id/messages`, async ({ request, params }) => {
    const u = auth(request)
    const c = consRows.find((x) => x.id === Number(params.id))
    if (!u || !c) return deny()
    const b = (await request.json()) as { text: string; clientMsgId: string }
    const isCounselor = u.role === 'COUNSELOR'
    const m: MsgRow = {
      id: nextId(),
      consultation_id: c.id,
      sender_id: u.id,
      sender_role: isCounselor ? 'COUNSELOR' : 'CUSTOMER',
      original_text: b.text,
      original_lang: isCounselor ? 'ko' : c.customer_locale,
      translated_text: null,
      translated_lang: isCounselor ? c.customer_locale : 'ko',
      translation_status: 'PENDING',
      flags: /\d/.test(b.text) && !isCounselor ? ['NUMBER_MISMATCH'] : [],
      client_msg_id: b.clientMsgId,
      created_at: nowIso(),
    }
    msgRows.push(m)
    // 가짜 번역 워커: 1초 뒤 DONE (실제 번역은 agent 번역 워커)
    setTimeout(() => {
      m.translation_status = 'DONE'
      m.translated_text = `${b.text}`
    }, 1000)
    return HttpResponse.json(toMessage(m), { status: 201 })
  }),
  http.post(`${API}/consultations/:id/messages/:msgId/retry-translation`, ({ params }) => {
    const m = msgRows.find((x) => x.id === Number(params.msgId))
    if (!m || m.translation_status !== 'FAILED') return error(409, 'INVALID_STATE_TRANSITION', 'Not failed')
    m.translation_status = 'DONE'
    m.translated_text = m.original_text
    return new HttpResponse(null, { status: 202 })
  }),
  http.get(`${API}/counselor/consultations`, ({ request }) => {
    const u = auth(request)
    if (!u || u.role !== 'COUNSELOR') return error(403, 'ACCESS_DENIED', 'Access denied')
    const status = new URL(request.url).searchParams.get('status')
    return HttpResponse.json(
      consRows.filter((c) => c.hospital_id === u.hospital_id && (!status || c.status === status)).sort((a, b) => b.created_at.localeCompare(a.created_at)).map((c) => toConsultation(c, true)),
    )
  }),
  http.post(`${API}/counselor/consultations/:id/accept`, ({ request, params }) => {
    const u = auth(request)
    const c = consRows.find((x) => x.id === Number(params.id))
    if (!u || !c || c.hospital_id !== u.hospital_id) return error(403, 'ACCESS_DENIED', 'Access denied')
    if (c.status !== 'WAITING') return error(409, 'INVALID_STATE_TRANSITION', 'Not waiting')
    c.status = 'ACTIVE'
    c.counselor_id = u.id
    msgRows.push({ id: nextId(), consultation_id: c.id, sender_id: null, sender_role: 'SYSTEM', original_text: '상담원이 들어왔어요. 이제부터 사람이 답변해요', original_lang: 'ko', translated_text: null, translated_lang: null, translation_status: 'DONE', flags: [], created_at: nowIso() })
    notify([c.user_id], 'CONSULTATION_ACCEPTED', { consultationId: c.id, conversationId: c.conversation_id })
    return HttpResponse.json(toConsultation(c, true))
  }),
  http.post(`${API}/counselor/consultations/:id/close`, ({ request, params }) => {
    const u = auth(request)
    const c = consRows.find((x) => x.id === Number(params.id))
    if (!u || !c || c.hospital_id !== u.hospital_id) return error(403, 'ACCESS_DENIED', 'Access denied')
    c.status = 'CLOSED'
    const conv = convRows.find((x) => x.id === c.conversation_id)
    if (conv) conv.mode = 'HOSPITAL'
    notify([c.user_id], 'CONSULTATION_CLOSED', { consultationId: c.id })
    return HttpResponse.json(toConsultation(c, true))
  }),
  http.post(`${API}/consultations/:id/close`, ({ request, params }) => {
    const u = auth(request)
    const c = consRows.find((x) => x.id === Number(params.id))
    if (!u || !c || u.role !== 'CUSTOMER' || c.user_id !== u.id) return error(403, 'ACCESS_DENIED', 'Access denied')
    if (c.status !== 'WAITING' && c.status !== 'ACTIVE') return error(409, 'INVALID_STATE_TRANSITION', 'Invalid state transition')
    c.status = 'CLOSED'
    const conv = convRows.find((x) => x.id === c.conversation_id)
    if (conv) conv.mode = 'HOSPITAL'
    return HttpResponse.json(toConsultation(c, false))
  }),

  // 병원관리자
  http.get(`${API}/hospital-admin/dashboard`, ({ request }) => {
    const u = auth(request)
    if (!u || u.role !== 'HOSPITAL_ADMIN') return error(403, 'ACCESS_DENIED', 'Access denied')
    const mine = resRows.filter((r) => r.hospital_id === u.hospital_id)
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date())
    const slotDay = (r: ResRow) => slots.find((s) => s.id === r.slot_id)!.start_at.slice(0, 10)
    return HttpResponse.json({
      todayReservations: mine.filter((r) => (r.status === 'PENDING' || r.status === 'CONFIRMED') && slotDay(r) === today).length,
      pendingReservations: mine.filter((r) => r.status === 'PENDING').length,
      activeConsultations: consRows.filter((c) => c.hospital_id === u.hospital_id && c.status === 'ACTIVE').length,
      recentRequests: mine.filter((r) => r.status === 'PENDING').sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 5).map((r) => toReservation(r, 'ko', true)),
    })
  }),
  http.get(`${API}/hospital-admin/reservations`, ({ request }) => {
    const u = auth(request)
    if (!u || u.role !== 'HOSPITAL_ADMIN') return error(403, 'ACCESS_DENIED', 'Access denied')
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    const list = resRows
      .filter((r) => r.hospital_id === u.hospital_id && (!status || r.status === status))
      .map((r) => toReservation(r, 'ko', true))
      .sort((a, b) => a.slot.startAt.localeCompare(b.slot.startAt))
    return HttpResponse.json(page(list, url))
  }),
  http.post(`${API}/hospital-admin/reservations/:id/approve`, ({ request, params }) => {
    const u = auth(request)
    const r = resRows.find((x) => x.id === Number(params.id))
    if (!u || !r || r.hospital_id !== u.hospital_id) return error(403, 'ACCESS_DENIED', 'Access denied')
    if (r.status === 'PENDING' && r.hold_expires_at && new Date(r.hold_expires_at).getTime() < Date.now()) {
      r.status = 'EXPIRED'
      notify([r.user_id], 'RESERVATION_EXPIRED', { reservationId: r.id })
    }
    if (r.status !== 'PENDING') return error(409, 'INVALID_STATE_TRANSITION', 'Not pending', { from: r.status, to: 'CONFIRMED' })
    r.status = 'CONFIRMED'
    r.decided_at = nowIso()
    notify([r.user_id], 'RESERVATION_CONFIRMED', { reservationId: r.id })
    audit({ id: u.id, role: u.role }, 'RESERVATION_APPROVED', `reservation ${r.id}`)
    return HttpResponse.json(toReservation(r, 'ko', true))
  }),
  http.post(`${API}/hospital-admin/reservations/:id/reject`, async ({ request, params }) => {
    const u = auth(request)
    const r = resRows.find((x) => x.id === Number(params.id))
    if (!u || !r || r.hospital_id !== u.hospital_id) return error(403, 'ACCESS_DENIED', 'Access denied')
    const b = (await request.json()) as { reason: string; alternativeSlotIds: number[] }
    if (!b.reason?.trim()) return error(400, 'VALIDATION_FAILED', 'reason required', { fields: [{ field: 'reason', reason: 'must not be blank' }] })
    if (r.status !== 'PENDING') return error(409, 'INVALID_STATE_TRANSITION', 'Not pending', { from: r.status, to: 'REJECTED' })
    r.status = 'REJECTED'
    r.reject_reason = b.reason
    r.alternative_slot_ids = b.alternativeSlotIds.slice(0, 3)
    r.decided_at = nowIso()
    notify([r.user_id], 'RESERVATION_REJECTED', { reservationId: r.id })
    audit({ id: u.id, role: u.role }, 'RESERVATION_REJECTED', `reservation ${r.id}`)
    return HttpResponse.json(toReservation(r, 'ko', true))
  }),

  // 운영자
  http.get(`${API}/ops/ai-tasks`, ({ request }) => {
    const u = auth(request)
    if (!u || u.role !== 'OPERATOR') return error(403, 'ACCESS_DENIED', 'Access denied')
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    return HttpResponse.json(page(tasks.filter((x) => !status || x.status === status).map(({ action: _a, phase: _p, approved: _ap, editedArgs: _e, ...x }) => x), url))
  }),
  http.get(`${API}/ops/audit-logs`, ({ request }) => {
    const u = auth(request)
    if (!u || u.role !== 'OPERATOR') return error(403, 'ACCESS_DENIED', 'Access denied')
    return HttpResponse.json(page(audits, new URL(request.url)))
  }),

  // AI 대화 · 작업 · SSE (시나리오)
  http.get(`${API}/ai/conversations`, ({ request }) => {
    const u = auth(request)
    if (!u) return deny()
    return HttpResponse.json(convRows.filter((c) => c.user_id === u.id).sort((a, b) => b.created_at.localeCompare(a.created_at)).map((c) => toConversation(c, localeOf(request), false)))
  }),
  http.get(`${API}/ai/conversations/:id`, ({ request, params }) => {
    const u = auth(request)
    const c = convRows.find((x) => x.id === params.id)
    if (!u || !c) return error(404, 'NOT_FOUND', 'Conversation not found')
    if (c.user_id !== u.id) return error(403, 'ACCESS_DENIED', 'Access denied')
    return HttpResponse.json(toConversation(c, localeOf(request)))
  }),
  http.post(`${API}/ai/conversations`, async ({ request }) => {
    const u = auth(request)
    if (!u) return deny()
    const b = (await request.json()) as { hospitalId: number | null; parentConversationId: string | null }
    if (b.hospitalId) {
      const existing = convRows.find((c) => c.user_id === u.id && c.selected_hospital_id === b.hospitalId && c.mode !== 'MAIN')
      if (existing) return HttpResponse.json(toConversation(existing, localeOf(request)))
    }
    const parent = convRows.find((c) => c.id === b.parentConversationId)
    const c: ConvRow = {
      id: crypto.randomUUID(),
      user_id: u.id,
      parent_conversation_id: b.parentConversationId,
      mode: b.hospitalId ? 'HOSPITAL' : 'MAIN',
      selected_hospital_id: b.hospitalId,
      consultation_id: null,
      created_at: nowIso(),
      conditions: parent?.conditions ?? emptyConditions(),
      messages: b.hospitalId ? [{ role: 'assistant', text: L(localeOf(request), TXT.agent), sources: [], cards: [], createdAt: nowIso() }] : [],
    }
    convRows.push(c)
    return HttpResponse.json(toConversation(c, localeOf(request)), { status: 201 })
  }),
  http.post(`${API}/ai/tasks`, async ({ request }) => {
    const u = auth(request)
    if (!u) return deny()
    const b = (await request.json()) as { conversationId: string; message: string | null; action: unknown }
    const conv = convRows.find((c) => c.id === b.conversationId)
    if (!conv) return error(404, 'NOT_FOUND', 'Conversation not found')
    if (conv.mode === 'HUMAN') return error(409, 'INVALID_STATE_TRANSITION', 'Counselor is connected')
    if (b.message) conv.messages!.push({ role: 'user', text: b.message, sources: [], cards: [], createdAt: nowIso() })
    const task: TaskRow = {
      id: crypto.randomUUID(),
      conversationId: conv.id,
      status: 'QUEUED',
      answer: null,
      sources: [],
      pendingAction: null,
      error: null,
      createdAt: nowIso(),
      message: b.message,
      finishedAt: null,
      userId: u.id,
      action: b.action,
      phase: 'initial',
    }
    tasks.unshift(task)
    return HttpResponse.json({ taskId: task.id }, { status: 202 })
  }),
  http.post(`${API}/ai/tasks/:id/approval`, async ({ request, params }) => {
    const task = tasks.find((x) => x.id === params.id)
    if (!task || task.status !== 'WAITING_APPROVAL') return error(409, 'TASK_NOT_WAITING_APPROVAL', 'Not waiting for approval')
    const b = (await request.json()) as { approved: boolean; editedArgs: Row | null }
    Object.assign(task, { phase: 'resume', approved: b.approved, editedArgs: b.editedArgs, status: 'QUEUED' })
    return HttpResponse.json(task, { status: 202 })
  }),
  http.get(`${API}/ai/tasks/:id`, ({ params }) => {
    const task = tasks.find((x) => x.id === params.id)
    if (!task) return error(404, 'NOT_FOUND', 'Task not found')
    const { action: _a, phase: _p, approved: _ap, editedArgs: _e, userId: _u, ...x } = task
    return HttpResponse.json(x)
  }),
  http.get(`${API}/ai/tasks/:id/stream`, ({ request, params }) => {
    const task = tasks.find((x) => x.id === params.id)
    if (!task) return error(404, 'NOT_FOUND', 'Task not found')
    if (task.phase === 'initial' && task.status === 'WAITING_APPROVAL') return sse([['APPROVAL_REQUIRED', task.pendingAction]])
    const res = aiStream(task, request)
    if (task.status === 'QUEUED') Object.assign(task, { status: 'DONE', finishedAt: nowIso() })
    return res
  }),
]
