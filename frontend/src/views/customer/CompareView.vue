<script setup lang="ts">
// 「화면 목록」 C6 비교표 (Figma 1:6502, /compare?ids=&procedure=): 최대 3열 — 가격 옵션 · 상담 언어 · 가장 빠른 예약 · 리뷰 · 가격 확인일
// 값이 null 이면 "확인 필요"/"미확인". 순위·추천 표시 없음 (D-01)
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useSearchStore } from '@/stores/search'
import { fmtDateTime, fmtKrw } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import type { ProcedureCode } from '@/types/contract'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const search = useSearchStore()
const failed = ref(false)

const procedure = computed(() => (route.query.procedure as ProcedureCode | undefined) ?? null)
const procedureName = computed(() => search.procedures.find((p) => p.code === procedure.value)?.name ?? '')
const columns = computed(() => search.compare?.columns ?? [])
const cheapest = <T extends { priceKrw: number }>(opts: T[]): T | null => [...opts].sort((a, b) => a.priceKrw - b.priceKrw)[0] ?? null

async function load() {
  failed.value = false
  const ids = String(route.query.ids ?? '').split(',').map(Number).filter(Boolean)
  if (ids.length) search.compareIds = ids.slice(0, 3)
  if (!procedure.value || !search.compareIds.length) return
  try {
    await search.loadCompare(procedure.value)
  } catch {
    failed.value = true
  }
}
async function remove(id: number) {
  search.toggleCompare(id)
  await router.replace({ query: { ...route.query, ids: search.compareIds.join(',') } })
  if (search.compareIds.length) await load()
  else search.compare = null
}
function askAi() {
  const names = columns.value.map((c) => c.hospital.name).join(', ')
  void router.push({ path: '/chat', query: { q: t('compare.askAiMessage', { names, procedure: procedureName.value }) } })
}
onMounted(async () => {
  await search.loadProcedures().catch(() => undefined)
  await load()
})
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('compare.title', { procedure: procedureName })" back="/explore" />
    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('explore.errorTitle')">
      <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
    </EmptyState>
    <EmptyState v-else-if="!columns.length" icon="columns" :title="t('compare.emptyTitle')" :description="t('compare.emptyBody')">
      <AppButton variant="secondary" @click="router.push('/explore')">{{ t('nav.explore') }}</AppButton>
    </EmptyState>
    <template v-else>
      <div class="table" :style="{ '--cols': columns.length }">
        <div class="heads">
          <div v-for="c in columns" :key="c.hospital.id" class="head">
            <RouterLink :to="`/hospitals/${c.hospital.id}`" class="t-body-14-sb">{{ c.hospital.name }}</RouterLink>
            <span class="t-caption-12 muted">{{ t(`domain.area.${c.hospital.areaCode}`) }}</span>
            <button type="button" class="remove" :aria-label="t('compare.remove')" @click="remove(c.hospital.id)"><AppIcon name="x" :size="16" /></button>
          </div>
        </div>

        <section class="row">
          <h2 class="t-caption-12-sb label">{{ t('compare.priceOptions') }}</h2>
          <div class="cells">
            <div v-for="c in columns" :key="c.hospital.id" class="cell">
              <template v-if="cheapest(c.options)">
                <p class="t-body-16-sb">{{ fmtKrw(cheapest(c.options)!.priceKrw) }}</p>
                <p class="t-caption-12 secondary">{{ cheapest(c.options)!.product }}<template v-if="cheapest(c.options)!.dose"> · {{ cheapest(c.options)!.dose }}</template></p>
                <p class="t-caption-12 muted">{{ cheapest(c.options)!.vatIncluded ? t('compare.vatIn') : t('compare.vatEx') }}</p>
                <p v-if="cheapest(c.options)!.conditions" class="t-caption-12 muted">{{ cheapest(c.options)!.conditions }}</p>
                <p v-if="c.options.length > 1" class="t-caption-12-sb brand">{{ t('compare.moreOptions', { n: c.options.length - 1 }) }}</p>
                <p v-if="!c.verifiedAt" class="warn t-caption-11"><AppIcon name="alert-triangle" :size="12" />{{ t('compare.priceNeedsCheck') }}</p>
              </template>
              <p v-else class="t-body-14-sb warnText">{{ t('common.needsCheck') }}</p>
            </div>
          </div>
        </section>
        <section class="row">
          <h2 class="t-caption-12-sb label">{{ t('compare.languages') }}</h2>
          <div class="cells">
            <div v-for="c in columns" :key="c.hospital.id" class="cell">
              <p class="t-body-14-sb">{{ c.hospital.languages.filter((l) => l !== 'ko').map((l) => t(`domain.lang.${l}`)).join(' · ') || '—' }}</p>
              <p class="t-caption-12" :class="c.hospital.hasInterpreter ? 'ok' : 'muted'">
                {{ c.hospital.hasInterpreter ? t('compare.interpreterYes') : t('compare.interpreterNo') }}
              </p>
            </div>
          </div>
        </section>
        <section class="row">
          <h2 class="t-caption-12-sb label">{{ t('compare.earliest') }}</h2>
          <div class="cells">
            <p v-for="c in columns" :key="c.hospital.id" class="cell t-body-14-sb">{{ c.earliestSlotAt ? fmtDateTime(c.earliestSlotAt) : t('domain.noSlot') }}</p>
          </div>
        </section>
        <section class="row">
          <h2 class="t-caption-12-sb label">{{ t('compare.reviews') }}</h2>
          <div class="cells">
            <p v-for="c in columns" :key="c.hospital.id" class="cell t-body-14-sb">
              <AppIcon name="star" :size="14" class="star" /> {{ c.hospital.rating?.toFixed(1) ?? '—' }} · {{ c.hospital.reviewCount }}
            </p>
          </div>
        </section>
        <section class="row">
          <h2 class="t-caption-12-sb label">{{ t('compare.verifiedAt') }}</h2>
          <div class="cells">
            <p v-for="c in columns" :key="c.hospital.id" class="cell t-body-14" :class="{ warnText: !c.verifiedAt }">
              {{ c.verifiedAt ?? t('domain.priceUnverified') }}
            </p>
          </div>
        </section>
      </div>
      <p class="notice t-caption-13"><AppIcon name="info" :size="16" />{{ t('compare.notice') }}</p>
      <footer class="bottom">
        <AppButton variant="secondary" size="l" block @click="askAi">{{ t('compare.askAi') }}</AppButton>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100dvh; }
