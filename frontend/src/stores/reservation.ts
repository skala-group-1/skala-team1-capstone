/** 예약 (C8 예약 시트, C9 내 예약). 상태 전이 판단은 backend (12-4) */
import { defineStore } from 'pinia'
import { catalogApi, reservationApi, newIdempotencyKey, toApiError } from '@/api'
import type { CreateReservationRequest, Reservation, Slot } from '@/types/contract'
import type { SlotQuery } from '@/api/catalog'

export const useReservationStore = defineStore('reservation', {
  state: () => ({
    mine: [] as Reservation[],
    slots: [] as Slot[],
    /** 같은 예약 시도의 재전송은 같은 키 (멱등) — 시트를 새로 열 때만 새로 발급 */
    idempotencyKey: newIdempotencyKey(),
    /** SLOT_UNAVAILABLE 시 대안 슬롯 */
    alternatives: [] as Slot[],
  }),
  actions: {
    startBooking() {
      this.idempotencyKey = newIdempotencyKey()
      this.alternatives = []
    },
    async loadSlots(hospitalId: number, q: SlotQuery) {
      this.slots = await catalogApi.slots(hospitalId, q)
    },
    async create(body: CreateReservationRequest) {
      try {
        return await reservationApi.create(body, this.idempotencyKey)
      } catch (e) {
        const err = toApiError(e)
        if (err?.code === 'SLOT_UNAVAILABLE') this.alternatives = err.details.alternatives ?? []
        // TODO(fe): CONCURRENT_UPDATE(두 브라우저 동시 예약 → 1건 실패, 데모 D) 안내 문구
        throw e
      }
    },
    async loadMine() {
      this.mine = await reservationApi.mine()
    },
    async cancel(id: number) {
      const r = await reservationApi.cancel(id)
      this.replace(r)
    },
    async acceptAlternative(id: number, slotId: number) {
      const r = await reservationApi.acceptAlternative(id, slotId)
      this.mine.unshift(r)
    },
    replace(r: Reservation) {
      const i = this.mine.findIndex((x) => x.id === r.id)
      if (i >= 0) this.mine[i] = r
    },
    // TODO(fe): 홀드 남은 시간 카운트다운(holdExpiresAt), 알림(RESERVATION_*) 수신 시 loadMine()
  },
})
