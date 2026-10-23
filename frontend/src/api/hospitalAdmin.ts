// 「API·이벤트 명세」 2장 병원관리자 / 운영자
import type {
  AdminReview,
  AdminReviewPage,
  AuditLog,
  Counselor,
  CounselorRoster,
  CreateCounselorRequest,
  HideRequest,
  HospitalDashboard,
  IsoDate,
  Locale,
  OpsAiTask,
  Page,
  PageRequest,
  RejectRequest,
  Reservation,
  ReservationStatus,
  ReviewFilter,
  ReviewSort,
  UpdateCounselorRequest,
} from '@/types/contract'
import { http } from './http'

export const hospitalAdminApi = {
  dashboard: () => http.get<HospitalDashboard>('/hospital-admin/dashboard').then((r) => r.data),
  /** 13-2: 페이지 응답, 슬롯 시각순 */
  reservations: (q: PageRequest & { status?: ReservationStatus; date?: IsoDate } = {}) =>
    http.get<Page<Reservation>>('/hospital-admin/reservations', { params: q }).then((r) => r.data),
  /** 슬롯 version 재검사 → CONFIRMED. CONCURRENT_UPDATE(409) 가능 */
  approve: (id: number) => http.post<Reservation>(`/hospital-admin/reservations/${id}/approve`).then((r) => r.data),
  /** 사유 필수, 대안 슬롯 ≤3 */
  reject: (id: number, body: RejectRequest) =>
    http.post<Reservation>(`/hospital-admin/reservations/${id}/reject`, body).then((r) => r.data),
  /** 상담사 관리 (H4-D): 우리 병원 상담사 + 대기 문의 수 */
  counselors: () => http.get<CounselorRoster>('/hospital-admin/counselors').then((r) => r.data),
  /** 초기 비밀번호로 바로 생성. EMAIL_DUPLICATED(409) 가능 */
  createCounselor: (body: CreateCounselorRequest) => http.post<Counselor>('/hospital-admin/counselors', body).then((r) => r.data),
  updateCounselor: (id: number, body: UpdateCounselorRequest) =>
    http.patch<Counselor>(`/hospital-admin/counselors/${id}`, body).then((r) => r.data),
  /** 진행 중 상담이 있으면 INVALID_STATE_TRANSITION(409) */
  deactivateCounselor: (id: number) => http.post<Counselor>(`/hospital-admin/counselors/${id}/deactivate`).then((r) => r.data),
  activateCounselor: (id: number) => http.post<Counselor>(`/hospital-admin/counselors/${id}/activate`).then((r) => r.data),
  /** 리뷰 관리 (H5-D): 목록 + 요약 */
  reviews: (q: PageRequest & { filter?: ReviewFilter; lang?: Locale; sort?: ReviewSort } = {}) =>
    http.get<AdminReviewPage>('/hospital-admin/reviews', { params: q }).then((r) => r.data),
  /** 답글 등록·수정 (리뷰당 1개, 고객 언어로 번역됨) */
  replyReview: (id: number, content: string) => http.put<AdminReview>(`/hospital-admin/reviews/${id}/reply`, { content }).then((r) => r.data),
  deleteReply: (id: number) => http.delete(`/hospital-admin/reviews/${id}/reply`).then(() => undefined),
  /** 바로 숨김 (고객 목록·통계에서 빠짐). OTHER 는 detail 필수 */
  hideReview: (id: number, body: HideRequest) => http.post<AdminReview>(`/hospital-admin/reviews/${id}/hide`, body).then((r) => r.data),
  unhideReview: (id: number) => http.post<AdminReview>(`/hospital-admin/reviews/${id}/unhide`).then((r) => r.data),
}

export const opsApi = {
  auditLogs: (q: PageRequest & { action?: string } = {}) => http.get<Page<AuditLog>>('/ops/audit-logs', { params: q }).then((r) => r.data),
  aiTasks: (q: PageRequest & { status?: string } = {}) => http.get<Page<OpsAiTask>>('/ops/ai-tasks', { params: q }).then((r) => r.data),
}
