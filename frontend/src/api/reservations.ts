// 「API·이벤트 명세」 2장 예약 (고객). 상태 전이 규칙은 「공통 계약서」 4장 — FE 는 판단하지 않고 status 만 보여준다
import type { CreateReservationRequest, CreateReviewRequest, Reservation, Review, Slot } from '@/types/contract'
import { http, newIdempotencyKey } from './http'

export const reservationApi = {
  /**
   * 직접 예약 → PENDING (슬롯 30분 홀드). Idempotency-Key 필수.
   * 재시도 버튼은 같은 key 를 넘겨야 중복 예약이 안 생긴다.
   * SLOT_UNAVAILABLE(409) → details.alternatives 로 대안 시간 표시
   */
  create: (body: CreateReservationRequest, idempotencyKey: string = newIdempotencyKey()) =>
    http
      .post<Reservation>('/reservations', body, { headers: { 'Idempotency-Key': idempotencyKey } })
      .then((r) => r.data),
  mine: () => http.get<Reservation[]>('/reservations/me').then((r) => r.data),
  get: (id: number) => http.get<Reservation>(`/reservations/${id}`).then((r) => r.data),
  cancel: (id: number) => http.post<Reservation>(`/reservations/${id}/cancel`).then((r) => r.data),
  /** 반려 시 제안된 대안 슬롯으로 새 PENDING */
  acceptAlternative: (id: number, slotId: Slot['id'], idempotencyKey: string = newIdempotencyKey()) =>
    http
      .post<Reservation>(`/reservations/${id}/accept-alternative`, { slotId }, { headers: { 'Idempotency-Key': idempotencyKey } })
      .then((r) => r.data),
  /** 리뷰 작성 (CONFIRMED 예약, 1회). REVIEW_NOT_ALLOWED·REVIEW_ALREADY_EXISTS(409) */
  writeReview: (id: number, body: CreateReviewRequest) =>
    http.post<Review>(`/reservations/${id}/review`, body).then((r) => r.data),
}
