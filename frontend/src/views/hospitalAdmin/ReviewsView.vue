<script setup lang="ts">
// H5-D 리뷰 관리 (Figma 209:3128) + H5-1-D 숨기기 모달: 요약(평균·점수 분포) + 탭·언어·정렬 + 리뷰 카드 목록 + 오른쪽 답글 패널(400)
// 숨김은 운영팀 검토 없이 바로 (고객 목록·통계에서 빠짐, 삭제 아님). 답글은 리뷰당 1개, 고객 언어로 번역됨
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { hospitalAdminApi } from '@/api'
import { showToast } from '@/composables/useToast'
import { fmtDate } from '@/utils/format'
import ReviewHideModal from '@/components/staff/ReviewHideModal.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import type { AdminReview, HideRequest, Locale, ReviewFilter, ReviewSort, ReviewSummary } from '@/types/contract'

const { t, locale } = useI18n()
const FILTERS: ReviewFilter[] = ['ALL', 'UNREPLIED', 'LOW', 'HIDDEN']
const SORTS: ReviewSort[] = ['LATEST', 'RATING_LOW', 'RATING_HIGH']
const LANGS: Locale[] = ['ko', 'en', 'zh', 'ja']
const PAGE_SIZE = 20

const items = ref<AdminReview[]>([])
const total = ref(0)
const page = ref(0)
const summary = ref<ReviewSummary | null>(null)
const failed = ref(false)
const loading = ref(true)
const moreLoading = ref(false)
const filter = ref<ReviewFilter>('ALL')
const lang = ref<Locale | ''>('')
const sort = ref<ReviewSort>('LATEST')
const selectedId = ref<number | null>(null)
const draft = ref('')
const busy = ref<'reply' | 'delete' | 'hide' | null>(null)
const hideOpen = ref(false)
const deleteOpen = ref(false)
let request = 0

const selected = computed(() => items.value.find((r) => r.id === selectedId.value) ?? null)
watch(selected, (r) => (draft.value = r?.reply?.content ?? ''), { immediate: true })
const filterCount = (f: ReviewFilter) =>
  !summary.value ? '' : { ALL: summary.value.reviewCount, UNREPLIED: summary.value.unreplied, LOW: summary.value.lowRating, HIDDEN: summary.value.hidden }[f]
const maxBar = computed(() => Math.max(1, ...Object.values(summary.value?.byRating ?? {})))
const nation = (code: string | null) => (code ? (new Intl.DisplayNames([locale.value], { type: 'region' }).of(code) ?? code) : '')
const meta = (r: AdminReview) =>
  [nation(r.reviewerNationality), r.ageGroup ? t('hospital.age', { age: r.ageGroup.replace(/s$/, '') }) : '', r.gender ? t(`signup.genders.${r.gender}`) : '', t(`domain.langName.${r.lang}`)]
    .filter(Boolean)
    .join(' · ')
const replyLangs = (r: AdminReview) => Object.keys(r.reply?.translations ?? {}).map((l) => t(`domain.langName.${l}`)).join(', ')
const canReply = computed(() => !!draft.value.trim() && draft.value.trim() !== (selected.value?.reply?.content ?? '') && !busy.value)

async function load(more = false) {
  const req = ++request
  const next = more ? page.value + 1 : 0
  if (more) moreLoading.value = true
  else failed.value = false
  try {
    const res = await hospitalAdminApi.reviews({ filter: filter.value, lang: lang.value || undefined, sort: sort.value, page: next, size: PAGE_SIZE })
    if (req !== request) return
    items.value = more ? [...items.value, ...res.items] : res.items
    total.value = res.total
    page.value = next
    summary.value = res.summary
  } catch {
    if (req === request && !more) failed.value = true
    else if (req === request) showToast(t('common.error'), 'error')
  } finally {
    if (req === request) {
      loading.value = false
      moreLoading.value = false
    }
  }
}
/** 답글·숨김 뒤 요약 숫자만 다시 받는다 (목록은 바뀐 행만 교체) */
async function refreshSummary() {
  summary.value = (await hospitalAdminApi.reviews({ size: 1 }).catch(() => null))?.summary ?? summary.value
}
function replace(r: AdminReview) {
  const i = items.value.findIndex((x) => x.id === r.id)
  if (i >= 0) items.value[i] = r
}
async function run(kind: 'reply' | 'delete' | 'hide', action: () => Promise<AdminReview | void>, toast: string) {
  busy.value = kind
  try {
    const r = await action()
    if (r) replace(r)
    showToast(t(toast))
    void refreshSummary()
    return true
  } catch {
    showToast(t('common.error'), 'error')
    return false
  } finally {
    busy.value = null
  }
}
const submitReply = () => selected.value && run('reply', () => hospitalAdminApi.replyReview(selected.value!.id, draft.value.trim()), 'reviewAdmin.toast.replied')
async function deleteReply() {
  const r = selected.value
  if (!r) return
  const ok = await run('delete', () => hospitalAdminApi.deleteReply(r.id), 'reviewAdmin.toast.deleted')
  if (ok) replace({ ...r, reply: null })
  deleteOpen.value = false
}
async function hide(body: HideRequest) {
  const r = selected.value
  if (r && (await run('hide', () => hospitalAdminApi.hideReview(r.id, body), 'reviewAdmin.toast.hidden'))) hideOpen.value = false
}
const unhide = () => selected.value && run('hide', () => hospitalAdminApi.unhideReview(selected.value!.id), 'reviewAdmin.toast.unhidden')

