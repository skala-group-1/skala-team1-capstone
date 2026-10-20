/**
 * 상담 실시간 채팅·알림 (「API·이벤트 명세」 4장, 「인증·인가 설계」 4장).
 * - CONNECT 헤더 Authorization: Bearer (ChannelInterceptor 에서 JWT 검증)
 * - 토큰 만료 시 refresh 후 재연결
 */
import { Client, type IMessage, type StompSubscription } from '@stomp/stompjs'
import type { ConsultationTopicEvent, Notification, SendChatMessage } from '@/types/contract'
import { session } from './session'

function wsUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws`
}

let client: Client | null = null

/** 로그인 후 1회 호출. 이미 연결돼 있으면 그대로 반환 */
export function connectStomp(): Client {
  if (client?.active) return client
  client = new Client({
    brokerURL: wsUrl(),
    reconnectDelay: 3000,
    // 재연결 때마다 최신 토큰을 싣도록 beforeConnect 에서 갱신
    beforeConnect: (c) => {
      c.connectHeaders = { Authorization: `Bearer ${session.getToken() ?? ''}` }
    },
    // TODO(fe): ERROR 프레임(토큰 만료)이면 refreshAccessToken() 후 재연결 — BE-16 오류 프레임 형식 확인 후 구현
    onStompError: (frame) => console.warn('[stomp] error', frame.headers.message),
  })
  client.activate()
  return client
}

/** 연결된 뒤 cb 실행 (이미 연결돼 있으면 바로). 반환값으로 대기 취소 */
export function whenStompConnected(cb: () => void): () => void {
  const c = connectStomp()
  if (c.connected) {
    cb()
    return () => undefined
  }
  const prev = c.onConnect
  let cancelled = false
  c.onConnect = (frame) => {
    prev?.(frame)
    if (!cancelled) cb()
  }
  return () => {
    cancelled = true
  }
}

export function isStompConnected(): boolean {
  return !!client?.connected
}

export function disconnectStomp(): Promise<void> {
  const c = client
  client = null
  return c ? c.deactivate() : Promise.resolve()
}

function parse<T>(m: IMessage): T {
  return JSON.parse(m.body) as T
}

/** SUBSCRIBE /topic/consultations/{id} — 당사자 여부는 backend AccessGuard 가 검사 */
export function subscribeConsultation(id: number, cb: (e: ConsultationTopicEvent) => void): StompSubscription {
  if (!client?.connected) throw new Error('STOMP not connected')
  // TODO(fe): 연결 전 호출 시 onConnect 이후로 미루는 큐 처리
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
