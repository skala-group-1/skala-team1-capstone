/**
 * data/mock/out/*.json (DB 행, snake_case) → 「공통 계약서」 DTO (camelCase) 변환.
 * dev 전용 — main.ts 에서 import.meta.env.DEV 일 때만 동적 import 되므로 운영 번들에 들어가지 않는다.
 * JSON 은 직접 고치지 말고 data/mock/generate.py 로 재생성 (README 협업 규칙).
 *
 * 주의: 이 파일의 변환은 "화면 개발용 근사치"다. 검색·정렬·가격 규칙의 기준은 backend 이며,
 * 실제 backend 응답과 다르면 backend 를 믿고 여기를 맞춘다.
 */
import hospitalsJson from '@mock/hospitals.json'
import proceduresJson from '@mock/procedures.json'
import usersJson from '@mock/users.json'
import doctorsJson from '@mock/doctors.json'
import priceOptionsJson from '@mock/price_options.json'
import slotsJson from '@mock/slots.json'
import reviewsJson from '@mock/reviews.json'
import type {
  AreaCode,
  Doctor,
  HospitalCard,
  HospitalCategory,
  HospitalDetail,
  Locale,
  PriceOption,
  Procedure,
  Review,
  ReviewStats,
  ProcedureCategory,
  ProcedureCode,
  Slot,
  SlotStatus,
  UserSummary,
  Role,
} from '@/types/contract'

// ─── DB 행 타입 (필요한 컬럼만) ──────────────────────────────
type I18nName = { name_ko: string; name_en: string; name_zh?: string | null; name_ja?: string | null }
type HospitalRow = I18nName & {
  id: number
  category: string
  area_code: string
  address_ko: string | null
  address_en: string | null
  phone: string | null
  open_hours: Record<string, { open: string; close: string } | null>
  supported_languages: string[]
  has_interpreter: boolean
  verified_at: string | null
  description_ko: string | null
  description_en: string | null
  description_zh: string | null
  description_ja: string | null
}
type ProcedureRow = I18nName & { code: string; category: string; duration_min: number; downtime_days: number }
type UserRow = {
  id: number
  email: string
  password: string
  name: string
  locale: string
  role: string
  hospital_id: number | null
}
type DoctorRow = {
  id: number
  hospital_id: number
  name_ko: string
  name_en: string
  title: string
  specialties: string[]
  languages: string[]
  career_years: number
}
type PriceOptionRow = {
  id: number
  hospital_id: number
  procedure_code: string
  product: string
  dose: string | null
  price_krw: number
  vat_included: boolean
  conditions_ko: string | null
  conditions_en: string | null
  verified_at: string | null
}
type SlotRow = {
  id: number
  hospital_id: number
  doctor_id: number | null
  start_at: string
  end_at: string
  status: string
}

export const hospitals = hospitalsJson as HospitalRow[]
export const procedures = proceduresJson as ProcedureRow[]
export const users = usersJson as UserRow[]
export const doctors = doctorsJson as DoctorRow[]
export const priceOptions = priceOptionsJson as PriceOptionRow[]
export const slots = slotsJson as SlotRow[]

type ReviewRow = {
  id: number
  hospital_id: number
  procedure_code: string
  rating: number
  age_group: string
  gender: string
  reviewer_nationality: string | null
  lang: string
  content: string
  created_at: string
}
export const reviews = (reviewsJson as ReviewRow[]).sort((a, b) => b.created_at.localeCompare(a.created_at))
/** app.hospital_review_stats 뷰와 같은 집계 (건수·평균·연령대·성별) */
const statsCache = new Map<number, ReviewStats>()
export function reviewStats(hospitalId: number): ReviewStats {
  let s = statsCache.get(hospitalId)
  if (!s) {
    const rows = reviews.filter((r) => r.hospital_id === hospitalId)
    const count = (key: 'age_group' | 'gender') => rows.reduce<Record<string, number>>((m, r) => ((m[r[key]] = (m[r[key]] ?? 0) + 1), m), {})
    s = {
      reviewCount: rows.length,
      avgRating: rows.length ? Math.round((rows.reduce((a, r) => a + r.rating, 0) / rows.length) * 100) / 100 : null,
      byAgeGroup: count('age_group'),
      byGender: count('gender'),
    }
    statsCache.set(hospitalId, s)
  }
  return s
}
export function toReview(r: ReviewRow): Review {
  return {
    id: r.id,
    procedureCode: r.procedure_code as ProcedureCode,
    rating: r.rating,
    ageGroup: r.age_group,
    gender: r.gender as Review['gender'],
    reviewerNationality: r.reviewer_nationality ?? '',
    lang: r.lang as Locale,
    content: r.content,
    createdAt: r.created_at,
  }
}

