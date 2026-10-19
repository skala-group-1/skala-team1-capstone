/**
 * MSW 핸들러 — backend 없이 화면 흐름을 검증하기 위한 가짜 응답.
 * 구현된 것: 인증(login/refresh/logout/me), 시술 목록, 병원 검색·상세·슬롯, AI 대화·작업 + 가짜 SSE
 * 경로·바디는 「공통 계약서」·「API·이벤트 명세」와 같다. 실제 backend 로 바꾸려면 .env.local 에서 VITE_USE_MSW=false
 */
import { delay, http, HttpResponse } from 'msw'
import type {
  CreateTaskRequest,
  ErrorResponse,
  HospitalCard,
  Locale,
  LoginRequest,
  LoginResponse,
  Page,
  ProcedureCode,
  SortBy,
  SseEventName,
} from '@/types/contract'
import {
  hospitals,
  procedures,
  slots,
  toHospitalCard,
  toHospitalDetail,
  toProcedure,
  toSlot,
  toUserSummary,
  users,
} from './db'

const API = '/api'

// mock 세션: access token = "mock.<userId>", refresh 는 메모리 플래그 (실제는 HttpOnly 쿠키)
let refreshUserId: number | null = null

function error(status: number, code: ErrorResponse['code'], message: string, details: ErrorResponse['details'] = {}) {
  return HttpResponse.json<ErrorResponse>({ code, message, traceId: crypto.randomUUID(), details }, { status })
}

function currentUser(request: Request) {
  const token = request.headers.get('Authorization')?.replace('Bearer ', '')
  const id = token?.startsWith('mock.') ? Number(token.slice(5)) : NaN
  return users.find((u) => u.id === id) ?? null
}

function localeOf(request: Request): Locale {
  const l = request.headers.get('Accept-Language')?.slice(0, 2)
  return l === 'zh' || l === 'ja' || l === 'ko' ? l : 'en'
}

function loginResponse(userId: number): LoginResponse {
  const u = users.find((x) => x.id === userId)!
  return { accessToken: `mock.${u.id}`, expiresIn: 1800, user: toUserSummary(u) }
}

/** D-17: /api/auth/** 외에는 로그인 필수 */
function requireUser(request: Request) {
  return currentUser(request) ? null : error(401, 'UNAUTHENTICATED', 'Login required')
}

