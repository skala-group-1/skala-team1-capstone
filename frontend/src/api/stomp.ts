/**
 * 상담 실시간 채팅·알림 (「API·이벤트 명세」 4장, 「인증·인가 설계」 4장).
 * - CONNECT 헤더 Authorization: Bearer (ChannelInterceptor 에서 JWT 검증)
 * - 토큰 만료 시 refresh 후 재연결
 * - 재연결되면 이전 구독은 서버에서 사라진다 → whenStompConnected 로 등록한 콜백이 연결될 때마다 다시 실행되어 다시 구독한다
 */
import { Client, type IMessage, type StompSubscription } from '@stomp/stompjs'
import type { ConsultationTopicEvent, Notification, SendChatMessage } from '@/types/contract'
import { refreshAccessToken } from './http'
import { session } from './session'

function wsUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws`
}

let client: Client | null = null

interface Listener {
  onConnect: () => void
  onDisconnect?: () => void
}
/** 연결(재연결 포함)·끊김 때마다 알려 줄 콜백들. 상담방·알림 스토어가 등록한다 */
const listeners = new Set<Listener>()

function notify(kind: keyof Listener) {
  for (const l of listeners) {
    try {
      l[kind]?.()
    } catch (e) {
      console.warn('[stomp] listener error', e)
    }
  }
}

/** access token 이 곧 만료되는지 (JWT exp 기준, 10초 여유). 읽을 수 없으면 false */
function tokenExpiresSoon(token: string | null): boolean {
  if (!token) return true
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))) as { exp?: number }
    return !!payload.exp && payload.exp * 1000 < Date.now() + 10_000
  } catch {
    return false
  }
}

/** 로그인 후 1회 호출. 이미 연결돼 있으면 그대로 반환 */
export function connectStomp(): Client {
  if (client?.active) return client
  const c: Client = new Client({
    brokerURL: wsUrl(),
    reconnectDelay: 3000,
    // 재연결 때마다 최신 토큰을 싣도록 beforeConnect 에서 갱신. access(30분)가 만료됐으면 먼저 refresh
    beforeConnect: async (c) => {
      if (tokenExpiresSoon(session.getToken())) await refreshAccessToken().catch(() => undefined)
      c.connectHeaders = { Authorization: `Bearer ${session.getToken() ?? ''}` }
    },
    // disconnectStomp 로 버린 이전 연결이 늦게 보내는 이벤트는 무시 (계정 전환 직후 새 구독을 지우지 않도록)
    onConnect: () => {
      if (client === c) notify('onConnect')
    },
    onWebSocketClose: () => {
      if (client === c) notify('onDisconnect')
    },
    // backend 는 인증 실패를 ERROR 프레임 message "UNAUTHENTICATED" 로 보낸다 → refresh 해 두면 다음 재연결이 새 토큰으로 붙는다
    onStompError: (frame) => {
      console.warn('[stomp] error', frame.headers.message)
      if (frame.headers.message?.includes('UNAUTHENTICATED')) void refreshAccessToken().catch(() => undefined)
    },
  })
  client = c
  c.activate()
  return c
}

/**
 * 연결될 때마다 cb 실행 (지금 연결돼 있으면 바로 1번 + 이후 재연결 때마다).
 * cb 안에서 구독하면 재연결 후에도 다시 구독된다. onDisconnect 는 연결이 끊길 때마다 호출.
 * 반환값을 호출하면 등록 해제 (화면을 떠날 때)
 */
export function whenStompConnected(cb: () => void, onDisconnect?: () => void): () => void {
  const c = connectStomp()
  const listener: Listener = { onConnect: cb, onDisconnect }
  listeners.add(listener)
  if (c.connected) cb()
  return () => {
    listeners.delete(listener)
  }
}

/** 구독 해제. 연결이 이미 끊겼으면 서버에도 구독이 없으므로 조용히 넘어간다 */
export function safeUnsubscribe(sub: StompSubscription | null | undefined): void {
  try {
    sub?.unsubscribe()
  } catch {
    // 연결이 끊긴 상태
  }
}

export function isStompConnected(): boolean {
  return !!client?.connected
}

export function disconnectStomp(): Promise<void> {
  const c = client
  client = null
  notify('onDisconnect')
  return c ? c.deactivate() : Promise.resolve()
}

function parse<T>(m: IMessage): T {
  return JSON.parse(m.body) as T
}

/** SUBSCRIBE /topic/consultations/{id} — 당사자 여부는 backend AccessGuard 가 검사 */
export function subscribeConsultation(id: number, cb: (e: ConsultationTopicEvent) => void): StompSubscription {
  // 연결 전에 부르면 안 됨 → whenStompConnected 콜백 안에서 호출할 것
  if (!client?.connected) throw new Error('STOMP not connected')
  return client.subscribe(`/topic/consultations/${id}`, (m) => cb(parse<ConsultationTopicEvent>(m)))
}

/** SEND /app/consultations/{id}/send {text, clientMsgId} — clientMsgId 로 낙관적 표시 후 MESSAGE_CREATED 와 매칭 */
export function sendConsultationMessage(id: number, body: SendChatMessage): void {
  if (!client?.connected) throw new Error('STOMP not connected')
  client.publish({ destination: `/app/consultations/${id}/send`, body: JSON.stringify(body) })
}

/** SUBSCRIBE /user/queue/notifications — 예약 상태 변경, 새 상담(상담사), 새 예약 요청(병원관리자) */
export function subscribeNotifications(cb: (n: Notification) => void): StompSubscription {
  if (!client?.connected) throw new Error('STOMP not connected')
  return client.subscribe('/user/queue/notifications', (m) => cb(parse<Notification>(m)))
}
