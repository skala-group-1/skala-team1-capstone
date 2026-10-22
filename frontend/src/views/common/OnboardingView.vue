<script setup lang="ts">
// 「화면 목록」 C1 언어 선택 → 온보딩 소개 (Figma 1:5710 · 1:5777). 다 보면 localStorage 'onboarded' → 재방문 시 건너뜀
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { setLocale } from '@/i18n'
import AppButton from '@/components/ui/AppButton.vue'
import AppIcon, { type IconName } from '@/components/ui/AppIcon.vue'
import type { Locale } from '@/types/contract'

const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()

const step = ref<'language' | 'intro'>('language')
// 처음 값은 지금 화면 언어(브라우저 언어 기준). 고르면 바로 화면에 반영
const picked = ref<Locale>(locale.value as Locale)
const languages: { locale: Locale; label: string }[] = [
  { locale: 'en', label: 'English' },
  { locale: 'zh', label: '简体中文' },
  { locale: 'ja', label: '日本語' },
  { locale: 'ko', label: '한국어' },
]
const points: { icon: IconName; key: string }[] = [
  { icon: 'message-circle', key: 'ai' },
  { icon: 'columns', key: 'compare' },
  { icon: 'calendar', key: 'booking' },
]

function pick(l: Locale) {
  picked.value = l
  setLocale(l)
}
function next() {
  // 기본 선택(브라우저 언어)을 그대로 두고 넘어가도 '고른 언어'로 저장 → 다음 고객 로그인 때 계정 언어로 1번 반영 (auth.setUser)
  setLocale(picked.value)
  localStorage.setItem('localePicked', picked.value)
  step.value = 'intro'
}
function finish(to: '/signup' | '/login') {
  localStorage.setItem('onboarded', '1')
  // 공유 링크 목적지(redirect)를 로그인·가입으로 이어 넘김
  void router.replace({ path: to, query: route.query.redirect ? { redirect: route.query.redirect } : {} })
}
</script>

<template>
  <div class="page">
    <section v-if="step === 'language'" class="content">
      <p class="logo t-display-28">{{ t('app.brand') }}</p>
      <h1 class="t-title-22">{{ t('onboarding.languageTitle') }}</h1>
      <p class="sub t-body-14">Choose your language · 选择语言 · 言語を選択 · 언어 선택</p>
      <div class="options" role="radiogroup" :aria-label="t('onboarding.languageTitle')">
        <button
          v-for="o in languages"
          :key="o.locale"
          type="button"
          role="radio"
          class="option"
          :class="{ 'option--on': picked === o.locale }"
          :aria-checked="picked === o.locale"
          @click="pick(o.locale)"
        >
          <span class="option__text">
            <span class="t-body-16-sb">{{ o.label }}</span>
            <span class="t-caption-13 muted">{{ t(`onboarding.languageName.${o.locale}`) }}</span>
          </span>
          <span class="radio" aria-hidden="true" />
        </button>
      </div>
      <p class="foot t-caption-12">{{ t('onboarding.languageNote') }}</p>
    </section>

    <section v-else class="content content--intro">
      <div class="hero">
        <span class="hero__icon"><AppIcon name="sparkles" /></span>
        <h1 class="t-title-22">{{ t('onboarding.heroTitle') }}</h1>
        <p class="t-body-15 sub">{{ t('onboarding.heroBody') }}</p>
      </div>
      <ul class="points">
        <li v-for="p in points" :key="p.key" class="point">
          <span class="point__icon"><AppIcon :name="p.icon" :size="20" /></span>
          <span>
            <span class="t-body-16-sb">{{ t(`onboarding.points.${p.key}.title`) }}</span>
            <span class="t-caption-13 sub">{{ t(`onboarding.points.${p.key}.body`) }}</span>
          </span>
        </li>
      </ul>
      <p class="notice t-caption-13">
        <AppIcon name="info" :size="16" />
        <span>{{ t('onboarding.notice') }}</span>
      </p>
    </section>

    <footer class="bottom">
      <AppButton v-if="step === 'language'" size="l" block @click="next">{{ t('onboarding.continue') }}</AppButton>
      <template v-else>
        <AppButton size="l" block @click="finish('/signup')">{{ t('onboarding.start') }}</AppButton>
        <AppButton variant="ghost" block @click="finish('/login')">{{ t('onboarding.haveAccount') }}</AppButton>
      </template>
    </footer>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100dvh; }
.content { display: flex; flex: 1; flex-direction: column; padding: var(--space-48) var(--space-24) var(--space-16); }
.content--intro { gap: var(--space-20); padding-top: var(--space-32); }
.logo { color: var(--text-brand); margin-bottom: var(--space-24); }
.sub { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.options { display: flex; flex-direction: column; gap: var(--space-12); margin-top: var(--space-32); }
.option {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  padding: var(--space-16);
  border: 1px solid var(--border-default);
  border-radius: 14px;
  background: var(--surface-card);
  text-align: left;
}
.option--on { border: 1.5px solid var(--brand-primary); background: var(--brand-subtle); }
.option__text { display: flex; flex: 1; flex-direction: column; gap: var(--space-2); }
.radio { width: 20px; height: 20px; border: 1.5px solid var(--border-strong); border-radius: 50%; background: var(--bg-default); }
.option--on .radio { border: 6px solid var(--brand-primary); }
.foot { margin-top: auto; color: var(--text-tertiary); }

.hero {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
  padding: var(--space-24);
  border-radius: 24px;
  background: var(--brand-subtle);
}
.hero__icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--brand-primary);
  color: var(--text-inverse);
}
.hero h1 { white-space: pre-line; }
.points { display: flex; flex-direction: column; gap: var(--space-16); margin: 0; padding: 0; list-style: none; }
.point { display: flex; gap: var(--space-12); }
.point > span:last-child { display: flex; flex-direction: column; gap: var(--space-2); }
.point__icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: 10px;
  background: var(--bg-subtle);
  color: var(--icon-default);
}
.notice {
  display: flex;
  gap: var(--space-8);
  margin-top: auto;
  padding: var(--space-12);
  border-radius: var(--radius-md);
  background: var(--status-info-bg);
  color: var(--status-info);
}
.notice .icon { margin-top: 1px; }
.bottom {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  padding: var(--space-12) var(--space-16) calc(var(--space-12) + env(safe-area-inset-bottom));
}
</style>
