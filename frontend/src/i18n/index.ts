/**
 * 화면 문구 다국어 (en/zh/ja + 스태프 ko).
 * locale 우선순위 (12-1 과 동일하게): 로그인 사용자 locale → 온보딩에서 고른 언어 → 브라우저 언어 → en
 * - API 응답의 병원명·시술명은 backend 가 Accept-Language 로 골라서 준다 → 여기서 번역하지 않음
 * - 온보딩에서 고른 언어는 localStorage('locale') 에 저장 (토큰이 아니므로 저장 가능)
 */
import { createI18n } from 'vue-i18n'
import en from './locales/en'
import zh from './locales/zh'
import ja from './locales/ja'
import ko from './locales/ko'
import { session } from '@/api/session'
import type { Locale } from '@/types/contract'

const SUPPORTED: Locale[] = ['en', 'zh', 'ja', 'ko']

function initialLocale(): Locale {
  const saved = localStorage.getItem('locale') as Locale | null
  if (saved && SUPPORTED.includes(saved)) return saved
  const nav = navigator.language.slice(0, 2) as Locale
  return SUPPORTED.includes(nav) ? nav : 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale(),
  fallbackLocale: 'en',
  messages: { en, zh, ja, ko },
})
session.setLocale(i18n.global.locale.value as Locale)

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  session.setLocale(locale)
  localStorage.setItem('locale', locale)
  document.documentElement.lang = locale
}
// TODO(fe): 날짜·금액 포맷 (Intl.DateTimeFormat Asia/Seoul, priceKrw 는 원 단위 정수 — 통화 변환 없음 12-1)
