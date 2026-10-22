<script setup lang="ts">
// 「화면 목록」 C4-0 대화 목록 (Figma 106:3603, /chats): 하단 탭 AI · 채팅 Top App Bar 아이콘으로 진입
// 맨 위 여신 AI(최근 메인 대화) 1줄 + 「병원 대화 N」 병원별 최근 대화. 배지는 대화 모드 + 그 병원 최근 예약 상태
// 데이터: GET /api/ai/conversations · GET /api/reservations/me · (상담 연결 대화만) GET /api/consultations/{id}
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { aiApi, consultationApi, reservationApi } from '@/api'
import { useSearchStore } from '@/stores/search'
import { seoulDate } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import AppBadge, { RESERVATION_TONE } from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import AftercareChatRows from '@/components/aftercare/AftercareChatRows.vue'
import type { ConsultationStatus, Conversation, Reservation } from '@/types/contract'

const { t } = useI18n()
const search = useSearchStore()
const conversations = ref<Conversation[] | null>(null)
const reservations = ref<Reservation[]>([])
const consultStatus = ref<Record<number, ConsultationStatus>>({})
const failed = ref(false)
const aftercareIds = ref(new Set<string>())
/** 대화별 마지막 활동 시각 = 그 대화의 가장 최근 AI 작업 시각 (GET /api/ai/tasks, 계약 변경 없음) */
const lastActive = ref<Record<string, string>>({})
// ponytail: /api/ai/tasks 는 최근 50건만 → 그보다 오래 쉰 대화는 생성 시각으로. 정확히 하려면 Conversation 에 마지막 활동 시각 필드 필요
const activeAt = (c: Conversation) => lastActive.value[c.id] ?? c.createdAt

const main = computed(() => conversations.value?.find((c) => c.mode === 'MAIN') ?? null)
/** 병원마다 최근 대화 1개 (목록은 최근 순) */
const hospitalChats = computed(() => {
  const seen = new Set<number>()
  return (conversations.value ?? []).filter((c) => c.hospital && c.mode !== 'AFTERCARE' && !aftercareIds.value.has(c.id)
    && !seen.has(c.hospital.id) && seen.add(c.hospital.id))
})

const md = (iso: string) => seoulDate(iso).slice(5).replace('-', '/')
const procName = (c: Conversation) => search.procedures.find((p) => p.code === c.conditions?.procedureCode)?.name
function mainSummary(c: Conversation) {
  const k = c.conditions
  const areas = (k?.areas ?? []).map((a) => t(`domain.area.${a}`)).join('·')
  const dates = k?.dateFrom ? `${md(k.dateFrom)}–${k.dateTo ? md(k.dateTo) : ''}` : ''
  return [procName(c), areas, dates].filter(Boolean).join(' · ') || t('chat.list.noConditions')
}
function modeBadge(c: Conversation) {
  if (c.mode !== 'HUMAN') return { tone: 'agent' as const, icon: 'hospital' as const, label: t('chat.mode.agent') }
  if (c.consultationId && consultStatus.value[c.consultationId] === 'WAITING') return { tone: 'warning' as const, icon: 'clock' as const, label: t('chat.mode.waiting') }
  return { tone: 'info' as const, icon: 'headphones' as const, label: t('chat.mode.human') }
}
/** 그 병원의 가장 최근 예약 */
const lastReservation = (hospitalId: number) =>
  reservations.value.filter((r) => r.hospital.id === hospitalId).sort((a, b) => b.createdAt.localeCompare(a.createdAt))[0] ?? null

