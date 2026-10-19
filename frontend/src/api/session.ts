/**
 * access token 보관소 (「인증·인가 설계」 1장: 메모리에만, localStorage 저장 금지).
 * axios·SSE·STOMP 가 공용으로 읽는다. Pinia auth 스토어가 값을 넣고 뺀다 (스토어 ↔ http 순환 import 방지용).
 */
import type { Locale } from '@/types/contract'

let accessToken: string | null = null
let locale: Locale = 'en'
let onLoggedOut: (() => void) | null = null

export const session = {
  getToken: () => accessToken,
  setToken: (token: string | null) => {
    accessToken = token
  },
  getLocale: () => locale,
  setLocale: (l: Locale) => {
    locale = l
  },
  /** refresh 실패(REFRESH_INVALID) 시 호출될 콜백 — auth 스토어가 등록 (상태 초기화 + /login 이동) */
  onLoggedOut: (cb: () => void) => {
    onLoggedOut = cb
  },
  emitLoggedOut: () => onLoggedOut?.(),
}
