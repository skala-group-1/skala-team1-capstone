/**
 * 라우트 = 08 문서 "FE 라우트 초안". 가드는 화면 표시용일 뿐, 권한 판단은 backend (08·11 문서)
 * - 비로그인: /onboarding, /login, /signup 만 (D-17) → 그 외는 /login?redirect=
 * - meta.roles 와 역할이 다르면 그 역할의 홈으로 (고객 / · 상담사 /counselor · 병원관리자 /hospital-admin · 운영자 /ops)
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/types/contract'

declare module 'vue-router' {
  interface RouteMeta {
    /** true 면 비로그인 접근 허용 */
    public?: boolean
    /** 접근 가능한 역할. 비어 있으면 로그인만 필요 */
    roles?: Role[]
  }
}

const C: Role[] = ['CUSTOMER']

const routes: RouteRecordRaw[] = [
  // 공개
  { path: '/onboarding', component: () => import('@/views/common/OnboardingView.vue'), meta: { public: true } },
  { path: '/login', component: () => import('@/views/common/LoginView.vue'), meta: { public: true } },
  { path: '/signup', component: () => import('@/views/common/SignupView.vue'), meta: { public: true } },

  // 고객
  { path: '/', component: () => import('@/views/customer/HomeView.vue'), meta: { roles: C } },
  // conversationId 없이 들어오면 새 메인 대화를 연다
  { path: '/chat/:conversationId?', component: () => import('@/views/customer/ChatView.vue'), meta: { roles: C } },
  // 탐색·비교·상세는 모든 역할 조회 가능 (11 문서 권한 매트릭스)
  { path: '/explore', component: () => import('@/views/customer/ExploreView.vue') },
  { path: '/compare', component: () => import('@/views/customer/CompareView.vue') },
  { path: '/hospitals/:id', component: () => import('@/views/customer/HospitalDetailView.vue') },
  { path: '/hospitals/:id/book', component: () => import('@/views/customer/BookingView.vue'), meta: { roles: C } },
  { path: '/reservations', component: () => import('@/views/customer/ReservationsView.vue'), meta: { roles: C } },
  { path: '/notifications', component: () => import('@/views/customer/NotificationsView.vue') },
  { path: '/me', component: () => import('@/views/customer/MeView.vue') },

  // 상담사
  { path: '/counselor', component: () => import('@/views/counselor/InboxView.vue'), meta: { roles: ['COUNSELOR'] } },
  {
    path: '/counselor/consultations/:id',
    component: () => import('@/views/counselor/ConsultationChatView.vue'),
    meta: { roles: ['COUNSELOR'] },
  },
  // TODO(fe): 고객 쪽 상담 화면은 C4 채팅(HUMAN 모드) 안에서 처리 — 별도 라우트 없음 (D-09)

  // 병원관리자
  { path: '/hospital-admin', component: () => import('@/views/hospitalAdmin/DashboardView.vue'), meta: { roles: ['HOSPITAL_ADMIN'] } },
  {
    path: '/hospital-admin/reservations',
    component: () => import('@/views/hospitalAdmin/ReservationsView.vue'),
    meta: { roles: ['HOSPITAL_ADMIN'] },
  },

  // 운영자 (P1)
  { path: '/ops', component: () => import('@/views/ops/OpsView.vue'), meta: { roles: ['OPERATOR'] } },

  { path: '/forbidden', component: () => import('@/views/common/ForbiddenView.vue') },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/common/NotFoundView.vue'), meta: { public: true } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.bootstrap()

  if (to.meta.public) {
    // 로그인 상태로 로그인·가입 화면에 오면 홈으로
    if (auth.isLoggedIn && (to.path === '/login' || to.path === '/signup')) return auth.home
    return true
  }
  if (!auth.isLoggedIn) {
    // TODO(fe): 첫 방문(언어 미선택)이면 /onboarding 으로
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  const roles = to.meta.roles
  if (roles?.length && auth.role && !roles.includes(auth.role)) return auth.home
  return true
})
