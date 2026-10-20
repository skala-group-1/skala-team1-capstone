<script setup lang="ts">
// 「화면 목록」 C5 탐색 리스트 (Figma 1:5991) + C5-1 필터 시트 + 비교 바(≤3) + 04 ③ Skeleton·5xx + Edge ⑤ 0건(D-36)
// 정렬은 사용자가 고른 기준만 (D-01). 검색창은 시술 이름 → procedure 코드, 나머지 글자는 받은 결과에서 병원 이름으로 거름
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useSearchStore } from '@/stores/search'
import { catalogApi, toApiError, traceIdOf } from '@/api'
import { showToast } from '@/composables/useToast'
import { fmtDate, fmtKrwCompact } from '@/utils/format'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import HospitalCard from '@/components/HospitalCard.vue'
import FilterSheet from '@/components/explore/FilterSheet.vue'
import { SORT_BY, type HospitalSearchQuery, type ProcedureCode, type SortBy } from '@/types/contract'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const search = useSearchStore()

const text = ref('')
const suggestOpen = ref(false)
const sheetOpen = ref(false)
const failed = ref<string | null>(null)
const loadedOnce = ref(false)
/** Edge ⑤: 켜진 필터를 하나씩 뺐을 때 결과 수 */
const loosen = ref<{ key: keyof HospitalSearchQuery; label: string; total: number }[]>([])

const procedureName = (code?: ProcedureCode) => search.procedures.find((p) => p.code === code)?.name ?? ''
const suggestions = computed(() => {
  const q = text.value.trim().toLowerCase()
  if (!q || q === procedureName(search.query.procedure).toLowerCase()) return []
  return search.procedures.filter((p) => p.name.toLowerCase().includes(q)).slice(0, 6)
})
/** 시술로 못 찾은 글자는 병원 이름 필터 */
const nameFilter = computed(() => {
  const q = text.value.trim().toLowerCase()
  return q && q !== procedureName(search.query.procedure).toLowerCase() && !suggestions.value.length ? q : ''
})
const visible = computed(() => (nameFilter.value ? search.results.filter((h) => h.name.toLowerCase().includes(nameFilter.value)) : search.results))

const filterChips = computed(() => {
  const q = search.query
  const chips: { key: string; label: string; value: string }[] = []
  if (q.procedure) chips.push({ key: 'procedure', label: t('chat.cond.procedure'), value: procedureName(q.procedure) })
  if (q.areas?.length) chips.push({ key: 'areas', label: t('chat.cond.area'), value: q.areas.map((a) => t(`domain.area.${a}`)).join('·') })
  if (q.language) chips.push({ key: 'language', label: t('chat.cond.language'), value: t(`domain.lang.${q.language}`) })
  if (q.priceMax) chips.push({ key: 'priceMax', label: t('chat.cond.budget'), value: `~${fmtKrwCompact(q.priceMax)}` })
  if (q.dateFrom) chips.push({ key: 'dateFrom', label: t('chat.cond.date'), value: [q.dateFrom, q.dateTo].filter(Boolean).map((d) => fmtDate(d!, { weekday: false })).join('–') })
  return chips
})
const filterCount = computed(() => filterChips.value.length)

async function run(patch: Partial<HospitalSearchQuery> = {}) {
  failed.value = null
  loosen.value = []
  try {
    await search.search({ ...patch, page: 0 })
    if (search.total === 0) await computeLoosen()
  } catch (e) {
    failed.value = traceIdOf(e) ?? toApiError(e)?.traceId ?? ''
  } finally {
    loadedOnce.value = true
  }
}
async function computeLoosen() {
  const q = search.query
  const keys: { key: keyof HospitalSearchQuery; label: string; active: boolean; clear: Partial<HospitalSearchQuery> }[] = [
    { key: 'areas', label: t('explore.loosen.areas'), active: !!q.areas?.length, clear: { areas: [] } },
    { key: 'language', label: t('explore.loosen.language'), active: !!q.language, clear: { language: undefined } },
    { key: 'priceMax', label: t('explore.loosen.priceMax'), active: !!q.priceMax, clear: { priceMax: undefined } },
    { key: 'dateFrom', label: t('explore.loosen.dates'), active: !!q.dateFrom, clear: { dateFrom: undefined, dateTo: undefined } },
  ]
  const res = await Promise.all(
    keys
      .filter((k) => k.active)
      .map(async (k) => ({ key: k.key, label: k.label, total: await catalogApi.searchHospitals({ ...q, ...k.clear, page: 0, size: 1 }).then((p) => p.total).catch(() => 0) })),
  )
  loosen.value = res.filter((r) => r.total > 0)
}
function applyLoosen(key: keyof HospitalSearchQuery) {
  if (key === 'areas') void run({ areas: [] })
  else if (key === 'dateFrom') void run({ dateFrom: undefined, dateTo: undefined })
  else void run({ [key]: undefined })
}
function resetFilters() {
  void run({ areas: [], language: undefined, priceMax: undefined, dateFrom: undefined, dateTo: undefined })
}
function pickProcedure(code: ProcedureCode) {
  text.value = procedureName(code)
  suggestOpen.value = false
  void run({ procedure: code })
}
function clearText() {
  text.value = ''
  if (search.query.procedure) void run({ procedure: undefined })
}
function goCompare() {
  if (!search.query.procedure) {
    showToast(t('explore.compareNeedsProcedure'), 'info')
    sheetOpen.value = true
    return
  }
  void router.push({ path: '/compare', query: { ids: search.compareIds.join(','), procedure: search.query.procedure } })
}