.table { display: flex; flex-direction: column; padding: 0 var(--space-16); }
.heads, .cells { display: grid; grid-template-columns: repeat(var(--cols), minmax(0, 1fr)); gap: var(--space-8); }
.heads { padding: var(--space-8) 0 var(--space-16); }
.head { position: relative; display: flex; flex-direction: column; gap: var(--space-4); min-height: 88px; padding: var(--space-12); padding-right: 28px; border-radius: var(--radius-md); background: var(--bg-subtle); }
.remove { position: absolute; top: 8px; right: 8px; border: 0; background: none; color: var(--icon-subtle); }
.row { display: flex; flex-direction: column; gap: var(--space-8); padding: var(--space-12) 0; border-top: 1px solid var(--border-default); }
.label { color: var(--text-secondary); }
.cell { display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; word-break: break-word; }
p.cell { display: block; }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.brand { color: var(--brand-text); }
.ok { color: var(--status-success); }
.warnText { color: var(--status-warning); }
.warn { display: inline-flex; align-items: center; gap: var(--space-2); align-self: flex-start; margin-top: var(--space-4); padding: 2px 6px; border-radius: var(--radius-xs); background: var(--status-warning-bg); color: var(--status-warning); }
.star { color: var(--rating-star); fill: var(--rating-star); vertical-align: -2px; }
.notice { display: flex; gap: var(--space-8); margin: var(--space-16); padding: var(--space-12); border-radius: var(--radius-md); background: var(--status-info-bg); color: var(--status-info); }
.bottom { margin-top: auto; padding: var(--space-12) var(--space-16) calc(var(--space-12) + env(safe-area-inset-bottom)); }
</style>
