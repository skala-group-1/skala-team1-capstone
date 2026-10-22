/**
 * AI 작업 SSE 구독 (「API·이벤트 명세」 3장, 「공통 계약서」 6장, 「인증·인가 설계」 4장).
 * - 브라우저 EventSource 는 헤더를 못 보내므로 fetch-event-source 로 Authorization 헤더를 싣는다 (토큰을 URL 에 넣지 않음)
 * - SSE `id:` = seq. 끊기면 Last-Event-ID 로 이후 이벤트만 다시 받는다 (backend 가 작업별 버퍼 보관)
 * - DONE / FAILED / APPROVAL_REQUIRED 가 오면 스트림 종료. 승인 후에는 같은 taskId 로 다시 streamTask 호출
 */
import { fetchEventSource, EventStreamContentType } from '@microsoft/fetch-event-source'
import type { SseEvent, SseEventName, Uuid } from '@/types/contract'
import { TERMINAL_SSE_EVENTS } from '@/types/contract'
import { API_BASE, refreshAccessToken } from './http'
import { session } from './session'

export interface StreamHandlers {
  /** 모든 이벤트. conversation 스토어의 reducer 로 넘긴다 */
  onEvent: (e: SseEvent) => void
  onError?: (err: unknown) => void
  /** 네트워크가 끊겨 재시도 중이면 true, 다시 열리면 false ("재연결 중" 배너용) */
  onReconnecting?: (reconnecting: boolean) => void
  /** 종료 이벤트 수신 또는 abort 후 */
  onClose?: () => void
}

class FatalSseError extends Error {}
class RefreshedError extends Error {}
/** 네트워크 오류 재시도 상한 — 넘으면 멈추고 onError (끝없이 타이핑 표시만 도는 것 방지) */
const MAX_RETRIES = 5

/**
 * 반환값을 호출하면 구독 해제.
 * fromSeq: 마지막으로 받은 seq. 승인 후 같은 작업을 다시 열 때 넘기면 그 이후 이벤트만 받는다 (Last-Event-ID)
 */
export function streamTask(taskId: Uuid, handlers: StreamHandlers, fromSeq: number | null = null): () => void {
  const ctrl = new AbortController()
  let lastSeq: string | undefined = fromSeq != null ? String(fromSeq) : undefined
  let refreshedOnce = false
  let retries = 0

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Accept-Language': session.getLocale() }
    const token = session.getToken()
    if (token) h.Authorization = `Bearer ${token}`
    // 라이브러리도 자동 재시도 때 last-event-id 를 붙이지만, refresh 후 새로 열 때를 위해 직접 넣는다
    if (lastSeq) h['Last-Event-ID'] = lastSeq
    return h
  }

  const run = (): Promise<void> =>
    fetchEventSource(`${API_BASE}/ai/tasks/${taskId}/stream`, {
      signal: ctrl.signal,
      credentials: 'include',
      openWhenHidden: true,
      headers: headers(),
      async onopen(res) {
        if (res.ok && res.headers.get('content-type')?.includes(EventStreamContentType)) {
          retries = 0
          handlers.onReconnecting?.(false)
          return
        }
        if (res.status === 401 && !refreshedOnce) {
          // 토큰 만료 → refresh 후 새 헤더로 다시 연다 (catch 에서 run() 재호출)
          refreshedOnce = true
          await refreshAccessToken()
          throw new RefreshedError()
        }
        throw new FatalSseError(`SSE open failed: ${res.status}`)
      },
      onmessage(msg) {
        if (msg.id) lastSeq = msg.id
        if (!msg.event) return // heartbeat 등
        // TODO(fe): backend 가 data 를 {event,data} 로 감싸는지, data 만 보내는지 BE-15 와 확정 (「공통 계약서」 6장 표기는 {event, data})
        const parsed = JSON.parse(msg.data)
        const data = parsed && typeof parsed === 'object' && 'event' in parsed && 'data' in parsed ? parsed.data : parsed
        const name = msg.event as SseEventName
        handlers.onEvent({ event: name, data, seq: msg.id ? Number(msg.id) : null } as SseEvent)
        if (TERMINAL_SSE_EVENTS.includes(name)) ctrl.abort()
      },
      onerror(err) {
        // Fatal·Refreshed 는 라이브러리 재시도를 멈추고 catch 로 보낸다. 그 외(네트워크)는 기본 재시도
        if (err instanceof FatalSseError || err instanceof RefreshedError) throw err
        if (++retries > MAX_RETRIES) throw err
        handlers.onReconnecting?.(true)
      },
      onclose() {
        // 서버가 종료 이벤트 없이 닫으면 재연결 시도
        if (!ctrl.signal.aborted) throw new Error('stream closed unexpectedly')
      },
    }).catch((err) => {
      if (err instanceof RefreshedError && !ctrl.signal.aborted) return run()
      handlers.onReconnecting?.(false)
      if (!ctrl.signal.aborted) handlers.onError?.(err)
    })

  void run().finally(() => handlers.onClose?.())
  return () => ctrl.abort()
}