onMounted(() => load())
watch([filter, lang, sort], () => {
  selectedId.value = null
  void load()
})
</script>

<template>
  <div class="layout">
    <div class="main">
      <header class="title">
        <h1 class="t-title-22">{{ t('reviewAdmin.nav') }}</h1>
        <p class="t-body-14 secondary">{{ t('reviewAdmin.sub') }}</p>
      </header>
      <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('staff.loadFailed')">
        <AppButton variant="secondary" icon="refresh-cw" @click="load()">{{ t('common.retry') }}</AppButton>
      </EmptyState>
      <template v-else>
        <section v-if="summary" class="summary">
          <div class="avg">
            <span class="t-display-28">{{ summary.avgRating?.toFixed(1) ?? '–' }}</span>
            <span class="stars" aria-hidden="true"><AppIcon v-for="i in 5" :key="i" name="star" :size="18" :class="{ on: i <= Math.round(summary.avgRating ?? 0) }" /></span>
            <span class="t-caption-12 muted">{{ t('reviewAdmin.reviews', { n: summary.reviewCount.toLocaleString() }) }}</span>
          </div>
          <div class="bars">
            <!-- 숫자 키 객체는 JS 에서 항상 오름차순이라 5→1 을 직접 돈다 -->
            <div v-for="s in [5, 4, 3, 2, 1]" :key="s" class="bar t-caption-12">
              <span class="muted">{{ t('reviewAdmin.stars', { n: s }) }}</span>
              <span class="track"><span class="fill" :class="{ low: s <= 2 }" :style="{ width: `${((summary.byRating[s] ?? 0) / maxBar) * 100}%` }" /></span>
              <span class="muted num">{{ (summary.byRating[s] ?? 0).toLocaleString() }}</span>
            </div>
          </div>
          <dl class="kv">
            <div><dt>{{ t('reviewAdmin.kpi.unreplied') }}</dt><dd class="warn">{{ t('reviewAdmin.kpi.count', { n: summary.unreplied.toLocaleString() }) }}</dd></div>
            <div><dt>{{ t('reviewAdmin.kpi.hidden') }}</dt><dd>{{ t('reviewAdmin.kpi.count', { n: summary.hidden }) }}</dd></div>
            <div><dt>{{ t('reviewAdmin.kpi.thisMonth') }}</dt><dd>{{ t('reviewAdmin.kpi.count', { n: summary.thisMonth }) }}</dd></div>
          </dl>
        </section>
        <div class="toolbar">
          <AppChip v-for="f in FILTERS" :key="f" :selected="filter === f" @click="filter = f">{{ t(`reviewAdmin.filters.${f}`) }} {{ filterCount(f) }}</AppChip>
          <span class="spacer" />
          <label class="select">
            <AppIcon name="globe" :size="16" />
            <select v-model="lang" class="t-caption-13" :aria-label="t('reviewAdmin.langAll')">
              <option value="">{{ t('reviewAdmin.langAll') }}</option>
              <option v-for="l in LANGS" :key="l" :value="l">{{ t(`domain.langName.${l}`) }}</option>
            </select>
          </label>
          <label class="select">
            <AppIcon name="filter" :size="16" />
            <select v-model="sort" class="t-caption-13" :aria-label="t('reviewAdmin.sort.LATEST')">
              <option v-for="s in SORTS" :key="s" :value="s">{{ t(`reviewAdmin.sort.${s}`) }}</option>
            </select>
          </label>
        </div>
        <div v-if="items.length" class="list">
          <button v-for="r in items" :key="r.id" type="button" class="card" :class="{ 'card--on': r.id === selectedId, 'card--hidden': r.hidden }" @click="selectedId = r.id">
            <span class="card__head">
              <span class="stars" :aria-label="t('reviewAdmin.detail.point', { n: r.rating })"><AppIcon v-for="i in 5" :key="i" name="star" :size="14" :class="{ on: i <= r.rating }" /></span>
              <AppBadge v-if="r.procedureName" tag>{{ r.procedureName }}</AppBadge>
              <span class="t-caption-12 muted">{{ meta(r) }}</span>
              <span class="spacer" />
              <span class="t-caption-12 muted">{{ fmtDate(r.createdAt, { weekday: false }) }}</span>
            </span>
            <span class="t-body-14 text">{{ r.content }}</span>
            <span v-if="r.translatedContent" class="t-caption-13 muted translated"><AppIcon name="languages" :size="14" />{{ t('reviewAdmin.translated') }} · {{ r.translatedContent }}</span>
            <span class="card__foot">
              <AppBadge v-if="r.hidden" tone="neutral" icon="eye-off">{{ t('reviewAdmin.hiddenBadge') }}</AppBadge>
              <AppBadge v-else-if="r.reply" tone="success" dot>{{ t('reviewAdmin.replied') }}</AppBadge>
              <AppBadge v-else tone="warning" dot>{{ t('reviewAdmin.unreplied') }}</AppBadge>
              <span class="spacer" />
              <span class="action t-body-14"><AppIcon name="message-circle" :size="16" />{{ r.reply ? t('reviewAdmin.viewReply') : t('reviewAdmin.reply') }}</span>
            </span>
          </button>
          <AppButton v-if="items.length < total" variant="outline" block :loading="moreLoading" @click="load(true)">{{ t('reviewAdmin.more') }} ({{ items.length }}/{{ total }})</AppButton>
        </div>
        <EmptyState v-else-if="!loading" icon="star" :title="t('reviewAdmin.empty')" />
      </template>
    </div>

    <!-- 답글 패널 -->
    <aside v-if="selected" class="panel">
      <header class="panel__head">
        <h2 class="t-body-16-sb">{{ t('reviewAdmin.detail.title') }}</h2>
        <button type="button" class="x" :aria-label="t('common.close')" @click="selectedId = null"><AppIcon name="x" :size="20" /></button>
      </header>
      <p class="rating">
        <span class="stars" aria-hidden="true"><AppIcon v-for="i in 5" :key="i" name="star" :size="18" :class="{ on: i <= selected.rating }" /></span>
        <b class="t-body-14-sb">{{ t('reviewAdmin.detail.point', { n: selected.rating }) }}</b>
        <span class="spacer" />
        <span class="t-caption-12 muted">{{ fmtDate(selected.createdAt, { weekday: false, year: true }) }}</span>
      </p>
      <p class="tags">
        <AppBadge v-if="selected.procedureName" tag>{{ selected.procedureName }}</AppBadge>
        <AppBadge tag>{{ meta(selected) }}</AppBadge>
      </p>
      <p class="t-body-15">{{ selected.content }}</p>
      <p v-if="selected.translatedContent" class="t-body-14 secondary translated"><AppIcon name="languages" :size="14" />{{ selected.translatedContent }}</p>
      <p class="t-caption-12 muted">{{ t('reviewAdmin.detail.privacy') }}</p>
      <p v-if="selected.hidden" class="notice notice--muted t-caption-13">
        <AppIcon name="eye-off" :size="16" />{{ t('reviewAdmin.detail.hiddenNotice', { reason: t(`reviewAdmin.hide.reasons.${selected.hidden.reason}`) }) }}{{ selected.hidden.detail ? ` — ${selected.hidden.detail}` : '' }}
      </p>
      <hr />
      <label class="group">
        <span class="t-caption-13">{{ t('reviewAdmin.detail.reply') }}</span>
        <textarea v-model="draft" class="t-body-14" rows="5" maxlength="500" :placeholder="t('reviewAdmin.detail.replyPlaceholder')" />
        <span class="t-caption-12 muted">{{ t('reviewAdmin.detail.replyCount', { n: draft.length }) }}</span>
      </label>
      <p v-if="selected.reply" class="t-caption-12 muted">
        {{ replyLangs(selected) ? t('reviewAdmin.detail.translatedTo', { langs: replyLangs(selected) }) : t('reviewAdmin.detail.translating') }}
        · <button type="button" class="link" :disabled="!!busy" @click="deleteOpen = true">{{ t('reviewAdmin.detail.deleteReply') }}</button>
      </p>
      <p class="notice t-caption-13"><AppIcon name="info" :size="16" />{{ t('reviewAdmin.detail.replyNotice') }}</p>
      <span class="fill" />
      <div class="actions">
        <AppButton v-if="selected.hidden" variant="outline" size="l" block icon="eye" :loading="busy === 'hide'" :disabled="!!busy" @click="unhide">{{ t('reviewAdmin.detail.unhide') }}</AppButton>
        <AppButton v-else variant="outline" size="l" block icon="eye-off" :disabled="!!busy" @click="hideOpen = true">{{ t('reviewAdmin.detail.hide') }}</AppButton>
        <AppButton size="l" block icon="send" :disabled="!canReply" :loading="busy === 'reply'" @click="submitReply">
          {{ selected.reply ? t('reviewAdmin.detail.update') : t('reviewAdmin.detail.submit') }}
        </AppButton>
      </div>
    </aside>

    <ReviewHideModal :open="hideOpen" :review="selected" :busy="busy === 'hide'" @close="hideOpen = false" @submit="hide" />
    <AppDialog :open="deleteOpen" :title="t('reviewAdmin.detail.deleteReply')" :body="t('reviewAdmin.confirmDeleteReply')" @close="busy || (deleteOpen = false)">
      <template #actions>
        <AppButton variant="secondary" :disabled="!!busy" @click="deleteOpen = false">{{ t('common.cancel') }}</AppButton>
        <AppButton variant="danger" :loading="busy === 'delete'" @click="deleteReply">{{ t('reviewAdmin.detail.deleteReply') }}</AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100%; }
