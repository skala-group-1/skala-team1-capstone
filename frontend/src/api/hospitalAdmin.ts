// 07 문서 2장 병원관리자 / 운영자
import type { HospitalDashboard, IsoDate, RejectRequest, Reservation, ReservationStatus } from '@/types/contract'
import { http } from './http'

export const hospitalAdminApi = {
  dashboard: () => http.get<HospitalDashboard>('/hospital-admin/dashboard').then((r) => r.data),
  reservations: (q: { status?: ReservationStatus; date?: IsoDate } = {}) =>
    http.get<Reservation[]>('/hospital-admin/reservations', { params: q }).then((r) => r.data),
  /** 슬롯 version 재검사 → CONFIRMED. CONCURRENT_UPDATE(409) 가능 */
  approve: (id: number) => http.post<Reservation>(`/hospital-admin/reservations/${id}/approve`).then((r) => r.data),
  /** 사유 필수, 대안 슬롯 ≤3 */
  reject: (id: number, body: RejectRequest) =>
    http.post<Reservation>(`/hospital-admin/reservations/${id}/reject`, body).then((r) => r.data),
}

export const opsApi = {
  // TODO(fe): P1 — 응답 DTO 가 12 계약서에 없음. BE-18 구현 시 타입 추가
  auditLogs: () => http.get<unknown>('/ops/audit-logs').then((r) => r.data),
  failedTasks: () => http.get<unknown>('/ops/ai-tasks', { params: { status: 'FAILED' } }).then((r) => r.data),
}
