<script setup lang="ts">
// H4-D 상담사 관리 (Figma 209:2238) + H4-1-D 추가 모달: 표(상태 필터·검색) + 오른쪽 상세 패널(400)
// 초대 메일 없이 바로 생성, 상태는 활성/비활성 두 가지. 진행 상담이 있으면 비활성 불가(409 INVALID_STATE_TRANSITION)
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { hospitalAdminApi, toApiError } from '@/api'
import { showToast } from '@/composables/useToast'
import { fmtDate, fmtDateTime } from '@/utils/format'
import KpiCard from '@/components/staff/KpiCard.vue'
import CounselorCreateModal from '@/components/staff/CounselorCreateModal.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import TextField from '@/components/ui/TextField.vue'
import type { CreateCounselorRequest, Counselor, Locale } from '@/types/contract'

const { t } = useI18n()
const LANGS: Locale[] = ['ko', 'en', 'zh', 'ja']
type Filter = 'all' | 'active' | 'inactive'
const FILTERS: Filter[] = ['all', 'active', 'inactive']

const all = ref<Counselor[]>([])
const waiting = ref(0)
const failed = ref(false)
const loading = ref(true)
const filter = ref<Filter>('all')
const q = ref('')
const selectedId = ref<number | null>(null)
const busy = ref<'save' | 'toggle' | 'create' | null>(null)
const createOpen = ref(false)
const emailTaken = ref(false)
const confirmOpen = ref(false)

const counts = computed(() => ({
  all: all.value.length,
  active: all.value.filter((c) => c.active).length,
  inactive: all.value.filter((c) => !c.active).length,
}))
const rows = computed(() => {
  const text = q.value.trim().toLowerCase()
  return all.value
    .filter((c) => filter.value === 'all' || (filter.value === 'active') === c.active)
    .filter((c) => !text || c.name.toLowerCase().includes(text) || c.email.toLowerCase().includes(text))
})
const ongoing = computed(() => all.value.reduce((n, c) => n + c.activeConsultations, 0))
const closed = computed(() => all.value.reduce((n, c) => n + c.closedThisMonth, 0))
const selected = computed(() => all.value.find((c) => c.id === selectedId.value) ?? null)

// 상세 패널 편집 값 (선택이 바뀌면 다시 채움)
const draft = ref<{ name: string; languages: Locale[]; acceptingNew: boolean }>({ name: '', languages: [], acceptingNew: true })
watch(
  selected,
  (c) => {
    if (c) draft.value = { name: c.name, languages: [...c.languages], acceptingNew: c.acceptingNew }
  },
  { immediate: true },
)
const sameLangs = (a: Locale[], b: Locale[]) => a.length === b.length && a.every((l) => b.includes(l))
const dirty = computed(
  () =>
    !!selected.value &&
    (draft.value.name.trim() !== selected.value.name || !sameLangs(draft.value.languages, selected.value.languages) || draft.value.acceptingNew !== selected.value.acceptingNew),
)
const canSave = computed(() => dirty.value && !!draft.value.name.trim() && draft.value.languages.length > 0)

const lastLogin = (c: Counselor) => (c.lastLoginAt ? fmtDateTime(c.lastLoginAt) : t('counselorAdmin.never'))
function toggleLang(l: Locale) {
  const ls = draft.value.languages
  draft.value.languages = ls.includes(l) ? ls.filter((x) => x !== l) : LANGS.filter((x) => x === l || ls.includes(x))
}