/** 12-1: 응답은 요청자 locale 로 이미 골라서 name 하나로. 없으면 en → ko */
export function pickName(row: I18nName, locale: Locale): string {
  const v = locale === 'zh' ? row.name_zh : locale === 'ja' ? row.name_ja : locale === 'ko' ? row.name_ko : row.name_en
  return v || row.name_en || row.name_ko
}

export function toUserSummary(u: UserRow): UserSummary {
  return { id: u.id, name: u.name, role: u.role as Role, hospitalId: u.hospital_id, locale: u.locale as Locale }
}

export function toProcedure(p: ProcedureRow, locale: Locale): Procedure {
  return {
    code: p.code as ProcedureCode,
    category: p.category as ProcedureCategory,
    name: pickName(p, locale),
    durationMin: p.duration_min,
    downtimeDays: p.downtime_days,
  }
}

export function toPriceOption(o: PriceOptionRow, locale: Locale): PriceOption {
  return {
    id: o.id,
    procedureCode: o.procedure_code as ProcedureCode,
    product: o.product,
    dose: o.dose,
    priceKrw: o.price_krw,
    vatIncluded: o.vat_included,
    conditions: locale === 'ko' ? o.conditions_ko : o.conditions_en,
    verifiedAt: o.verified_at,
  }
}

export function toDoctor(d: DoctorRow, locale: Locale): Doctor {
  return {
    id: d.id,
    name: locale === 'ko' ? d.name_ko : d.name_en,
    title: d.title,
    specialties: d.specialties as ProcedureCode[],
    languages: d.languages as Locale[],
    careerYears: d.career_years,
  }
}

export function toSlot(s: SlotRow): Slot {
  const doc = s.doctor_id != null ? doctors.find((d) => d.id === s.doctor_id) : undefined
  return {
    id: s.id,
    startAt: s.start_at,
    endAt: s.end_at,
    doctorId: s.doctor_id,
    doctorName: doc ? doc.name_en : null,
    status: s.status as SlotStatus,
  }
}

export function toHospitalCard(h: HospitalRow, locale: Locale, procedureCode?: ProcedureCode): HospitalCard {
  const opts = priceOptions.filter((o) => o.hospital_id === h.id && (!procedureCode || o.procedure_code === procedureCode))
  const min = opts.length ? opts.reduce((a, b) => (a.price_krw <= b.price_krw ? a : b)) : null
  const firstSlot = slots.find((s) => s.hospital_id === h.id && s.status === 'AVAILABLE' && new Date(s.start_at).getTime() > Date.now())
  return {
    id: h.id,
    name: pickName(h, locale),
    areaCode: h.area_code as AreaCode,
    category: h.category as HospitalCategory,
    minPriceKrw: min ? min.price_krw : null,
    priceVerified: !!min?.verified_at,
    reviewCount: reviewStats(h.id).reviewCount,
    rating: reviewStats(h.id).avgRating,
    languages: h.supported_languages as Locale[],
    hasInterpreter: h.has_interpreter,
    earliestSlotAt: firstSlot ? firstSlot.start_at : null,
    distanceKm: null,
  }
}

export function toHospitalDetail(h: HospitalRow, locale: Locale): HospitalDetail {
  const desc =
    { ko: h.description_ko, en: h.description_en, zh: h.description_zh, ja: h.description_ja }[locale] ?? h.description_en
  const opts = priceOptions.filter((o) => o.hospital_id === h.id)
  const codes = [...new Set(opts.map((o) => o.procedure_code))]
  return {
    id: h.id,
    name: pickName(h, locale),
    nameKo: h.name_ko,
    category: h.category as HospitalCategory,
    areaCode: h.area_code as AreaCode,
    address: locale === 'ko' ? h.address_ko : h.address_en,
    phone: h.phone,
    description: desc,
    openHours: h.open_hours,
    languages: h.supported_languages as Locale[],
    hasInterpreter: h.has_interpreter,
    verifiedAt: h.verified_at,
    doctors: doctors.filter((d) => d.hospital_id === h.id).map((d) => toDoctor(d, locale)),
    procedures: codes.flatMap((code) => {
      const p = procedures.find((x) => x.code === code)
      if (!p) return []
      return [
        {
          procedure: toProcedure(p, locale),
          options: opts.filter((o) => o.procedure_code === code).map((o) => toPriceOption(o, locale)),
        },
      ]
    }),
    reviewStats: reviewStats(h.id),
  }
}
