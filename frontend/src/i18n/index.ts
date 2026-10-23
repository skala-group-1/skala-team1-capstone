/**
 * 화면 문구 다국어 (en/zh/ja/ko — 고객도 ko 선택 가능, 스태프는 ko/en).
 * locale 우선순위 (「공통 계약서」 1장 과 동일하게): 로그인 사용자 locale → 온보딩에서 고른 언어 → 브라우저 언어 → en
 * - API 응답의 병원명·시술명은 backend 가 Accept-Language 로 골라서 준다 → 여기서 번역하지 않음
 * - 화면 언어는 localStorage('locale') 에 저장 (토큰이 아니므로 저장 가능). 로그인 사용자 locale 로도 바뀐다(App.vue)
 * - 온보딩에서 고른 언어는 따로 localStorage('localePicked') 에 두고, 다음 고객 로그인 때 계정에 1번 반영한다(auth.setUser)
 */
import { createI18n } from 'vue-i18n'
import en from './locales/en'
import zh from './locales/zh'
import ja from './locales/ja'
import ko from './locales/ko'
import { aftercareMessages } from './aftercare'
import { counselorAdminMessages } from './counselorAdmin'
import { session } from '@/api/session'
import type { Locale } from '@/types/contract'
import { storage } from '@/utils/storage'

const SUPPORTED: Locale[] = ['en', 'zh', 'ja', 'ko']

function initialLocale(): Locale {
  const saved = storage.get('locale') as Locale | null
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
for (const l of SUPPORTED) i18n.global.mergeLocaleMessage(l, aftercareMessages[l])
for (const l of SUPPORTED) i18n.global.mergeLocaleMessage(l, counselorAdminMessages[l])
session.setLocale(i18n.global.locale.value as Locale)
applyDocumentLocale(i18n.global.locale.value as Locale)

/** <html lang>(스크린리더 발음·글꼴 분기)과 탭 제목을 화면 언어로. 중국어는 간체 zh-Hans */
function applyDocumentLocale(locale: Locale) {
  document.documentElement.lang = locale === 'zh' ? 'zh-Hans' : locale
  document.title = i18n.global.t('app.brand')
}

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  session.setLocale(locale)
  storage.set('locale', locale)
  applyDocumentLocale(locale)
}
// TODO(fe): 날짜·금액 포맷 (Intl.DateTimeFormat Asia/Seoul, priceKrw 는 원 단위 정수 — 통화 변환 없음 「공통 계약서」 1장)
