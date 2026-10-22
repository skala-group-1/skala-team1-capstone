<script setup lang="ts">
// 「화면 목록」 O1-D 운영 (04 ④ 2:11966): 실패한 AI 작업(GET /api/ops/ai-tasks) + 감사 로그(GET /api/ops/audit-logs). 읽기 전용
// /ops → 두 표, /ops/audit-logs → 감사 로그만. 추적은 traceId(=taskId) 복사 → LangSmith 에서 검색
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { opsApi } from '@/api'
import { showToast } from '@/composables/useToast'
import AppChip from '@/components/ui/AppChip.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import AftercareOpsCard from '@/components/aftercare/AftercareOpsCard.vue'
import type { AuditLog, OpsAiTask, Page } from '@/types/contract'

const route = useRoute()
const { t } = useI18n()
const SIZE = 20
const auditOnly = computed(() => route.path.endsWith('/audit-logs'))

const taskStatus = ref<'FAILED' | 'QUEUED' | 'DONE' | 'ALL'>('FAILED')
const tasks = ref<Page<OpsAiTask> | null>(null)
const logs = ref<Page<AuditLog> | null>(null)
const taskPage = ref(0)
const logPage = ref(0)
const failed = ref(false)

const ts = (iso: string) =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })
    .format(new Date(iso))
    .replace(',', '')
const short = (id: string) => `${id.slice(0, 4)}…${id.slice(-4)}`
const range = (p: Page<unknown> | null) => (p && p.total ? `${p.page * p.size + 1}–${Math.min((p.page + 1) * p.size, p.total)} / ${p.total}` : '0')

async function loadTasks() {
  tasks.value = await opsApi.aiTasks({ status: taskStatus.value === 'ALL' ? undefined : taskStatus.value, page: taskPage.value, size: SIZE })
}
async function loadLogs() {
  logs.value = await opsApi.auditLogs({ page: logPage.value, size: SIZE })
}
async function load() {
  failed.value = false
  try {
    await Promise.all([auditOnly.value ? Promise.resolve() : loadTasks(), loadLogs()])
  } catch {
    failed.value = true
  }
}
async function copyTrace(id: string) {
  await navigator.clipboard?.writeText(id).catch(() => undefined)
  showToast(t('staff.ops.copied'))
}
onMounted(load)
watch([taskStatus, taskPage], () => void loadTasks().catch(() => (failed.value = true)))
watch(logPage, () => void loadLogs().catch(() => (failed.value = true)))
watch(auditOnly, () => void load())
</script>