async function load() {
  failed.value = false
  try {
    const [list, mine, tasks] = await Promise.all([
      aiApi.conversations(),
      reservationApi.mine().catch(() => []),
      aiApi.myTasks().catch(() => []),
    ])
    const last: Record<string, string> = {}
    for (const task of tasks) {
      const prev = last[task.conversationId]
      if (!prev || Date.parse(task.createdAt) > Date.parse(prev)) last[task.conversationId] = task.createdAt
    }
    lastActive.value = last
    // 최근에 대화한 순 (메인 대화·병원별 대화 모두 마지막 활동 기준으로 고른다)
    conversations.value = [...list].sort((a, b) => Date.parse(activeAt(b)) - Date.parse(activeAt(a)))
    reservations.value = mine
    const ids = list.filter((c) => c.mode === 'HUMAN' && c.consultationId).map((c) => c.consultationId!)
    const got = await Promise.all(ids.map((id) => consultationApi.get(id).catch(() => null)))
    consultStatus.value = Object.fromEntries(got.filter((x) => x).map((x) => [x!.id, x!.status]))
  } catch {
    failed.value = true
  }
}
onMounted(() => {
  void search.loadProcedures().catch(() => undefined)
  void load()
})
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('chat.list.title')" :back="true" />

    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('common.error')">
      <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
    </EmptyState>

    <div v-else class="content">
      <!-- 불러오는 중 (빈 화면 대신) -->
      <div v-if="!conversations" class="skeleton-list" role="status" :aria-label="t('common.loading')" aria-busy="true">
        <span v-for="i in 4" :key="i" class="bone" style="height: 64px" />
      </div>
      <template v-if="conversations">
        <!-- 여신 AI (맨 위 고정): 최근 메인 대화. 없으면 /chat 이 새로 연다 -->
        <RouterLink :to="main ? `/chat/${main.id}` : '/chat'" class="row">
          <span class="avatar avatar--brand"><AppIcon name="sparkles" :size="22" /></span>
          <span class="text">
            <span class="line1">
              <span class="name t-body-16-sb">{{ t('chat.aiTitle') }}</span>
              <span v-if="main" class="date t-caption-12">{{ md(activeAt(main)) }}</span>
            </span>
            <span class="sub t-body-14">{{ main ? mainSummary(main) : t('chat.helloAi') }}</span>
            <span class="badges"><AppBadge tone="brand" icon="sparkles">{{ t('chat.mode.ai') }}</AppBadge></span>
          </span>
        </RouterLink>

        <template v-if="hospitalChats.length">
          <hr class="divider" />
          <h2 class="section t-caption-13">{{ t('chat.list.hospitals', { n: hospitalChats.length }) }}</h2>
          <template v-for="(c, i) in hospitalChats" :key="c.id">
            <hr v-if="i" class="divider" />
            <RouterLink :to="`/chat/${c.id}`" class="row">
              <span class="avatar"><AppIcon name="hospital" :size="22" /></span>
              <span class="text">
                <span class="line1">
                  <span class="name t-body-16-sb">{{ c.hospital!.name }}</span>
                  <span class="date t-caption-12">{{ md(activeAt(c)) }}</span>
                </span>
                <span class="sub t-body-14">{{ procName(c) ?? t('chat.list.noConditions') }}</span>
                <span class="badges">
                  <AppBadge :tone="modeBadge(c).tone" :icon="modeBadge(c).icon">{{ modeBadge(c).label }}</AppBadge>
                  <AppBadge v-if="lastReservation(c.hospital!.id)" :tone="RESERVATION_TONE[lastReservation(c.hospital!.id)!.status]" dot>
                    {{ t(`domain.status.${lastReservation(c.hospital!.id)!.status}`) }}
                  </AppBadge>
                </span>
              </span>
            </RouterLink>
          </template>
        </template>
        <AftercareChatRows @loaded="(ids) => (aftercareIds = new Set(ids))" />
      </template>
    </div>
  </div>
</template>

<style scoped>
/* Figma 106:3603 · Chat Room Row(106:156) */
.page { display: flex; flex-direction: column; min-height: 100%; }
.content { flex: 1; padding-bottom: var(--space-8); border-top: 1px solid var(--border-default); }
.row { display: flex; align-items: center; gap: var(--space-12); padding: var(--space-12) var(--space-16); color: var(--text-primary); text-decoration: none; }
.avatar { display: grid; flex: none; place-items: center; width: 44px; height: 44px; border-radius: 22px; background: var(--status-neutral-bg); color: var(--chat-agent-accent); }
.avatar--brand { background: var(--brand-subtle); color: var(--brand-primary); }
.text { display: flex; flex: 1; flex-direction: column; gap: var(--space-4); min-width: 0; }
.line1 { display: flex; align-items: center; gap: var(--space-8); }
.name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.date { flex: none; color: var(--text-tertiary); }
.sub { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-tertiary); }
.badges { display: flex; gap: var(--space-6); }
.divider { height: 1px; margin: 0 var(--space-16); border: 0; background: var(--border-default); }
.section { padding: var(--space-16) var(--space-16) var(--space-4); color: var(--text-secondary); }
</style>
