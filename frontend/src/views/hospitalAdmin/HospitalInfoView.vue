<script setup lang="ts">
// 「화면 목록」 H3-D 병원 정보 (04 ④ 40:1030, /hospital-admin/hospital): 읽기 전용 — 기본 정보 · 진료 시간 · 의료진
// 데이터: GET /api/hospitals/{token.hospitalId}. 수정은 운영팀 요청 (H-03 P1)
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { catalogApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import EmptyState from '@/components/ui/EmptyState.vue'
import AppButton from '@/components/ui/AppButton.vue'
import type { HospitalDetail } from '@/types/contract'

const { t, locale } = useI18n()
const auth = useAuthStore()
const h = ref<HospitalDetail | null>(null)
const failed = ref(false)

const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const
const dayName = (i: number) => new Intl.DateTimeFormat(locale.value, { weekday: 'short' }).format(new Date(`2026-10-${19 + i}T12:00:00+09:00`))
const hours = computed(() => {
  const rows: { from: number; to: number; text: string }[] = []
  DAYS.forEach((d, i) => {
    const v = h.value?.openHours[d]
    const text = v ? `${v.open} – ${v.close}` : t('hospital.closed')
    const last = rows.at(-1)
    if (last && last.text === text && last.to === i - 1) last.to = i
    else rows.push({ from: i, to: i, text })
  })
  return rows
})

async function load() {
  failed.value = false
  try {
    if (auth.user?.hospitalId) h.value = await catalogApi.hospital(auth.user.hospitalId)
  } catch {
    failed.value = true
  }
}
onMounted(load)
</script>

<template>
  <div class="page">
    <header class="title">
      <h1 class="t-title-22">{{ t('staff.nav.hospital') }}</h1>
      <p class="t-body-14 secondary">{{ t('staff.hospital.sub') }}</p>
    </header>
    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('staff.loadFailed')">
      <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
    </EmptyState>
    <div v-else-if="h" class="cards">
      <section class="card">
        <div>
          <h2 class="t-title-18">{{ h.nameKo ?? h.name }}</h2>
          <p class="t-caption-12 muted">{{ h.name }}</p>
        </div>
        <dl class="kv">
          <div><dt>{{ t('staff.hospital.category') }}</dt><dd>{{ t(`domain.category.${h.category}`) }}</dd></div>
          <div><dt>{{ t('chat.cond.area') }}</dt><dd>{{ t(`domain.area.${h.areaCode}`) }}</dd></div>
          <div><dt>{{ t('staff.hospital.address') }}</dt><dd>{{ h.address ?? '—' }}</dd></div>
          <div><dt>{{ t('hospital.phone') }}</dt><dd>{{ h.phone ?? '—' }}</dd></div>
          <div><dt>{{ t('hospital.consultLang') }}</dt><dd>{{ h.languages.map((l) => t(`domain.langName.${l}`)).join(' · ') }}</dd></div>
          <div><dt>{{ t('domain.interpreter') }}</dt><dd>{{ h.hasInterpreter ? t('compare.interpreterYes') : t('compare.interpreterNo') }}</dd></div>
          <div><dt>{{ t('staff.hospital.verifiedAt') }}</dt><dd>{{ h.verifiedAt ?? '—' }}</dd></div>
        </dl>
      </section>
      <section class="card">
        <h2 class="t-title-18">{{ t('hospital.hours') }}</h2>
        <dl class="kv">
          <div v-for="r in hours" :key="r.from">
            <dt>{{ r.from === r.to ? dayName(r.from) : `${dayName(r.from)} – ${dayName(r.to)}` }}</dt>
            <dd>{{ r.text }}</dd>
          </div>
        </dl>
      </section>
      <section class="card">
        <h2 class="t-title-18">{{ t('staff.hospital.doctors', { n: h.doctors.length }) }}</h2>
        <dl class="kv">
          <div v-for="d in h.doctors" :key="d.id">
            <dt>{{ d.name }}</dt>
            <dd>{{ d.title }} · {{ t('hospital.career', { n: d.careerYears }) }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: var(--space-20); padding: var(--space-32); }
.title { display: flex; flex-direction: column; gap: var(--space-4); }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-16); align-items: start; }
.card { display: flex; flex-direction: column; gap: var(--space-16); padding: var(--space-20); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.kv { display: flex; flex-direction: column; gap: var(--space-12); margin: 0; }
.kv div { display: grid; grid-template-columns: 84px 1fr; font: 600 14px/20px var(--font-sans); }
.kv dt { font-weight: 400; color: var(--text-tertiary); }
.kv dd { margin: 0; }
</style>