<template>
  <div class="page">
    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('staff.loadFailed')" />
    <template v-else>
      <AftercareOpsCard v-if="!auditOnly" />
      <section v-if="!auditOnly" class="section">
        <header>
          <h1 class="t-title-22">{{ t('staff.ops.failedTitle') }}</h1>
          <p class="t-body-14 secondary">{{ t('staff.ops.failedSub') }}</p>
        </header>
        <div class="chips">
          <AppChip v-for="s in ['ALL', 'FAILED', 'QUEUED', 'DONE'] as const" :key="s" :selected="taskStatus === s" @click="(taskStatus = s), (taskPage = 0)">
            {{ t(`staff.ops.status.${s}`) }}<template v-if="s === taskStatus && tasks"> {{ tasks.total }}</template>
          </AppChip>
        </div>
        <div class="table">
          <div class="tr tr--tasks th t-caption-12-sb">
            <span>{{ t('staff.ops.cols.createdAt') }}</span><span>{{ t('staff.ops.cols.taskId') }}</span><span>{{ t('staff.ops.cols.user') }}</span>
            <span>{{ t('staff.ops.cols.input') }}</span><span>{{ t('staff.ops.cols.error') }}</span><span>{{ t('staff.ops.cols.status') }}</span><span>{{ t('staff.ops.cols.trace') }}</span>
          </div>
          <div v-for="x in tasks?.items ?? []" :key="x.id" class="tr tr--tasks t-body-14">
            <span>{{ ts(x.createdAt) }}</span>
            <span class="mono">{{ short(x.id) }}</span>
            <span>#{{ x.userId }}</span>
            <span class="ellipsis">{{ x.message ?? '—' }}</span>
            <span class="ellipsis">{{ x.error?.message ?? '—' }}</span>
            <span><AppBadge :tone="x.status === 'FAILED' ? 'danger' : x.status === 'DONE' ? 'success' : 'neutral'">{{ x.status }}</AppBadge></span>
            <button type="button" class="link t-caption-13" @click="copyTrace(x.id)">{{ t('staff.ops.copyTrace') }} <AppIcon name="chevron-right" :size="14" /></button>
          </div>
          <p v-if="!tasks?.items.length" class="no-rows t-body-14">{{ t('staff.ops.noTasks') }}</p>
          <footer class="foot t-caption-12">
            <span>{{ range(tasks) }} · GET /api/ops/ai-tasks</span>
            <span class="pager">
              <button type="button" :disabled="!taskPage" :aria-label="t('booking.prevMonth')" @click="taskPage--"><AppIcon name="chevron-left" :size="16" /></button>
              <button type="button" :disabled="!tasks || (taskPage + 1) * SIZE >= tasks.total" :aria-label="t('booking.nextMonth')" @click="taskPage++"><AppIcon name="chevron-right" :size="16" /></button>
            </span>
          </footer>
        </div>
      </section>

      <section class="section">
        <h2 :class="auditOnly ? 't-title-22' : 't-title-18'">{{ t('staff.nav.auditLogs') }}</h2>
        <div class="table">
          <div class="tr tr--logs th t-caption-12-sb">
            <span>{{ t('staff.ops.cols.time') }}</span><span>traceId</span><span>{{ t('staff.ops.cols.role') }}</span><span>action</span><span>target</span>
          </div>
          <div v-for="l in logs?.items ?? []" :key="l.id" class="tr tr--logs t-body-14">
            <span>{{ ts(l.createdAt) }}</span>
            <span class="mono">{{ l.traceId?.slice(0, 10) ?? '—' }}</span>
            <span>{{ l.actorRole ?? '—' }}</span>
            <span>{{ l.action }}</span>
            <span class="ellipsis">{{ l.target }}</span>
          </div>
          <p v-if="!logs?.items.length" class="no-rows t-body-14">{{ t('staff.ops.noLogs') }}</p>
          <footer class="foot t-caption-12">
            <span>{{ range(logs) }} · {{ t('staff.ops.latest') }} · GET /api/ops/audit-logs</span>
            <span class="pager">
              <button type="button" :disabled="!logPage" :aria-label="t('booking.prevMonth')" @click="logPage--"><AppIcon name="chevron-left" :size="16" /></button>
              <button type="button" :disabled="!logs || (logPage + 1) * SIZE >= logs.total" :aria-label="t('booking.nextMonth')" @click="logPage++"><AppIcon name="chevron-right" :size="16" /></button>
            </span>
          </footer>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: var(--space-32); padding: var(--space-32); }
.section { display: flex; flex-direction: column; gap: var(--space-16); }
.secondary { color: var(--text-secondary); }
.chips { display: flex; gap: var(--space-8); }
.table { overflow: hidden; border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.tr { display: grid; align-items: center; gap: var(--space-16); padding: var(--space-16) var(--space-20); border-top: 1px solid var(--border-default); }
.tr--tasks { grid-template-columns: 150px 110px 60px 1.4fr 1.4fr 90px 100px; }
.tr--logs { grid-template-columns: 150px 130px 150px 1fr 1.4fr; }
.th { border-top: 0; background: var(--bg-subtle); color: var(--text-secondary); }
.ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mono { font-variant-numeric: tabular-nums; }
.link { display: inline-flex; align-items: center; padding: 0; border: 0; background: none; color: var(--text-brand); font-weight: 600; }
.no-rows { padding: var(--space-24); color: var(--text-tertiary); text-align: center; }
.foot { display: flex; justify-content: space-between; padding: var(--space-12) var(--space-20); border-top: 1px solid var(--border-default); color: var(--text-tertiary); }
.pager { display: flex; gap: var(--space-8); }
.pager button { border: 0; background: none; color: var(--icon-default); }
.pager button:disabled { color: var(--icon-subtle); }
</style>
