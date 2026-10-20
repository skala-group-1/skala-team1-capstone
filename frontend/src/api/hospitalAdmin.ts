// 「API·이벤트 명세」 2장 병원관리자 / 운영자
import type { AuditLog, HospitalDashboard, IsoDate, OpsAiTask, Page, PageRequest, RejectRequest, Reservation, ReservationStatus } from '@/types/contract'
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
}

export const opsApi = {
  auditLogs: (q: PageRequest & { action?: string } = {}) => http.get<Page<AuditLog>>('/ops/audit-logs', { params: q }).then((r) => r.data),
  aiTasks: (q: PageRequest & { status?: string } = {}) => http.get<Page<OpsAiTask>>('/ops/ai-tasks', { params: q }).then((r) => r.data),
}
