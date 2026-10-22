<script setup lang="ts">
// 「화면 목록」 C7 병원 상세 (Figma 1:3330 시술·가격 · 1:3442 의료진 · 1:3545 리뷰 · 1:3720 정보) + C8 예약 시트
// /hospitals/:id/book 이면 예약 시트를 연 상태. ?procedure&option&slot&date&note 로 미리 채움 (만료 후 다시 요청, D-37)
// 하단 고정: "이 병원에 물어보기"(병원 대화, D-20) · "예약하기"
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { catalogApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { showToast } from '@/composables/useToast'
import { fmtDate, fmtKrw, mapUrl } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BookingSheet, { type BookingInitial } from '@/components/booking/BookingSheet.vue'
import type { HospitalDetail, ProcedureCategory, ProcedureCode, Reservation, Review } from '@/types/contract'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const auth = useAuthStore()

const id = computed(() => Number(route.params.id))
const hospital = ref<HospitalDetail | null>(null)
const failed = ref(false)
const tab = ref<'prices' | 'doctors' | 'reviews' | 'info'>((route.query.tab as 'prices') ?? 'prices')
const category = ref<ProcedureCategory | 'ALL'>('ALL')
const myLangOnly = ref(false)
const reviews = ref<Review[]>([])
const reviewTotal = ref(0)
const reviewProc = ref<ProcedureCode | 'ALL'>('ALL')

const bookingOpen = computed(() => route.path.endsWith('/book'))
const bookingInitial = computed<BookingInitial | null>(() => {
  const q = route.query
  if (!q.slot) return null
  return {
    procedure: q.procedure as ProcedureCode,
    optionId: q.option ? Number(q.option) : undefined,
    slotId: Number(q.slot),
    date: q.date as string | undefined,
    note: (q.note as string | undefined) ?? '',
  }
})

const langs = computed(() => hospital.value?.languages.filter((l) => l !== 'ko') ?? [])
const procedures = computed(() =>
  (hospital.value?.procedures ?? []).filter((p) => category.value === 'ALL' || p.procedure.category === category.value),
)
const myLang = computed(() => (auth.user?.locale && auth.user.locale !== 'ko' ? auth.user.locale : null))
const doctors = computed(() =>
  (hospital.value?.doctors ?? []).filter((d) => !myLangOnly.value || !myLang.value || d.languages.includes(myLang.value)),
)
const foreignDoctors = computed(() => (hospital.value?.doctors ?? []).filter((d) => d.languages.some((l) => l !== 'ko')).length)
const procName = (code: string) => hospital.value?.procedures.find((p) => p.procedure.code === code)?.procedure.name ?? code
const reviewProcs = computed(() => {
  const counts = new Map<ProcedureCode, number>()
  for (const r of reviews.value) counts.set(r.procedureCode, (counts.get(r.procedureCode) ?? 0) + 1)
  return [...counts.entries()]
})
const shownReviews = computed(() => reviews.value.filter((r) => reviewProc.value === 'ALL' || r.procedureCode === reviewProc.value))
const ageBars = computed(() => {
  const by = hospital.value?.reviewStats.byAgeGroup ?? {}
  const max = Math.max(1, ...Object.values(by))
  return Object.entries(by).map(([k, v]) => ({ k, v, pct: (v / max) * 100 }))
})

// 정보 탭: 같은 시간이 이어지는 요일은 묶음 (월–수)
const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const
const todayKey = computed(() => new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Seoul', weekday: 'short' }).format(new Date()).toLowerCase().slice(0, 3))
const dayName = (i: number) => new Intl.DateTimeFormat(locale.value, { weekday: 'short' }).format(new Date(`2026-10-${19 + i}T12:00:00+09:00`))
const hourRows = computed(() => {
  const oh = hospital.value?.openHours ?? {}
  const rows: { from: number; to: number; text: string; today: boolean }[] = []
  DAYS.forEach((d, i) => {
    const h = oh[d]
    const text = h ? `${h.open} – ${h.close}` : t('hospital.closed')
    const last = rows.at(-1)
    if (last && last.text === text && last.to === i - 1) last.to = i
    else rows.push({ from: i, to: i, text, today: false })
  })
  const ti = DAYS.indexOf(todayKey.value as (typeof DAYS)[number])
  rows.forEach((r) => (r.today = ti >= r.from && ti <= r.to))
  return rows
})
const openNow = computed(() => {
  const h = hospital.value?.openHours[todayKey.value as (typeof DAYS)[number]]
  if (!h) return false
  const hm = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit' }).format(new Date())
  return hm >= h.open && hm < h.close
})

async function load() {
  failed.value = false
  try {
    hospital.value = await catalogApi.hospital(id.value)
  } catch {
    failed.value = true
  }
}
async function loadReviews() {
  const page = await catalogApi.reviews(id.value, { page: 0, size: 50 }).catch(() => null)
  reviews.value = page?.items ?? []
  reviewTotal.value = page?.total ?? 0
}
async function copyAddress() {
  if (!hospital.value?.address) return
  await navigator.clipboard?.writeText(hospital.value.address).catch(() => undefined)
  showToast(t('hospital.copied'))
}
function openBooking() {
  void router.push(`/hospitals/${id.value}/book`)
}
function closeBooking() {
  void router.replace(`/hospitals/${id.value}`)
}
function booked(r: Reservation) {
  showToast(t('hospital.booked', { at: fmtDate(r.slot.startAt) }))
  void router.replace('/reservations')
}

onMounted(load)
// ?tab=reviews 로 바로 들어와도(예약 상세 → 병원 리뷰 보기) 불러오도록 immediate
watch(tab, (v) => v === 'reviews' && !reviews.value.length && void loadReviews(), { immediate: true })
watch(id, () => void load())
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('hospital.title')" back="/explore" />
    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('hospital.loadFailed')">
      <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
    </EmptyState>
    <template v-else-if="hospital">
      <header class="head">
        <h1 class="t-title-20">{{ hospital.name }}</h1>
        <p class="t-caption-13 muted">
          {{ t(`domain.area.${hospital.areaCode}`) }} · {{ t(`domain.category.${hospital.category}`) }}<template v-if="hospital.address"> · {{ hospital.address }}</template>
        </p>
        <p class="rating t-caption-13">
          <AppIcon name="star" :size="14" class="star" />
          <b>{{ hospital.reviewStats.avgRating?.toFixed(1) ?? '—' }}</b>
          <span class="muted">{{ t('domain.reviews', { n: hospital.reviewStats.reviewCount }) }}</span>
          <AppBadge v-for="l in langs" :key="l" tag>{{ t(`domain.lang.${l}`) }}</AppBadge>
          <AppBadge v-if="hospital.hasInterpreter" tag>{{ t('domain.interpreter') }}</AppBadge>
        </p>
      </header>

      <nav class="tabs" role="tablist">
        <button
          v-for="k in ['prices', 'doctors', 'reviews', 'info'] as const"
          :key="k"
          type="button"
          role="tab"
          class="tab t-body-14"
          :class="{ 'tab--on': tab === k }"
          :aria-selected="tab === k"
          @click="tab = k"
        >
          {{ k === 'reviews' ? t('hospital.tabs.reviewsN', { n: hospital.reviewStats.reviewCount }) : t(`hospital.tabs.${k}`) }}
        </button>
      </nav>

      <!-- 시술·가격 -->
      <section v-if="tab === 'prices'" class="body">
        <div class="chips">
          <AppChip v-for="c in ['ALL', 'SURGERY', 'SKIN'] as const" :key="c" :selected="category === c" @click="category = c">
            {{ c === 'ALL' ? t('hospital.all') : t(`home.category.${c}`) }}
          </AppChip>
        </div>
        <article v-for="p in procedures" :key="p.procedure.code" class="card">
          <header class="card__head">
            <h2 class="t-body-16-sb">{{ p.procedure.name }}</h2>
            <span class="t-caption-12 muted">{{ t('hospital.optionsN', { n: p.options.length }) }}</span>
          </header>
          <div v-for="o in p.options" :key="o.id" class="opt">
            <div>
              <p class="t-body-14">{{ o.product }}<template v-if="o.dose"> · {{ o.dose }}</template></p>
              <p class="t-caption-12 muted">{{ o.vatIncluded ? t('compare.vatIn') : t('compare.vatEx') }}<template v-if="o.conditions"> · {{ o.conditions }}</template></p>
            </div>
            <span class="opt__price t-body-16-sb">{{ fmtKrw(o.priceKrw) }}</span>
          </div>
          <p v-if="!p.options.length" class="t-body-14 warn">{{ t('common.needsCheck') }}</p>
        </article>
        <p class="t-caption-12 muted">{{ t('hospital.priceNote', { date: hospital.verifiedAt ?? t('domain.priceUnverified') }) }}</p>
      </section>

      <!-- 의료진 -->
      <section v-else-if="tab === 'doctors'" class="body">
        <div class="row-between">
          <span class="t-caption-13 secondary">{{ t('hospital.doctorsN', { n: hospital.doctors.length, m: foreignDoctors }) }}</span>
          <label v-if="myLang" class="check t-caption-13">
            <input v-model="myLangOnly" type="checkbox" />
            <span class="box" aria-hidden="true"><AppIcon v-if="myLangOnly" name="check" :size="14" /></span>
            {{ t('hospital.myLangOnly', { lang: t(`domain.langName.${myLang}`) }) }}
          </label>
        </div>
        <article v-for="d in doctors" :key="d.id" class="card doctor">
          <span class="avatar t-body-16-sb">{{ d.name.slice(0, 1) }}</span>
          <div class="doctor__body">
            <p class="t-body-16-sb">{{ d.name }} {{ d.title }}</p>
            <p class="t-caption-12 muted">{{ t('hospital.career', { n: d.careerYears }) }}</p>
            <p v-if="d.languages.some((l) => l !== 'ko')" class="langs t-caption-12">
              <span class="muted">{{ t('hospital.consultLang') }}</span>
              <AppBadge v-for="l in d.languages.filter((x) => x !== 'ko')" :key="l" tag>{{ t(`domain.lang.${l}`) }}</AppBadge>
            </p>
            <p v-else class="t-caption-12 muted">{{ hospital.hasInterpreter ? t('hospital.koOnlyInterp') : t('hospital.koOnly') }}</p>
            <p class="t-caption-12 secondary">{{ d.specialties.map(procName).join(' · ') }}</p>
          </div>
        </article>
      </section>

      <!-- 리뷰 -->
      <section v-else-if="tab === 'reviews'" class="body">
        <div class="card stats">
          <div class="stats__score">
            <span class="t-display-28">{{ hospital.reviewStats.avgRating?.toFixed(1) ?? '—' }}</span>
            <span class="stars" aria-hidden="true">
              <AppIcon v-for="i in 5" :key="i" name="star" :size="14" :class="{ star: i <= Math.round(hospital.reviewStats.avgRating ?? 0) }" />
            </span>
            <span class="t-caption-12 muted">{{ t('domain.reviews', { n: hospital.reviewStats.reviewCount }) }}</span>
          </div>
          <ul class="bars">
            <li v-for="b in ageBars" :key="b.k" class="t-caption-12">
              <span class="muted">{{ t('hospital.age', { age: b.k }) }}</span>
              <span class="age-bar"><i :style="{ width: `${b.pct}%` }" /></span>
              <span class="muted">{{ b.v }}</span>
            </li>
          </ul>
        </div>
        <div class="chips">
          <AppChip :selected="reviewProc === 'ALL'" @click="reviewProc = 'ALL'">{{ t('hospital.all') }}</AppChip>
          <AppChip v-for="[code, n] in reviewProcs" :key="code" :selected="reviewProc === code" @click="reviewProc = code">{{ procName(code) }} {{ n }}</AppChip>
        </div>
        <article v-for="r in shownReviews" :key="r.id" class="review">
          <header class="row-between">
            <span class="review__stars">
              <AppIcon v-for="i in 5" :key="i" name="star" :size="14" :class="{ star: i <= r.rating }" />
              <b class="t-caption-13">{{ procName(r.procedureCode) }}</b>
            </span>
            <span class="t-caption-12 muted">{{ fmtDate(r.createdAt, { weekday: false, year: true }) }}</span>
          </header>
          <p class="t-caption-12 muted">
            {{ t('hospital.age', { age: r.ageGroup }) }} · {{ t(`signup.genders.${r.gender}`) }}<template v-if="r.reviewerNationality"> · {{ new Intl.DisplayNames([locale], { type: 'region' }).of(r.reviewerNationality) }}</template>
          </p>
          <p class="t-body-14">{{ r.content }}</p>
          <p class="t-caption-11 muted"><AppIcon name="languages" :size="12" /> {{ t('hospital.writtenIn', { lang: t(`domain.langName.${r.lang}`) }) }}</p>
        </article>
        <EmptyState v-if="!shownReviews.length" icon="star" :title="t('hospital.noReviews')" />
      </section>

      <!-- 정보 -->
      <section v-else class="body">
        <article class="card">
          <header class="card__head">
            <h2 class="t-body-16-sb"><AppIcon name="clock" :size="18" /> {{ t('hospital.hours') }}</h2>
            <AppBadge :tone="openNow ? 'success' : 'neutral'">{{ openNow ? t('hospital.openNow') : t('hospital.closedNow') }}</AppBadge>
          </header>
          <dl class="hours">
            <div v-for="r in hourRows" :key="r.from" :class="{ today: r.today }">
              <dt class="t-body-14">{{ r.from === r.to ? dayName(r.from) : `${dayName(r.from)}–${dayName(r.to)}` }}</dt>
              <dd class="t-body-14">{{ r.text }}</dd>
            </div>
          </dl>
          <p class="t-caption-12 muted">{{ t('hospital.holidayNote') }}</p>
        </article>
        <article class="card">
          <h2 class="t-body-16-sb"><AppIcon name="map-pin" :size="18" /> {{ t('hospital.location') }}</h2>
          <p class="t-body-14-sb">{{ hospital.address ?? t('common.needsCheck') }}</p>
          <div v-if="hospital.address" class="btns">
            <AppButton variant="outline" size="s" block @click="copyAddress">{{ t('hospital.copyAddress') }}</AppButton>
            <a :href="mapUrl(hospital.address)" target="_blank" rel="noopener" class="map-link t-caption-13">{{ t('hospital.openMap') }}</a>
          </div>
        </article>
        <article class="card">
          <h2 class="t-body-16-sb"><AppIcon name="globe" :size="18" /> {{ t('hospital.contact') }}</h2>
          <dl class="kv">
            <div><dt>{{ t('hospital.consultLang') }}</dt><dd>{{ hospital.languages.map((l) => t(`domain.langName.${l}`)).join(' · ') }}</dd></div>
            <div><dt>{{ t('domain.interpreter') }}</dt><dd>{{ hospital.hasInterpreter ? t('compare.interpreterYes') : t('compare.interpreterNo') }}</dd></div>
            <div><dt>{{ t('hospital.phone') }}</dt><dd><a v-if="hospital.phone" :href="`tel:${hospital.phone}`">{{ hospital.phone }}</a><template v-else>—</template></dd></div>
          </dl>
        </article>
        <p class="t-caption-12 muted">{{ t('hospital.verified', { date: hospital.verifiedAt ?? t('domain.priceUnverified') }) }}</p>
      </section>

      <footer class="bottom">
        <AppButton variant="outline" size="l" block @click="router.push({ path: '/chat', query: { hospitalId: hospital.id } })">{{ t('hospital.ask') }}</AppButton>
        <AppButton size="l" block @click="openBooking">{{ t('chat.book') }}</AppButton>
      </footer>
      <BookingSheet :open="bookingOpen" :hospital="hospital" :initial="bookingInitial" @close="closeBooking" @done="booked" />
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100dvh; }
.head { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-8) var(--space-16) var(--space-16); }
.muted { color: var(--text-tertiary); }
.secondary { color: var(--text-secondary); }
.warn { color: var(--status-warning); }
.rating { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-4); }
.star { color: var(--rating-star); fill: var(--rating-star); }
.tabs { position: sticky; top: var(--app-bar-h); z-index: 4; display: flex; border-bottom: 1px solid var(--border-default); background: var(--bg-default); }
.tab { flex: 1; height: 44px; border: 0; border-bottom: 2px solid transparent; background: none; color: var(--text-tertiary); }
.tab--on { border-bottom-color: var(--brand-primary); color: var(--brand-text); font-weight: 600; }
.body { display: flex; flex: 1; flex-direction: column; gap: var(--space-12); padding: var(--space-16) var(--space-16) 100px; background: var(--bg-subtle); }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.card { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.card h2 { display: flex; align-items: center; gap: var(--space-6); }
.card__head { display: flex; align-items: center; justify-content: space-between; }
.opt { display: flex; justify-content: space-between; gap: var(--space-12); padding-top: var(--space-12); border-top: 1px solid var(--border-default); }
.opt:nth-child(2) { padding-top: 0; border-top: 0; }
.opt__price { flex: none; white-space: nowrap; }
.row-between { display: flex; align-items: center; justify-content: space-between; gap: var(--space-8); }
.check { position: relative; display: flex; align-items: center; gap: var(--space-6); cursor: pointer; }
.check input { position: absolute; opacity: 0; }
.box { display: grid; place-items: center; width: 18px; height: 18px; border: 1.5px solid var(--border-strong); border-radius: var(--radius-xs); color: var(--text-inverse); }
.check input:checked + .box { border-color: var(--brand-primary); background: var(--brand-primary); }
.doctor { flex-direction: row; gap: var(--space-12); }
.avatar { display: grid; place-items: center; flex: none; width: 40px; height: 40px; border-radius: 50%; background: var(--brand-subtle); color: var(--brand-text); }
.doctor__body { display: flex; flex-direction: column; gap: var(--space-4); }
.langs { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-4); }
.stats { flex-direction: row; align-items: center; gap: var(--space-20); }
.stats__score { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.stars, .review__stars { display: inline-flex; align-items: center; gap: 1px; color: var(--border-strong); }
.review__stars b { margin-left: var(--space-6); color: var(--text-primary); }
.bars { display: flex; flex: 1; flex-direction: column; gap: var(--space-6); margin: 0; padding: 0; list-style: none; }
.bars li { display: grid; grid-template-columns: 40px 1fr 28px; align-items: center; gap: var(--space-8); }
.age-bar { height: 6px; border-radius: 3px; background: var(--bg-muted); overflow: hidden; }
.age-bar i { display: block; height: 100%; background: var(--rating-star); }
.review { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-16) 0; border-bottom: 1px solid var(--border-default); }
.hours { display: flex; flex-direction: column; gap: var(--space-8); margin: 0; }
.hours div { display: grid; grid-template-columns: 72px 1fr; }
.hours dt { color: var(--text-secondary); }
.hours dd { margin: 0; }
.hours .today dt, .hours .today dd { color: var(--brand-text); font-weight: 600; }
.btns { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-8); }
.map-link { display: grid; place-items: center; height: 36px; border: 1px solid var(--border-strong); border-radius: var(--radius-sm); color: var(--text-primary); }
.kv { display: flex; flex-direction: column; gap: var(--space-8); margin: 0; }
.kv div { display: grid; grid-template-columns: 72px 1fr; font: 400 14px/20px var(--font-sans); }
.kv dt { color: var(--text-tertiary); }
.kv dd { margin: 0; }
.bottom {
  position: fixed;
  bottom: 0;
  left: 50%;
  z-index: 10;
  display: flex;
  gap: var(--space-8);
  width: 100%;
  max-width: 480px;
  padding: var(--space-12) var(--space-16) calc(var(--space-12) + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  border-top: 1px solid var(--border-default);
  background: var(--bg-default);
}
</style>
