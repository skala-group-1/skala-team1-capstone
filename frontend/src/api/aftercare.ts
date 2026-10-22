// 시술 사후관리 대화방. 메시지·작업·SSE 는 기존 aiApi / streamTask 를 그대로 쓴다
import type { ConversationMode, Uuid } from '@/types/contract'
import { http } from './http'

export interface AftercareConversation {
  conversationId: Uuid
  reservationId: number
  mode: ConversationMode
  procedureCode: string
  procedureName: string | null
  hospital: { id: number; name: string }
  /** 시술(슬롯) 시작 시각 */
  startAt: string
  /** 진행 중인 AI 작업(첫 안내 포함) */
  activeTaskId: Uuid | null
  createdAt: string
}

export const aftercareApi = {
  /** 확정 예약의 사후관리 방 열기: 새로 만들면 201 (AI 첫 안내 요청), 이미 있으면 200 */
  open: (reservationId: number) =>
    http.post<AftercareConversation>(`/reservations/${reservationId}/aftercare-conversation`).then((r) => r.data),
  /** 내 사후관리 방 목록 (최신순) */
  mine: () => http.get<AftercareConversation[]>('/aftercare/conversations').then((r) => r.data),
}
