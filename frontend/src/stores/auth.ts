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
    /** 사용 중 세션 만료 → App.vue 가 보고 안내 + /login?redirect= 로 보낸다 (스토어가 router 를 import 하면 순환) */
    sessionExpired: false,
  }),
  getters: {
    isLoggedIn: (s) => !!s.user,
    role: (s) => s.user?.role ?? null,
    home: (s) => (s.user ? ROLE_HOME[s.user.role] : '/login'),
  },
  actions: {
    /** 앱 시작 시 1회: refresh 성공 → 로그인 유지 / 실패 → 비로그인 */
    async bootstrap() {
      session.onLoggedOut(() => {
        if (this.user) this.sessionExpired = true
        this.clear()
      })
      try {
        const res = await authApi.refresh()
        this.setUser(await this.applyPickedLocale(res.user))
      } catch {
        this.clear()
      } finally {
        this.ready = true
      }
    },
    async login(body: LoginRequest) {
      const res = await authApi.login(body)
      session.setToken(res.accessToken)
      const user = await this.applyPickedLocale(res.user)
      this.setUser(user)
      return user
    },
    async signup(body: SignupRequest) {
      // TODO(fe): 가입 후 자동 로그인할지 /login 으로 보낼지 결정 (「인증·인가 설계」에 명시 없음)
      return authApi.signup(body)
    },
    /** 서버 로그아웃이 실패해도(오프라인 등) 화면은 로그아웃 — 이 브라우저의 토큰·상태는 지운다 */
    async logout() {
      await authApi.logout().catch(() => undefined)
      this.clear()
    },
    /**
     * 고객: 로그인 전 온보딩에서 고른 언어가 있으면 계정 언어보다 우선 → 계정에 1번 저장하고 지운다.
     * 화면 언어('locale')는 직원 로그인 때도 ko 로 바뀌므로 쓰지 않는다 (같은 브라우저에서 직원 다음 고객이 로그인하면 고객 언어가 ko 로 바뀌던 문제).
     * backend 응답 언어(병원·시술 이름 등)는 토큰 locale 로 정해지므로, 저장 후 화면이 데이터를 불러오기 전에 새 토큰을 받는다
     */
    async applyPickedLocale(user: UserSummary): Promise<UserSummary> {
      const picked = localStorage.getItem('localePicked') as Locale | null
      localStorage.removeItem('localePicked')
      if (user.role !== 'CUSTOMER' || !picked || !['en', 'zh', 'ja', 'ko'].includes(picked) || picked === user.locale) return user
      try {
        await authApi.updateMe({ locale: picked })
        await authApi.refresh()
        return { ...user, locale: picked }
      } catch {
        return user
      }
    },
    setUser(user: UserSummary) {
      // 다른 계정으로 바뀌면(로그아웃 없이 다시 로그인) 이전 계정의 상태·구독을 모두 정리한 뒤 새 토큰으로 다시 연결.
      // STOMP 만 끊으면 남은 상담방 리스너가 재연결 때 이전 계정 상담방을 구독 → ACCESS_DENIED 로 연결이 끊기는 루프
      if (this.user && this.user.id !== user.id) {
        const token = session.getToken() // clear() 가 지우므로 새 계정 토큰을 보존
        this.clear()
        session.setToken(token)
      }
      this.user = user
      session.setLocale(user.locale)
      // TODO(fe): STOMP 는 상담·알림 화면에서만 필요하면 지연 연결로 바꿔도 됨. MSW 모드에서는 /ws 가 없어 재연결 로그가 남음
      if (import.meta.env.VITE_USE_MSW !== 'true') {
        connectStomp()
        // 실시간 알림 (예약 확정·반려, 새 상담 요청, 새 예약 요청)
        useNotificationStore().listen()
      }
    },
    /** 내 정보에서 언어 변경 → 계정 저장 → 새 토큰(새 locale) → 언어가 들어간 캐시 비우기 (다음 화면 진입 때 새 언어로 다시 받음) */
    async setLocale(locale: Locale) {
      session.setLocale(locale)
      if (!this.user) return
      const me = await authApi.updateMe({ locale })
      // 토큰에 예전 locale 이 남아 있으면 backend 가 예전 언어로 응답한다 → 바로 갱신 (실패해도 다음 refresh 때 반영)
      await authApi.refresh().catch(() => undefined)
      this.user = { ...this.user, ...me, locale }
      const search = useSearchStore()
      search.procedures = []
      search.results = []
    },
    clear() {
      this.user = null
      session.setToken(null)
      void disconnectStomp()
      // 다음에 로그인한 사용자에게 이전 사용자의 대화·예약·알림이 보이지 않게
      const conv = useConversationStore()
      conv.unsubscribe?.()
      useConsultationStore().close()
      useNotificationStore().stopListening()
      for (const s of [conv, useConsultationStore(), useNotificationStore(), useReservationStore(), useSearchStore()]) s.$reset()
    },
  },
})
