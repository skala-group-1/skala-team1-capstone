// 시술 사후관리 대화방 (시술 전 준비 안내 포함). 메시지·작업·SSE 는 기존 aiApi / streamTask 를 그대로 쓴다
import type { ConversationMode, ReservationStatus, Uuid } from '@/types/contract'
import { http } from './http'

export interface AftercareConversation {
  conversationId: Uuid
  reservationId: number
  /** PENDING·CONFIRMED 가 아니면 안내가 끝난 방 (기록만 표시) */
  reservationStatus: ReservationStatus
  mode: ConversationMode
  procedureCode: string
  procedureName: string | null
  hospital: { id: number; name: string }
  /** 시술(슬롯) 시작 시각 */
  startAt: string
  /** 오늘이 시술일로부터 며칠째인지 (시술일 0, 시술 전 음수) — backend 가 Asia/Seoul 날짜로 계산 */
  daysFromProcedure: number
  /** 진행 중인 AI 작업(그날 안내 포함) */
  activeTaskId: Uuid | null
  createdAt: string
}

export const aftercareApi = {
  /** 승인 대기·확정 예약의 사후관리 방 열기: 새로 만들면 201, 이미 있으면 200. 그날 안내가 없으면 AI 안내를 요청한다 */
  open: (reservationId: number) =>
    http.post<AftercareConversation>(`/reservations/${reservationId}/aftercare-conversation`).then((r) => r.data),
  /** 내 사후관리 방 목록 (최신순) */
  mine: () => http.get<AftercareConversation[]>('/aftercare/conversations').then((r) => r.data),
}

/** 안내를 받을 수 있는 예약 상태 */
export const AFTERCARE_ACTIVE: ReservationStatus[] = ['PENDING', 'CONFIRMED']
export const isAftercareClosed = (room: AftercareConversation) => !AFTERCARE_ACTIVE.includes(room.reservationStatus)
