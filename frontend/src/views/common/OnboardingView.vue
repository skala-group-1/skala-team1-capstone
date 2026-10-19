<script setup lang="ts">
// 「화면 목록」 C1 언어 선택/온보딩
// TODO(fe): 서비스 소개 1장, 재방문 시 스킵(localStorage 'onboarded')
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { setLocale } from '@/i18n'
import type { Locale } from '@/types/contract'

const router = useRouter()
const { t } = useI18n()
const options: { locale: Locale; label: string }[] = [
  { locale: 'en', label: 'English' },
  { locale: 'zh', label: '中文' },
  { locale: 'ja', label: '日本語' },
]

function choose(locale: Locale) {
  setLocale(locale)
  void router.push('/login')
}
</script>

<template>
  <section>
    <h1>C1 · {{ t('app.title') }}</h1>
    <p>{{ t('onboarding.notice') }}</p>
    <button v-for="o in options" :key="o.locale" type="button" @click="choose(o.locale)">{{ o.label }}</button>
  </section>
</template>