async function load() {
  failed.value = false
  try {
    const res = await hospitalAdminApi.counselors()
    all.value = res.items
    waiting.value = res.waitingConsultations
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
function replace(c: Counselor) {
  const i = all.value.findIndex((x) => x.id === c.id)
  if (i >= 0) all.value[i] = c
  else all.value.push(c)
}
async function create(body: CreateCounselorRequest) {
  busy.value = 'create'
  emailTaken.value = false
  try {
    const c = await hospitalAdminApi.createCounselor(body)
    replace(c)
    createOpen.value = false
    filter.value = 'all'
    selectedId.value = c.id
    showToast(t('counselorAdmin.toast.created'))
  } catch (e) {
    if (toApiError(e)?.code === 'EMAIL_DUPLICATED') emailTaken.value = true
    else showToast(t('common.error'), 'error')
  } finally {
    busy.value = null
  }
}
async function save() {
  if (!selected.value || !canSave.value) return
  busy.value = 'save'
  try {
    replace(
      await hospitalAdminApi.updateCounselor(selected.value.id, {
        name: draft.value.name.trim(),
        languages: draft.value.languages,
        acceptingNew: draft.value.acceptingNew,
      }),
    )
    showToast(t('counselorAdmin.toast.saved'))
  } catch {
    showToast(t('common.error'), 'error')
  } finally {
    busy.value = null
  }
}
async function setActive(active: boolean) {
  if (!selected.value) return
  busy.value = 'toggle'
  try {
    const id = selected.value.id
    replace(active ? await hospitalAdminApi.activateCounselor(id) : await hospitalAdminApi.deactivateCounselor(id))
    confirmOpen.value = false
    showToast(t(active ? 'counselorAdmin.toast.activated' : 'counselorAdmin.toast.deactivated'))
  } catch (e) {
    confirmOpen.value = false
    showToast(toApiError(e)?.code === 'INVALID_STATE_TRANSITION' ? t('counselorAdmin.toast.ongoing') : t('common.error'), 'error')
    await load()
  } finally {
    busy.value = null
  }
}
function openCreate() {
  emailTaken.value = false
  createOpen.value = true
}

onMounted(load)
watch(filter, () => {
  if (selected.value && !rows.value.includes(selected.value)) selectedId.value = null
})
</script>

<template>
  <div class="layout">
    <div class="main">
      <header class="title">
        <div>
          <h1 class="t-title-22">{{ t('counselorAdmin.nav') }}</h1>
          <p class="t-body-14 secondary">{{ t('counselorAdmin.sub') }}</p>
        </div>
        <AppButton icon="plus" size="l" @click="openCreate">{{ t('counselorAdmin.add') }}</AppButton>
      </header>
      <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('staff.loadFailed')">
        <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
      </EmptyState>
      <template v-else>
        <div class="kpis">
          <KpiCard :label="t('counselorAdmin.kpi.active')" :value="counts.active" :sub="t('counselorAdmin.kpi.activeSub', { n: counts.inactive })" />
          <KpiCard :label="t('counselorAdmin.kpi.ongoing')" :value="ongoing" :sub="t('counselorAdmin.kpi.ongoingSub', { n: waiting })" :warn="waiting > 0 && counts.active === 0" />
          <KpiCard :label="t('counselorAdmin.kpi.closed')" :value="closed" :sub="t('counselorAdmin.kpi.closedSub')" />
        </div>
        <div class="toolbar">
          <AppChip v-for="f in FILTERS" :key="f" :selected="filter === f" @click="filter = f">{{ t(`counselorAdmin.filters.${f}`) }} {{ counts[f] }}</AppChip>
          <span class="spacer" />
          <label class="search">
            <AppIcon name="search" :size="16" />
            <input v-model="q" class="t-caption-13" :placeholder="t('counselorAdmin.search')" :aria-label="t('counselorAdmin.search')" />
          </label>
        </div>
        <div v-if="rows.length" class="table">
          <!-- 행이 버튼이라 머리글은 시각용 (ReservationTable 과 같은 방식) -->
          <div class="tr th t-caption-12-sb" aria-hidden="true">
            <span>{{ t('counselorAdmin.table.counselor') }}</span>
            <span>{{ t('counselorAdmin.table.languages') }}</span>
            <span>{{ t('counselorAdmin.table.ongoing') }}</span>
            <span>{{ t('counselorAdmin.table.lastLogin') }}</span>
            <span>{{ t('counselorAdmin.table.status') }}</span>
          </div>
          <button
            v-for="c in rows"
            :key="c.id"
            type="button"
            class="tr td"
            :class="{ 'td--on': c.id === selectedId, 'td--off': !c.active }"
            @click="selectedId = c.id"
          >
            <span class="who">
              <span class="avatar t-caption-12-sb">{{ c.name.slice(0, 1) }}</span>
              <span>
                <span class="t-body-14-sb">{{ c.name }}</span>
                <span class="t-caption-12 muted">{{ c.email }}</span>
              </span>
            </span>
            <span class="langs"><AppBadge v-for="l in c.languages" :key="l" tag>{{ l.toUpperCase() }}</AppBadge></span>
            <span class="t-body-14">{{ c.active ? t('counselorAdmin.count', { n: c.activeConsultations }) : '—' }}</span>
            <span class="t-body-14">{{ lastLogin(c) }}</span>
            <span class="badges">
              <AppBadge :tone="c.active ? 'success' : 'neutral'" dot>{{ t(c.active ? 'counselorAdmin.status.active' : 'counselorAdmin.status.inactive') }}</AppBadge>
              <AppBadge v-if="c.active && !c.acceptingNew" tone="warning">{{ t('counselorAdmin.status.paused') }}</AppBadge>
            </span>
          </button>
          <p class="foot t-caption-12">{{ t('counselorAdmin.foot', { n: rows.length }) }}</p>
        </div>
        <EmptyState v-else-if="!loading" icon="headphones" :title="t(all.length ? 'counselorAdmin.emptyFiltered' : 'counselorAdmin.empty')" />
      </template>
    </div>

    <!-- 상세 패널 -->
    <aside v-if="selected" class="panel">
      <header class="panel__head">
        <h2 class="t-body-16-sb">{{ t('counselorAdmin.detail.title') }}</h2>
        <button type="button" class="x" :aria-label="t('common.close')" @click="selectedId = null"><AppIcon name="x" :size="20" /></button>
      </header>
      <div class="who">
        <span class="avatar avatar--l t-body-16-sb">{{ selected.name.slice(0, 1) }}</span>
        <div>
          <p class="t-title-18">{{ selected.name }}</p>
          <p class="t-caption-12 muted">{{ selected.email }}</p>
        </div>
      </div>
      <div class="badges">
        <AppBadge :tone="selected.active ? 'success' : 'neutral'" dot>{{ t(selected.active ? 'counselorAdmin.status.active' : 'counselorAdmin.status.inactive') }}</AppBadge>
        <AppBadge v-if="selected.active && !selected.acceptingNew" tone="warning">{{ t('counselorAdmin.status.paused') }}</AppBadge>
      </div>
      <hr />
      <TextField v-model="draft.name" :label="t('counselorAdmin.detail.name')" required :invalid="!draft.name.trim()" />
      <div class="readonly">
        <p class="t-caption-13">{{ t('counselorAdmin.detail.email') }}</p>
        <p class="box t-body-15">{{ selected.email }}</p>
        <p class="t-caption-12 muted">{{ t('counselorAdmin.detail.emailHint') }}</p>
      </div>
      <div class="group">
        <p class="t-caption-13">{{ t('counselorAdmin.detail.languages') }}</p>
        <div class="chips" role="group" :aria-label="t('counselorAdmin.detail.languages')">
          <AppChip v-for="l in LANGS" :key="l" :selected="draft.languages.includes(l)" :aria-pressed="draft.languages.includes(l)" @click="toggleLang(l)">
            {{ t(`domain.langName.${l}`) }}
          </AppChip>
        </div>
        <p v-if="!draft.languages.length" class="t-caption-12 danger">{{ t('counselorAdmin.detail.languagesHint') }}</p>
      </div>
      <label class="switch">
        <span>
          <span class="t-body-14-sb">{{ t('counselorAdmin.detail.acceptingNew') }}</span>
          <span class="t-caption-12 muted">{{ t('counselorAdmin.detail.acceptingNewHint') }}</span>
        </span>
        <input v-model="draft.acceptingNew" type="checkbox" role="switch" />
        <span class="track" aria-hidden="true" />
      </label>
      <hr />
      <dl class="kv">
        <div><dt>{{ t('counselorAdmin.detail.joined') }}</dt><dd>{{ fmtDate(selected.createdAt, { year: true }) }}</dd></div>
        <div><dt>{{ t('counselorAdmin.detail.ongoing') }}</dt><dd>{{ t('counselorAdmin.count', { n: selected.activeConsultations }) }}</dd></div>
        <div><dt>{{ t('counselorAdmin.detail.closedThisMonth') }}</dt><dd>{{ t('counselorAdmin.count', { n: selected.closedThisMonth }) }}</dd></div>
        <div><dt>{{ t('counselorAdmin.table.lastLogin') }}</dt><dd>{{ lastLogin(selected) }}</dd></div>
      </dl>
      <span class="fill" />
      <p v-if="!selected.active" class="notice t-caption-13"><AppIcon name="info" :size="16" />{{ t('counselorAdmin.detail.inactiveNotice') }}</p>
      <p v-else class="notice notice--warn t-caption-13">
        <AppIcon name="alert-triangle" :size="16" />
        {{ selected.activeConsultations ? t('counselorAdmin.detail.deactivateBlocked', { n: selected.activeConsultations }) : t('counselorAdmin.detail.deactivateNotice') }}
      </p>
      <div class="actions">
        <AppButton v-if="selected.active" variant="outline" size="l" block :disabled="!!busy || selected.activeConsultations > 0" @click="confirmOpen = true">
          {{ t('counselorAdmin.detail.deactivate') }}
        </AppButton>
        <AppButton v-else variant="outline" size="l" block :loading="busy === 'toggle'" :disabled="!!busy" @click="setActive(true)">
          {{ t('counselorAdmin.detail.activate') }}
        </AppButton>
        <AppButton size="l" block :disabled="!canSave || !!busy" :loading="busy === 'save'" @click="save">{{ t('counselorAdmin.detail.save') }}</AppButton>
      </div>
    </aside>

    <CounselorCreateModal :open="createOpen" :busy="busy === 'create'" :email-taken="emailTaken" @close="createOpen = false" @submit="create" @email-edited="emailTaken = false" />
    <AppDialog :open="confirmOpen" :title="t('counselorAdmin.detail.deactivate')" :body="selected ? t('counselorAdmin.confirmDeactivate', { name: selected.name }) : ''" @close="busy || (confirmOpen = false)">
      <template #actions>
        <AppButton variant="secondary" :disabled="!!busy" @click="confirmOpen = false">{{ t('common.cancel') }}</AppButton>
        <AppButton variant="danger" :loading="busy === 'toggle'" @click="setActive(false)">{{ t('counselorAdmin.detail.deactivate') }}</AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100%; }
.main { display: flex; flex: 1; flex-direction: column; gap: var(--space-20); min-width: 0; padding: var(--space-32); }
.title { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-16); }
.title > div { display: flex; flex-direction: column; gap: var(--space-4); }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.danger { color: var(--status-danger); }
.kpis { display: flex; gap: var(--space-16); }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-8); }
.spacer { flex: 1; }
.search { display: flex; align-items: center; gap: var(--space-6); width: 220px; height: 36px; padding: 0 var(--space-12); border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--bg-default); color: var(--icon-subtle); }
.search input { flex: 1; min-width: 0; border: 0; outline: none; color: var(--text-primary); }
.table { overflow: hidden; border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.tr { display: grid; grid-template-columns: 1.6fr 1fr 80px 1fr 1.1fr; align-items: center; gap: var(--space-16); width: 100%; padding: var(--space-12) var(--space-20); border: 0; border-top: 1px solid var(--border-default); background: none; text-align: left; }
.th { border-top: 0; background: var(--bg-subtle); color: var(--text-secondary); }
.td { position: relative; cursor: pointer; }
.td:hover { background: var(--bg-subtle); }
.td--on { background: var(--brand-subtle); }
.td--on::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--brand-primary); }
.td--off .who { opacity: 0.6; }
.who { display: flex; align-items: center; gap: var(--space-12); min-width: 0; }
.who > span:last-child, .who > div { display: flex; flex-direction: column; min-width: 0; }
.avatar { display: grid; place-items: center; flex: none; width: 32px; height: 32px; border-radius: 50%; background: var(--bg-muted); color: var(--text-secondary); }
.avatar--l { width: 44px; height: 44px; }
.langs, .badges { display: flex; flex-wrap: wrap; gap: var(--space-4); }
.foot { padding: var(--space-12) var(--space-20); border-top: 1px solid var(--border-default); color: var(--text-tertiary); }
.panel { position: sticky; top: 0; display: flex; flex: none; flex-direction: column; gap: var(--space-16); width: 400px; height: calc(100dvh - var(--staff-top-h)); padding: var(--space-24); border-left: 1px solid var(--border-default); background: var(--bg-default); overflow-y: auto; }
.panel__head { display: flex; align-items: center; justify-content: space-between; }
.x { border: 0; background: none; color: var(--icon-subtle); }
hr { width: 100%; height: 1px; margin: 0; border: 0; background: var(--border-default); }
.readonly, .group { display: flex; flex-direction: column; gap: var(--space-8); }
.box { padding: var(--space-12) var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-md); background: var(--bg-subtle); color: var(--text-tertiary); }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.switch { position: relative; display: flex; align-items: center; justify-content: space-between; gap: var(--space-12); cursor: pointer; }
.switch > span:first-child { display: flex; flex-direction: column; gap: var(--space-2); }
.switch input { position: absolute; opacity: 0; }
.track { position: relative; flex: none; width: 36px; height: 20px; border-radius: 10px; background: var(--border-strong); transition: background 0.15s; }
.track::after { content: ''; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: var(--bg-default); transition: transform 0.15s; }
.switch input:checked + .track { background: var(--brand-primary); }
.switch input:checked + .track::after { transform: translateX(16px); }
.switch input:focus-visible + .track { outline: 2px solid var(--border-focus); outline-offset: 2px; }
.kv { display: flex; flex-direction: column; gap: var(--space-12); margin: 0; }
.kv div { display: grid; grid-template-columns: 96px 1fr; font: 600 14px/20px var(--font-sans); }
.kv dt { font-weight: 500; color: var(--text-tertiary); }
.kv dd { margin: 0; }
.fill { flex: 1; }
.notice { display: flex; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); background: var(--status-info-bg); color: var(--status-info); }
.notice--warn { background: var(--status-warning-bg); color: var(--status-warning); }
.actions { display: flex; gap: var(--space-8); }
</style>
