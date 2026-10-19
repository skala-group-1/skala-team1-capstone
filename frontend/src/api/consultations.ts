// 「API·이벤트 명세」 2장 상담 (고객·상담사 공통 + 상담사 전용). 실시간 메시지는 stomp.ts
import type { ChatMessage, Consultation, ConsultationStatus } from '@/types/contract'
import { http } from './http'

export const consultationApi = {
  /** 요약 카드는 역할에 따라 ko / 고객 언어로 내려온다 */
  get: (id: number) => http.get<Consultation>(`/consultations/${id}`).then((r) => r.data),
  messages: (id: number) => http.get<ChatMessage[]>(`/consultations/${id}/messages`).then((r) => r.data),
  retryTranslation: (id: number, msgId: number) =>
    http.post<void>(`/consultations/${id}/messages/${msgId}/retry-translation`).then(() => undefined),
}

export const counselorApi = {
  /** 자기 병원 문의함 (S1). hospital 필터는 backend 가 토큰으로 강제 */
  inbox: (status?: ConsultationStatus) =>
    http.get<Consultation[]>('/counselor/consultations', { params: { status } }).then((r) => r.data),
  /** WAITING → ACTIVE */
  accept: (id: number) => http.post<Consultation>(`/counselor/consultations/${id}/accept`).then((r) => r.data),
  /** → CLOSED, 대화 mode AI 복귀 */
  close: (id: number) => http.post<Consultation>(`/counselor/consultations/${id}/close`).then((r) => r.data),
}
