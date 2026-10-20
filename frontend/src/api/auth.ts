// 「인증·인가 설계」 1장 API (backend PR #1 에 구현됨: AuthController, MeController)
import type { Locale, LoginRequest, LoginResponse, SignupRequest, UserSummary } from '@/types/contract'
import { http, refreshAccessToken } from './http'

export const authApi = {
  /** 201. EMAIL_DUPLICATED(409), VALIDATION_FAILED(400). 고객만 가입 가능 */
  signup: (body: SignupRequest) => http.post<UserSummary>('/auth/signup', body).then((r) => r.data),
  /** 200 + Set-Cookie refresh_token. 실패 시 INVALID_CREDENTIALS(401) */
  login: (body: LoginRequest) => http.post<LoginResponse>('/auth/login', body).then((r) => r.data),
  /** 쿠키로 새 access 발급 (회전). REFRESH_INVALID(401) */
  refresh: () => refreshAccessToken(),
  /** 204, 쿠키 삭제 */
  logout: () => http.post<void>('/auth/logout').then(() => undefined),
  me: () => http.get<UserSummary>('/me').then((r) => r.data),
  /** 언어 변경 (고객 en/zh/ja, 스태프 ko/en). 토큰 locale 은 다음 refresh 부터 반영 */
  updateMe: (body: { locale: Locale }) => http.patch<UserSummary>('/me', body).then((r) => r.data),
}
