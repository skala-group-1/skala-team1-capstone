/**
 * 날짜·금액 표시. 시간대는 항상 Asia/Seoul (「공통 계약서」 1장), 금액은 원 단위 정수 — 통화 변환 없음.
 * 언어는 i18n 현재 locale.
 */
import { i18n } from '@/i18n'

const TZ = 'Asia/Seoul'
const loc = () => i18n.global.locale.value as string

/** "오후 2:14" / "2:14 PM" */
export function fmtTime(iso: string): string {
  return new Intl.DateTimeFormat(loc(), { timeZone: TZ, hour: 'numeric', minute: '2-digit' }).format(new Date(iso))
}

/** "10월 21일 (수)" / "Wed, Oct 21" — 날짜만(YYYY-MM-DD)도 받음 */
export function fmtDate(isoOrDate: string, opts: { weekday?: boolean; year?: boolean } = { weekday: true }): string {
  const d = isoOrDate.length === 10 ? new Date(`${isoOrDate}T00:00:00+09:00`) : new Date(isoOrDate)
  return new Intl.DateTimeFormat(loc(), {
    timeZone: TZ,
    month: 'short',
    day: 'numeric',
    weekday: opts.weekday ? 'short' : undefined,
    year: opts.year ? 'numeric' : undefined,
  }).format(d)
}

/** "10월 21일 (수) 12:00" */
export function fmtDateTime(iso: string): string {
  return `${fmtDate(iso)} ${new Intl.DateTimeFormat(loc(), { timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(iso))}`
}

/** "2026년 10월" / "October 2026" (달력 머리) */
export function fmtMonth(yyyyMm: string): string {
  return new Intl.DateTimeFormat(loc(), { timeZone: TZ, year: 'numeric', month: 'long' }).format(new Date(`${yyyyMm}-15T00:00:00+09:00`))
}

/** 일~토 짧은 요일 이름 (2026-10-18 이 일요일) */
export function weekdayNames(): string[] {
  const f = new Intl.DateTimeFormat(loc(), { timeZone: TZ, weekday: 'short' })
  return Array.from({ length: 7 }, (_, i) => f.format(new Date(`2026-10-${18 + i}T12:00:00+09:00`)))
}

/** "12:00" (24시간, 슬롯 칩) */
export function fmtHm(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit' }).format(new Date(iso))
}

/** 서울 기준 YYYY-MM-DD */
export function seoulDate(iso: string | Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(typeof iso === 'string' ? new Date(iso) : iso)
}

/** 860000 → "860,000원" (ko) / "₩860,000" */
export function fmtKrw(n: number | null | undefined): string {
  if (n == null) return ''
  if (loc() === 'ko') return `${n.toLocaleString('ko-KR')}원`
  return new Intl.NumberFormat(loc(), { style: 'currency', currency: 'KRW' }).format(n)
}

/** 2000000 → "200만 원" (ko) / "₩2M" — 조건 칩처럼 좁은 곳 */
export function fmtKrwCompact(n: number | null | undefined): string {
  if (n == null) return ''
  if (loc() === 'ko') return `${new Intl.NumberFormat('ko-KR', { notation: 'compact' }).format(n)} 원`
  return new Intl.NumberFormat(loc(), { style: 'currency', currency: 'KRW', notation: 'compact' }).format(n)
}

/** 남은 시간 mm:ss (홀드 타이머) — 0 이하면 null */
export function remaining(untilIso: string | null, now = Date.now()): string | null {
  if (!untilIso) return null
  const s = Math.floor((new Date(untilIso).getTime() - now) / 1000)
  if (s <= 0) return null
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/** 외부 지도 앱 링크 (D-34: 주소로 Google Maps 검색, 좌표·임베드 없음) */
export function mapUrl(address: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
}