export const handlers = [
  // ─── 인증 (「인증·인가 설계」) ────────────────────────────────────────
  http.post(`${API}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as LoginRequest
    const u = users.find((x) => x.email === body.email && x.password === body.password)
    if (!u) return error(401, 'INVALID_CREDENTIALS', 'Invalid email or password')
    refreshUserId = u.id
    return HttpResponse.json(loginResponse(u.id))
  }),
  http.post(`${API}/auth/refresh`, () => {
    if (refreshUserId == null) return error(401, 'REFRESH_INVALID', 'Refresh token invalid')
    return HttpResponse.json(loginResponse(refreshUserId))
  }),
  http.post(`${API}/auth/logout`, () => {
    refreshUserId = null
    return new HttpResponse(null, { status: 204 })
  }),
  // TODO(fe): POST /auth/signup mock (EMAIL_DUPLICATED·VALIDATION_FAILED 케이스 포함)
  http.get(`${API}/me`, ({ request }) => {
    const u = currentUser(request)
    return u ? HttpResponse.json(toUserSummary(u)) : error(401, 'UNAUTHENTICATED', 'Login required')
  }),

  // ─── 탐색 (「API·이벤트 명세」 2장) ────────────────────────────────────
  http.get(`${API}/procedures`, ({ request }) => {
    return requireUser(request) ?? HttpResponse.json(procedures.map((p) => toProcedure(p, localeOf(request))))
  }),
  http.get(`${API}/hospitals/search`, ({ request }) => {
    const denied = requireUser(request)
    if (denied) return denied
    const q = new URL(request.url).searchParams
    const locale = localeOf(request)
    const procedure = (q.get('procedure') || undefined) as ProcedureCode | undefined
    const areas = q.getAll('areas')
    const language = q.get('language')
    const priceMax = q.get('priceMax') ? Number(q.get('priceMax')) : null
    const sort = (q.get('sort') || 'REVIEW_COUNT') as SortBy
    const page = Number(q.get('page') ?? 0)
    const size = Number(q.get('size') ?? 20)
    // TODO(fe): dateFrom/dateTo 슬롯 필터, DISTANCE 정렬은 backend 규칙 — mock 은 단순 필터만
    let cards: HospitalCard[] = hospitals
      .filter((h) => !areas.length || areas.includes(h.area_code))
      .filter((h) => !language || h.supported_languages.includes(language))
      .map((h) => toHospitalCard(h, locale, procedure))
      .filter((c) => !procedure || c.minPriceKrw != null)
      .filter((c) => priceMax == null || (c.minPriceKrw ?? 0) <= priceMax)
    if (sort === 'PRICE') cards = cards.sort((a, b) => (a.minPriceKrw ?? Infinity) - (b.minPriceKrw ?? Infinity))
    const body: Page<HospitalCard> = { items: cards.slice(page * size, page * size + size), page, size, total: cards.length }
    return HttpResponse.json(body)
  }),
  http.get(`${API}/hospitals/:id`, ({ request, params }) => {
    const denied = requireUser(request)
    if (denied) return denied
    const h = hospitals.find((x) => x.id === Number(params.id))
    return h ? HttpResponse.json(toHospitalDetail(h, localeOf(request))) : error(404, 'NOT_FOUND', 'Hospital not found', { resource: 'hospital' })
  }),
  http.get(`${API}/hospitals/:id/slots`, ({ request, params }) => {
    const denied = requireUser(request)
    if (denied) return denied
    const q = new URL(request.url).searchParams
    const from = q.get('dateFrom')
    const to = q.get('dateTo')
    const list = slots
      .filter((s) => s.hospital_id === Number(params.id) && s.status === 'AVAILABLE')
      .filter((s) => !from || s.start_at.slice(0, 10) >= from)
      .filter((s) => !to || s.start_at.slice(0, 10) <= to)
      .slice(0, Number(q.get('limit') ?? 100))
      .map(toSlot)
    return HttpResponse.json(list)
  }),
  // TODO(fe): GET /hospitals/:id/reviews, POST /hospitals/compare, GET /docs/:docId mock

  // ─── AI 상담 (「API·이벤트 명세」 2·3장) ───────────────────────────────
  http.post(`${API}/ai/conversations`, ({ request }) => {
    const denied = requireUser(request)
    if (denied) return denied
    return HttpResponse.json({
      id: crypto.randomUUID(),
      mode: 'MAIN',
      hospital: null,
      parentConversationId: null,
      consultationId: null,
      conditions: { procedureCode: null, areas: [], dateFrom: null, dateTo: null, budgetMaxKrw: null, consultLanguage: null, sortBy: 'REVIEW_COUNT' },
      createdAt: new Date().toISOString(),
      messages: [],
    })
  }),
  http.post(`${API}/ai/tasks`, async ({ request }) => {
    const denied = requireUser(request)
    if (denied) return denied
    await request.json() as CreateTaskRequest
    return HttpResponse.json({ taskId: crypto.randomUUID() }, { status: 202 })
  }),
  /** 가짜 SSE: STATUS → TOKEN×3 → RESULT_CARDS → DONE (fetch-event-source 가 읽는 text/event-stream) */
  http.get(`${API}/ai/tasks/:id/stream`, ({ request }) => {
    const locale = localeOf(request)
    const cards = hospitals.slice(0, 3).map((h) => toHospitalCard(h, locale, 'DOUBLE_EYELID_NONINCISION'))
    const seq: [SseEventName, unknown][] = [
      ['STATUS', { status: 'RUNNING' }],
      ['TOKEN', { text: '조건에 맞는 ' }],
      ['TOKEN', { text: '병원을 ' }],
      ['TOKEN', { text: '찾았어요.' }],
      ['RESULT_CARDS', { cards, relaxOptions: [] }],
      ['DONE', { answer: '조건에 맞는 병원을 찾았어요.', sources: [] }],
    ]
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        for (let i = 0; i < seq.length; i++) {
          const [event, data] = seq[i]
          await delay(300)
          controller.enqueue(encoder.encode(`id: ${i + 1}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`))
        }
        controller.close()
      },
    })
    return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' } })
  }),
  // TODO(fe): GET /ai/conversations/:id, POST /ai/tasks/:id/approval (+ APPROVAL_REQUIRED 시퀀스), CONVERSATION_OPENED 시나리오

  // TODO(fe): 예약(/reservations*), 알림, 상담(/consultations*, /counselor/*), 병원관리자(/hospital-admin/*) mock
  //           reservations.json·consultations.json·chat_messages.json 을 위 db.ts 와 같은 방식으로 변환해 사용
]
