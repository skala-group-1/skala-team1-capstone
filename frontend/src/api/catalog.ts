// 「API·이벤트 명세」 2장 탐색·비교 (backend PR #1 에 구현됨: CatalogController)
import type {
  CompareRequest,
  CompareResponse,
  HospitalDetail,
  HospitalCard,
  HospitalSearchQuery,
  Locale,
  Page,
  PageRequest,
  Procedure,
  ProcedureCode,
  IsoDate,
  Review,
  Slot,
} from '@/types/contract'
import { http } from './http'

export interface SlotQuery {
  procedure?: ProcedureCode
  dateFrom?: IsoDate
  dateTo?: IsoDate
  doctorId?: number
  limit?: number
}

export const catalogApi = {
  procedures: () => http.get<Procedure[]>('/procedures').then((r) => r.data),
  /** 추천이 아니라 사용자가 고른 sort 로만 정렬 (D-01) */
  searchHospitals: (q: HospitalSearchQuery) =>
    http.get<Page<HospitalCard>>('/hospitals/search', { params: q }).then((r) => r.data),
  hospital: (id: number) => http.get<HospitalDetail>(`/hospitals/${id}`).then((r) => r.data),
  slots: (id: number, q: SlotQuery) => http.get<Slot[]>(`/hospitals/${id}/slots`, { params: q }).then((r) => r.data),
  reviews: (id: number, q: PageRequest & { lang?: Locale; procedure?: ProcedureCode }) =>
    http.get<Page<Review>>(`/hospitals/${id}/reviews`, { params: q }).then((r) => r.data),
  /** 최대 3곳 */
  compare: (body: CompareRequest) => http.post<CompareResponse>('/hospitals/compare', body).then((r) => r.data),
  /** 근거 문서 원문 (C4-1). 응답은 13-2 제안 형식 {uri, docId, title, section, body, meta} — AGENT-16 에서 확정 */
  doc: (docId: string, section?: string) =>
    http.get<unknown>(`/docs/${encodeURIComponent(docId)}`, { params: { section } }).then((r) => r.data),
}