.main { display: flex; flex: 1; flex-direction: column; gap: var(--space-20); min-width: 0; padding: var(--space-32); }
.title { display: flex; flex-direction: column; gap: var(--space-4); }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.spacer { flex: 1; }
.stars { display: inline-flex; gap: 1px; color: var(--border-strong); }
.stars .on { color: var(--rating-star); fill: var(--rating-star); }
.summary { display: grid; grid-template-columns: 140px 1fr 220px; align-items: center; gap: var(--space-24); padding: var(--space-20) var(--space-24); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.avg { display: flex; flex-direction: column; gap: var(--space-4); }
.bars { display: flex; flex-direction: column; gap: var(--space-6); padding: 0 var(--space-24); border-left: 1px solid var(--border-default); border-right: 1px solid var(--border-default); }
.bar { display: grid; grid-template-columns: 32px 1fr 48px; align-items: center; gap: var(--space-12); }
.bar .num { text-align: right; }
.track { height: 8px; overflow: hidden; border-radius: 4px; background: var(--bg-muted); }
.track .fill { display: block; height: 100%; border-radius: 4px; background: var(--brand-primary); }
.track .fill.low { background: var(--rating-star); }
.kv { display: flex; flex-direction: column; gap: var(--space-12); margin: 0; }
.kv div { display: flex; justify-content: space-between; font: 500 14px/20px var(--font-sans); }
.kv dt { color: var(--text-secondary); }
.kv dd { margin: 0; font-weight: 700; }
.kv dd.warn { color: var(--status-warning); }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-8); }
.select { display: flex; align-items: center; gap: var(--space-6); height: 36px; padding: 0 var(--space-12); border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--bg-default); color: var(--icon-subtle); }
.select select { border: 0; outline: none; background: none; color: var(--text-primary); cursor: pointer; }
.list { display: flex; flex-direction: column; gap: var(--space-12); }
.card { display: flex; flex-direction: column; gap: var(--space-8); width: 100%; padding: var(--space-16) var(--space-20); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); text-align: left; cursor: pointer; }
.card:hover { border-color: var(--border-strong); }
.card--on { border-color: var(--brand-primary); background: var(--brand-subtle); }
.card--hidden .text { color: var(--text-tertiary); }
.card__head, .card__foot { display: flex; align-items: center; gap: var(--space-8); }
.translated { display: flex; gap: var(--space-6); }
.translated :deep(svg) { flex: none; margin-top: 3px; }
.action { display: flex; align-items: center; gap: var(--space-6); color: var(--text-secondary); }
.panel { position: sticky; top: 0; display: flex; flex: none; flex-direction: column; gap: var(--space-12); width: 400px; height: calc(100dvh - var(--staff-top-h)); padding: var(--space-24); border-left: 1px solid var(--border-default); background: var(--bg-default); overflow-y: auto; }
.panel__head { display: flex; align-items: center; justify-content: space-between; }
.x { border: 0; background: none; color: var(--icon-subtle); }
.rating { display: flex; align-items: center; gap: var(--space-8); }
.tags { display: flex; flex-wrap: wrap; gap: var(--space-6); }
hr { width: 100%; height: 1px; margin: var(--space-4) 0; border: 0; background: var(--border-default); }
.group { display: flex; flex-direction: column; gap: var(--space-8); }
textarea { padding: var(--space-12); border: 1px solid var(--border-default); border-radius: var(--radius-md); resize: vertical; }
textarea:focus { border-color: var(--brand-primary); outline: none; }
.link { padding: 0; border: 0; background: none; color: var(--status-danger); font: inherit; text-decoration: underline; cursor: pointer; }
.notice { display: flex; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); background: var(--bg-subtle); color: var(--text-secondary); }
.notice--muted { background: var(--bg-muted); }
.fill { flex: 1; }
.actions { display: flex; gap: var(--space-8); }
</style>