onMounted(async () => {
  await search.loadProcedures().catch(() => undefined)
  const p = route.query.procedure as ProcedureCode | undefined
  if (p) text.value = procedureName(p)
  else if (search.query.procedure) text.value = procedureName(search.query.procedure)
  await run(p ? { procedure: p } : {})
})
watch(text, () => (suggestOpen.value = true))
</script>

<template>
  <div class="page">
    <header class="head">
      <h1 class="t-title-22">{{ t('nav.explore') }}</h1>
      <div class="searchbox">
        <AppIcon name="search" :size="20" />
        <input v-model="text" class="t-body-15" :placeholder="t('home.searchPlaceholder')" :aria-label="t('home.searchPlaceholder')" @focus="suggestOpen = true" />
        <button v-if="text" type="button" :aria-label="t('explore.clear')" @click="clearText"><AppIcon name="x" :size="18" /></button>
        <ul v-if="suggestOpen && suggestions.length" class="suggest" role="listbox">
          <li v-for="p in suggestions" :key="p.code">
            <button type="button" role="option" class="t-body-14" @click="pickProcedure(p.code)">{{ p.name }}</button>
          </li>
        </ul>
      </div>
      <div class="filters">
        <button type="button" class="filter-btn t-caption-13" :class="{ 'filter-btn--on': filterCount }" @click="sheetOpen = true">
          <AppIcon name="filter" :size="16" />{{ t('explore.filterN', { n: filterCount }) }}
        </button>
        <AppChip v-for="c in filterChips" :key="c.key" type="condition" :label="c.label" @click="sheetOpen = true">{{ c.value }}</AppChip>
      </div>
    </header>

    <!-- 04 ③ 로딩 Skeleton -->
    <div v-if="search.loading && !search.results.length" class="list" aria-busy="true">
      <div v-for="i in 3" :key="i" class="skeleton">
        <span class="bone bone--title" /><span class="bone bone--short" /><span class="bone" /><span class="bone bone--block" />
      </div>
    </div>

    <!-- 04 ③ 서버 오류 -->
    <EmptyState v-else-if="failed !== null" icon="alert-triangle" tone="danger" :title="t('explore.errorTitle')" :description="t('explore.errorBody')">
      <AppButton variant="secondary" icon="refresh-cw" @click="run()">{{ t('common.retry') }}</AppButton>
      <p v-if="failed" class="trace t-caption-12">traceId {{ failed }}</p>
    </EmptyState>

    <!-- Edge ⑤ 0건 (D-36) -->
    <section v-else-if="loadedOnce && !visible.length" class="no-result">
      <EmptyState icon="search" :title="t('explore.emptyTitle')" :description="t('explore.emptyBody')" />
      <button v-for="l in loosen" :key="l.key" type="button" class="loosen" @click="applyLoosen(l.key)">
        <span class="t-body-14-sb">{{ l.label }}</span>
        <span class="t-body-14-sb brand">{{ t('chat.relaxCount', { n: l.total }) }}</span>
        <AppIcon name="chevron-right" :size="18" />
      </button>
      <button v-if="filterCount > (search.query.procedure ? 1 : 0)" type="button" class="reset t-body-14" @click="resetFilters">
        {{ t('explore.filter.reset') }}
      </button>
    </section>

    <template v-else>
      <div class="meta">
        <span class="t-caption-13 secondary">{{ t('explore.count', { n: nameFilter ? visible.length : search.total }) }}</span>
        <label class="sort t-caption-13">
          <span class="sr-only">{{ t('chat.cond.sort') }}</span>
          <select :value="search.query.sort" @change="run({ sort: ($event.target as HTMLSelectElement).value as SortBy })">
            <option v-for="s in SORT_BY.filter((x) => x !== 'DISTANCE')" :key="s" :value="s">{{ t(`domain.sort.${s}`) }}</option>
          </select>
          <AppIcon name="chevron-down" :size="16" />
        </label>
      </div>
      <div class="list">
        <HospitalCard
          v-for="h in visible"
          :key="h.id"
          :card="h"
          :procedure-name="procedureName(search.query.procedure)"
          :compare-checked="search.compareIds.includes(h.id)"
          :compare-disabled="search.compareIds.length >= 3"
          @open="router.push(`/hospitals/${h.id}`)"
          @compare="search.toggleCompare(h.id)"
        />
      </div>
    </template>

    <div v-if="search.compareIds.length" class="compare-bar">
      <div>
        <p class="t-body-14-sb">{{ t('explore.selected', { n: search.compareIds.length }) }}</p>
        <p class="t-caption-12 muted">{{ t('explore.maxThree') }}</p>
      </div>
      <AppButton :disabled="search.compareIds.length < 2" @click="goCompare">{{ t('explore.compareGo') }}</AppButton>
    </div>

    <FilterSheet
      :open="sheetOpen"
      :query="search.query"
      :procedures="search.procedures"
      @close="sheetOpen = false"
      @apply="(q) => { sheetOpen = false; text = procedureName(q.procedure); run(q) }"
    />
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100%; }
.head { position: sticky; top: 0; z-index: 5; display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16) var(--space-16) var(--space-12); background: var(--bg-default); }
.searchbox { position: relative; display: flex; align-items: center; gap: var(--space-8); height: 48px; padding: 0 var(--space-16); border-radius: var(--radius-md); background: var(--bg-muted); color: var(--icon-subtle); }
.searchbox input { flex: 1; min-width: 0; border: 0; background: none; outline: none; color: var(--text-primary); }
.searchbox button { display: grid; place-items: center; border: 0; background: none; color: var(--icon-subtle); }
.suggest { position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 10; margin: 0; padding: var(--space-4); list-style: none; border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--surface-card); box-shadow: var(--shadow-toast); }
.suggest button { width: 100%; padding: var(--space-8) var(--space-12); border: 0; border-radius: var(--radius-sm); background: none; text-align: left; color: var(--text-primary); }
.suggest button:hover { background: var(--bg-muted); }
.filters { display: flex; gap: var(--space-8); margin: 0 -16px; padding: 0 var(--space-16); overflow-x: auto; scrollbar-width: none; }
.filter-btn { display: inline-flex; align-items: center; gap: var(--space-4); flex: none; height: 30px; padding: 0 10px; border: 1px solid var(--border-default); border-radius: var(--radius-full); background: var(--bg-default); color: var(--text-primary); font-weight: 600; }
.filter-btn--on { border-color: var(--brand-border); background: var(--brand-subtle); color: var(--brand-text); }
.meta { display: flex; align-items: center; justify-content: space-between; padding: var(--space-8) var(--space-16); }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.brand { color: var(--brand-text); }
.sort { position: relative; display: flex; align-items: center; gap: var(--space-4); color: var(--text-primary); }
.sort select { padding-right: 18px; border: 0; background: none; font-weight: 600; appearance: none; cursor: pointer; }
.sort .icon { position: absolute; right: 0; pointer-events: none; }
.list { display: flex; flex-direction: column; gap: var(--space-12); padding: 0 var(--space-16) var(--space-24); }
.skeleton { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); }
.bone { display: block; height: 10px; border-radius: var(--radius-xs); background: var(--bg-muted); animation: shimmer 1.2s ease-in-out infinite; }
.bone--title { width: 60%; height: 14px; }
.bone--short { width: 35%; }
.bone--block { height: 40px; border-radius: var(--radius-md); }
@keyframes shimmer { 50% { opacity: 0.5; } }
.trace { color: var(--text-tertiary); }
.no-result { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-24) var(--space-16); }
.loosen { display: flex; align-items: center; gap: var(--space-8); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--bg-default); text-align: left; }
.loosen > :first-child { flex: 1; }
.loosen .icon { color: var(--icon-subtle); }
.reset { align-self: center; padding: var(--space-8); border: 0; background: none; color: var(--text-secondary); }
.compare-bar {
  position: sticky;
  bottom: calc(var(--tab-bar-h) + env(safe-area-inset-bottom));
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding: var(--space-12) var(--space-16);
  border-top: 1px solid var(--border-default);
  background: var(--bg-default);
}
</style>
