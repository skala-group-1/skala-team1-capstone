/** 직접 탐색 (C5 리스트·C5-1 필터·C6 비교). 정렬은 사용자가 고른 기준만 (D-01, 추천 금지) */
import { defineStore } from 'pinia'
import { catalogApi } from '@/api'
import type { CompareResponse, HospitalCard, HospitalSearchQuery, Procedure, ProcedureCode } from '@/types/contract'

export const useSearchStore = defineStore('search', {
  state: () => ({
    procedures: [] as Procedure[],
    query: { sort: 'REVIEW_COUNT', page: 0, size: 20 } as HospitalSearchQuery,
    results: [] as HospitalCard[],
    total: 0,
    loading: false,
    /** 비교 체크박스 (≤3) */
    compareIds: [] as number[],
    compare: null as CompareResponse | null,
  }),
  actions: {
    async loadProcedures() {
      if (!this.procedures.length) this.procedures = await catalogApi.procedures()
    },
    async search(patch: Partial<HospitalSearchQuery> = {}) {
      this.query = { ...this.query, ...patch }
      this.loading = true
      try {
        const page = await catalogApi.searchHospitals(this.query)
        // TODO(fe): 무한 스크롤이면 page>0 일 때 append
        this.results = page.items
        this.total = page.total
      } finally {
        this.loading = false
      }
    },
    toggleCompare(id: number) {
      const i = this.compareIds.indexOf(id)
      if (i >= 0) this.compareIds.splice(i, 1)
      else if (this.compareIds.length < 3) this.compareIds.push(id)
      // TODO(fe): 3개 초과 시 안내 토스트
    },
    async loadCompare(procedureCode: ProcedureCode) {
      this.compare = await catalogApi.compare({ hospitalIds: this.compareIds, procedureCode })
    },
    // TODO(fe): 거리 정렬(DISTANCE) 시 navigator.geolocation 으로 lat/lng 채우기 (지도 없음, D-21)
  },
})
