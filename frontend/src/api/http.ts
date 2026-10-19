/**
 * axios 공용 인스턴스 (「인증·인가 설계」 5장 FE 처리).
 * - 모든 요청: Authorization Bearer, Accept-Language(사용자 locale)
 * - 401 TOKEN_EXPIRED → POST /api/auth/refresh 를 1회만 호출 (동시에 실패한 요청들은 같은 refresh 프로미스를 기다림) → 원 요청 재시도
 * - refresh 가 REFRESH_INVALID 등으로 실패 → 로그아웃 처리
 * - refresh 토큰은 HttpOnly 쿠키(refresh_token, Path=/api/auth) 라 JS 는 만지지 않는다 → withCredentials 필요
 */
import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import type { ErrorResponse, LoginResponse } from '@/types/contract'
import { session } from './session'

export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export const http = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  timeout: 15000,
  // Spring 은 배열을 areas=A&areas=B 로 받는다 (axios 기본값 areas[]=A 는 안 됨)
  paramsSerializer: { indexes: null },
})

http.interceptors.request.use((config) => {
  const token = session.getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  config.headers['Accept-Language'] = session.getLocale()
  return config
})

// ─── refresh 단일 비행(single-flight) ───────────────────────
let refreshing: Promise<LoginResponse> | null = null

/** 앱 시작(새로고침) 시에도 호출 — 성공하면 로그인 유지, 실패하면 /login (「인증·인가 설계」 1장) */
export function refreshAccessToken(): Promise<LoginResponse> {
  if (!refreshing) {
    refreshing = axios
      .post<LoginResponse>(`${API_BASE}/auth/refresh`, null, { withCredentials: true })
      .then((res) => {
        session.setToken(res.data.accessToken)
        return res.data
      })
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean }

http.interceptors.response.use(
  (res) => res,
  async (error: AxiosError<ErrorResponse>) => {
    const config = error.config as RetriableConfig | undefined
    const code = error.response?.data?.code
    if (error.response?.status === 401 && code === 'TOKEN_EXPIRED' && config && !config._retried) {
      config._retried = true
      try {
        await refreshAccessToken()
        return http(config)
      } catch (refreshError) {
        session.setToken(null)
        session.emitLoggedOut()
        return Promise.reject(refreshError)
      }
    }
    // TODO(fe): 403 ACCESS_DENIED → "권한 없음" 화면/토스트 (권한 판단은 backend, 「인증·인가 설계」 5장)
    // TODO(fe): 5xx·네트워크 오류 공통 토스트 + traceId 표시 (12-1: 모든 응답에 X-Trace-Id)
    return Promise.reject(error)
  },
)

/** 오류에서 계약서 형식 바디를 꺼낸다. 화면은 code 로 분기하고 message 는 그대로 보여준다 */
export function toApiError(e: unknown): ErrorResponse | null {
  if (axios.isAxiosError<ErrorResponse>(e) && e.response?.data?.code) return e.response.data
  return null
}

/** 응답 헤더의 trace id (오류 신고·LangSmith 추적용) */
export function traceIdOf(e: unknown): string | null {
  if (axios.isAxiosError(e)) return (e.response?.headers?.['x-trace-id'] as string | undefined) ?? null
  return null
}

/** 변경 요청용 멱등키. 예약은 필수 (「공통 계약서」 4장) — 같은 시도에서 재전송할 때는 같은 키를 재사용할 것 */
export function newIdempotencyKey(): string {
  return crypto.randomUUID()
}

export type { AxiosRequestConfig }
