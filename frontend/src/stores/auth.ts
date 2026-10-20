/**
 * 인증 상태 (「인증·인가 설계」 1·5장).
 * - access token 은 메모리(session)에만. 새로고침 시 bootstrap() 이 /api/auth/refresh 로 복구
 * - 역할별 홈: 고객 /, 상담사 /counselor, 병원관리자 /hospital-admin, 운영자 /ops
 */
import { defineStore } from 'pinia'
import { authApi, session } from '@/api'
import { connectStomp, disconnectStomp } from '@/api/stomp'
import { useConversationStore } from './conversation'
import { useConsultationStore } from './consultation'
import { useNotificationStore } from './notification'
import { useReservationStore } from './reservation'
import { useSearchStore } from './search'
import type { LoginRequest, Locale, Role, SignupRequest, UserSummary } from '@/types/contract'

export const ROLE_HOME: Record<Role, string> = {
  CUSTOMER: '/',
  COUNSELOR: '/counselor',
  HOSPITAL_ADMIN: '/hospital-admin',
  OPERATOR: '/ops',
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as UserSummary | null,
    /** bootstrap(새로고침 refresh 시도) 완료 여부 — 라우터 가드가 기다린다 */
    ready: false,
  }),
  getters: {
    isLoggedIn: (s) => !!s.user,
    role: (s) => s.user?.role ?? null,
    home: (s) => (s.user ? ROLE_HOME[s.user.role] : '/login'),
  },
  actions: {
    /** 앱 시작 시 1회: refresh 성공 → 로그인 유지 / 실패 → 비로그인 */
    async bootstrap() {
      session.onLoggedOut(() => this.clear())
      try {
        const res = await authApi.refresh()
        this.setUser(res.user)
      } catch {
        this.clear()
      } finally {
        this.ready = true
      }
    },
    async login(body: LoginRequest) {
      const res = await authApi.login(body)
      session.setToken(res.accessToken)
      this.setUser(res.user)
      return res.user
    },
    async signup(body: SignupRequest) {
      // TODO(fe): 가입 후 자동 로그인할지 /login 으로 보낼지 결정 (「인증·인가 설계」에 명시 없음)
      return authApi.signup(body)
    },
    async logout() {
      try {
        await authApi.logout()
      } finally {
        this.clear()
      }
    },
    setUser(user: UserSummary) {
      // 고객: 이 기기에서 고른 언어(온보딩·내 정보, i18n setLocale 이 저장)가 계정 언어보다 우선 → 계정에도 저장
      const picked = localStorage.getItem('locale') as Locale | null
      if (user.role === 'CUSTOMER' && picked && ['en', 'zh', 'ja', 'ko'].includes(picked) && picked !== user.locale) {
        user = { ...user, locale: picked }
        void authApi.updateMe({ locale: picked }).catch(() => undefined)
      }
      this.user = user
      session.setLocale(user.locale)
      // TODO(fe): STOMP 는 상담·알림 화면에서만 필요하면 지연 연결로 바꿔도 됨. MSW 모드에서는 /ws 가 없어 재연결 로그가 남음
      if (import.meta.env.VITE_USE_MSW !== 'true') connectStomp()
    },
    async setLocale(locale: Locale) {
      session.setLocale(locale)
      if (this.user) this.user = { ...this.user, ...(await authApi.updateMe({ locale })), locale }
    },
    clear() {
      this.user = null
      session.setToken(null)
      void disconnectStomp()
      // 다음에 로그인한 사용자에게 이전 사용자의 대화·예약·알림이 보이지 않게
      const conv = useConversationStore()
      conv.unsubscribe?.()
      useConsultationStore().close()
      for (const s of [conv, useConsultationStore(), useNotificationStore(), useReservationStore(), useSearchStore()]) s.$reset()
    },
  },
})
