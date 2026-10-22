<script setup lang="ts">
// 「화면 목록」 C4 AI 채팅 — 메인 AI(MAIN) · 병원 대화(HOSPITAL) · 상담원 연결(HUMAN) 공용 (Figma 02 C4 섹션 + Edge ①②③ + 04 ④ 일정/기억)
// SSE 는 conversation 스토어 reducer, HUMAN 모드 메시지는 consultation 스토어(STOMP)
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { aiApi, toApiError } from '@/api'
import { useConversationStore } from '@/stores/conversation'
import { useConsultationStore } from '@/stores/consultation'
import { useSearchStore } from '@/stores/search'
import { useReservationStore } from '@/stores/reservation'
import { useAuthStore } from '@/stores/auth'
import { useNow } from '@/composables/useNow'
import { showToast } from '@/composables/useToast'
import { fmtDate, fmtDateTime, fmtKrw, fmtKrwCompact, fmtTime, remaining } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge, { RESERVATION_TONE } from '@/components/ui/AppBadge.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppBanner from '@/components/ui/AppBanner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import HospitalCarousel from '@/components/chat/HospitalCarousel.vue'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import ApprovalCard from '@/components/chat/ApprovalCard.vue'
import ConsultSummaryCard from '@/components/chat/ConsultSummaryCard.vue'
import EvidenceSheet from '@/components/chat/EvidenceSheet.vue'
import TripPlanCard from '@/components/chat/TripPlanCard.vue'
import TopicCarousel from '@/components/chat/TopicCarousel.vue'
import ProcedureInfoCard from '@/components/chat/ProcedureInfoCard.vue'
import AftercareHeader from '@/components/aftercare/AftercareHeader.vue'
import AftercareClosed from '@/components/aftercare/AftercareClosed.vue'
import { isAftercareClosed } from '@/api/aftercare'
import { useAftercareRoom } from '@/composables/useAftercareRoom'
import { SKIN_CONCERNS } from '@/types/contract'
import type { ChatMessage, Conditions, ConsultTopic, ConversationMessage, Locale, ProcedureInfo, Reservation, SkinConcern, Source } from '@/types/contract'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const conv = useConversationStore()
const consult = useConsultationStore()
const search = useSearchStore()
const reservations = useReservationStore()
const auth = useAuthStore()
const now = useNow()

const input = ref('')
const inputEl = ref<HTMLTextAreaElement | null>(null)
const scroller = ref<HTMLElement | null>(null)
const evidence = ref<Source[] | null>(null)
const infoOpen = ref(false)
const consent = ref(false)
const approving = ref(false)
const requested = ref<Reservation | null>(null)
const shownOriginal = ref(new Set<number>())
const startingConversation = ref(false)
/** 대화를 불러오지 못함 (네트워크·서버 오류) → 재시도 화면 */
const loadFailed = ref(false)
/** 다른 대화를 불러오는 중 (이전 대화 화면·입력을 막는다) */
const loading = ref(false)

// ─── 모드 ───
const isHospital = computed(() => conv.mode !== 'MAIN')
const isHuman = computed(() => conv.mode === 'HUMAN')
const consultStatus = computed(() => consult.current?.status ?? 'WAITING')
const aftercare = useAftercareRoom(() => conv.conversationId)
const title = computed(() => (isHospital.value ? (conv.hospital?.name ?? '') : t('chat.aiTitle')))
const modeBadge = computed(() => {
  if (!isHospital.value) return { tone: 'brand' as const, icon: 'sparkles' as const, label: t('chat.mode.ai') }
  if (conv.mode === 'AFTERCARE') return { tone: 'success' as const, icon: 'file-text' as const, label: t('aftercare.badge') }
  if (!isHuman.value) return { tone: 'agent' as const, icon: 'hospital' as const, label: t('chat.mode.agent') }
  if (consultStatus.value === 'WAITING') return { tone: 'warning' as const, icon: 'clock' as const, label: t('chat.mode.waiting') }
  return { tone: 'info' as const, icon: 'headphones' as const, label: t('chat.mode.human') }
})
const assistantName = computed(() =>
  isHospital.value ? t('chat.agentName', { hospital: conv.hospital?.name ?? '' }) : t('chat.aiTitle'),
)

// ─── 이름 표시 ───
const procedureName = (code: string | null) => search.procedures.find((p) => p.code === code)?.name ?? code ?? ''
const conditionChips = computed(() => {
  const c = conv.conditions
  if (!c) return []
  const chips: { key: keyof Conditions | 'sort'; label: string; value: string }[] = []
  if (c.procedureCode) chips.push({ key: 'procedureCode', label: t('chat.cond.procedure'), value: procedureName(c.procedureCode) })
  if (c.areas.length) chips.push({ key: 'areas', label: t('chat.cond.area'), value: c.areas.map((a) => t(`domain.area.${a}`)).join('·') })
  if (c.budgetMaxKrw) chips.push({ key: 'budgetMaxKrw', label: t('chat.cond.budget'), value: `~${fmtKrwCompact(c.budgetMaxKrw)}` })
  if (c.consultLanguage) chips.push({ key: 'consultLanguage', label: t('chat.cond.language'), value: t(`domain.langName.${c.consultLanguage}`) })
  if (c.dateFrom)
    chips.push({ key: 'dateFrom', label: t('chat.cond.date'), value: [c.dateFrom, c.dateTo].filter(Boolean).map((d) => fmtDate(d!, { weekday: false })).join('–') })
  if (c.sortBy) chips.push({ key: 'sort', label: t('chat.cond.sort'), value: t(`domain.sort.${c.sortBy}`) })
  return chips
})

// ─── 메시지 ───
// AI 메시지 사이에 상담 블록(m 없음)을 상담 요청 시각 위치에 끼워 넣는다 → 종료 후 AI 대화는 상담 아래로
const timeline = computed(() => {
  const rows: { m?: ConversationMessage; i: number }[] = conv.messages.map((m, i) => ({ m, i }))
  const c = consult.current
  if (c && c.id === conv.consultationId) {
    // 로컬은 Z, 서버는 +09:00 이라 문자열 비교 대신 Date.parse
    const at = Date.parse(c.createdAt)
    const k = conv.messages.findIndex((m) => Date.parse(m.createdAt) > at)
    rows.splice(k < 0 ? rows.length : k, 0, { i: -1 })
  }
  return rows
})
const lastCardsIndex = computed(() => conv.messages.map((m) => m.cards.length > 0).lastIndexOf(true))
const showTyping = computed(() => conv.streaming && !conv.draft && !conv.pendingAction)
const pending = computed(() => conv.pendingAction)
// 답변 중이거나 승인 카드가 떠 있으면 새 요청을 보낼 수 없다 (store.send 가 무시함) → 입력·버튼을 미리 막는다
const busy = computed(() => conv.streaming || !!conv.pendingAction)
const consultRows = computed(() => {
  const s = consult.current?.summaryCard
  if (!s) return []
  return [
    { label: t('chat.summary.procedure'), value: s.procedure },
    { label: t('chat.summary.dates'), value: s.preferredDates },
    ...(s.stayDays ? [{ label: t('chat.summary.stay'), value: t('chat.summary.days', { n: s.stayDays }) }] : []),
    ...(s.budget ? [{ label: t('chat.summary.budget'), value: s.budget }] : []),
    { label: t('chat.summary.language'), value: t(`domain.langName.${s.customerLocale}`) },
  ]
})
const pendingQuestions = computed(() => {
  const card = pending.value?.args.summaryCard as { questions?: string[] } | undefined
  return card?.questions ?? []
})
const isMine = (m: ChatMessage) => m.senderRole === 'CUSTOMER'
// D-43: 한국어 고객은 번역 없이 그대로 전달 → 번역 안내·원문 보기를 숨긴다
const untranslated = (m: ChatMessage) => m.translatedLang === m.originalLang
function myStatus(m: ChatMessage) {
  if (m.translationStatus === 'PENDING') return t('chat.human.translating')
  if (m.translationStatus === 'FAILED') return t('chat.human.failed')
  if (untranslated(m)) return ''
  return m.translatedLang ? t('chat.human.sentIn', { lang: t(`domain.langName.${m.translatedLang}`) }) : ''
}
function toggleOriginal(id: number) {
  const s = new Set(shownOriginal.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  shownOriginal.value = s
}

// ─── C4-T 상담 주제 · 피부 고민 ───
const pickingTopic = ref(false)
const showTopics = computed(() => !isHospital.value && !busy.value && (pickingTopic.value || (!conv.topic && !conv.messages.length)))
const topicLabel = (topic: ConsultTopic) => t(`chat.topic.items.${topic}`)
const QUICK: { key: string; topic?: ConsultTopic; to?: string }[] = [
  { key: 'procedures', topic: 'SKIN_CONCERN' },
  { key: 'hospitals', topic: 'HOSPITAL_SEARCH' },
  { key: 'reservations', to: '/reservations' },
  { key: 'faq' },
  { key: 'list', to: '/chats' },
]
function quickReply(q: (typeof QUICK)[number]) {
  if (q.to) void router.push(q.to)
  else if (q.topic) pickTopic(q.topic)
  else void conv.send(t(`chat.quick.${q.key}`))
}
function pickTopic(topic: ConsultTopic) {
  pickingTopic.value = false
  addingConcern.value = false
  const label = topicLabel(topic)
  // 시작 안내 pill 은 화면에만 (서버 기록 X — 새로고침 후엔 사용자 말풍선·주제 바로 남음)
  conv.messages.push({ role: 'system', text: t('chat.topic.started', { topic: label }), sources: [], cards: [], createdAt: new Date().toISOString() })
  void conv.send(label, { type: 'SELECT_TOPIC', topic })
}
const concerns = ref<SkinConcern[]>([])
const addingConcern = ref(false)
const lastProcIndex = computed(() => conv.messages.map((m) => !!m.procedures?.length).lastIndexOf(true))
// 고민 칩은 주제를 막 고른 직후(마지막 사용자 말이 주제 선택)에만. 고민을 고른 뒤 AI 가 되물어도 다시 띄우지 않는다
const justPickedConcernTopic = computed(
  () => conv.messages.filter((m) => m.role === 'user').at(-1)?.text === topicLabel('SKIN_CONCERN'),
)
const showConcerns = computed(
  () => conv.topic === 'SKIN_CONCERN' && !busy.value && !pickingTopic.value && (addingConcern.value || justPickedConcernTopic.value),
)
function toggleConcern(c: SkinConcern) {
  concerns.value = concerns.value.includes(c) ? concerns.value.filter((x) => x !== c) : [...concerns.value, c]
}
function submitConcerns() {
  const list = SKIN_CONCERNS.filter((c) => concerns.value.includes(c))
  concerns.value = []
  addingConcern.value = false
  void conv.send(list.map((c) => t(`chat.concern.items.${c}`)).join(', '), { type: 'FIND_BY_CONCERNS', concerns: list })
}
function findHospitals(procs: ProcedureInfo[]) {
  void conv.send(t('chat.concern.findText', { names: procs.map((p) => p.name).join(', ') }))
}

// ─── 입력 ───
const placeholder = computed(() => {
  if (isHuman.value) return consultStatus.value === 'WAITING' ? t('chat.input.waiting') : t('chat.input.human')
  if (conv.pendingAction) return t('chat.input.approvalPending')
  return isHospital.value ? t('chat.input.agent') : t('chat.input.ai')
})
const canSend = computed(() => input.value.trim().length > 0 && (isHuman.value ? !!consult.current : !busy.value) && !loading.value && !loadFailed.value)
async function submit() {
  const text = input.value.trim()
  if (!text || !canSend.value) return
  input.value = ''
  if (isHuman.value) await consult.send(text, 'CUSTOMER', (auth.user?.locale ?? 'en') as Locale)
  else await conv.send(text)
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    void submit()
  }
}
function editCondition(label: string) {
  input.value = `${label}: `
  void nextTick(() => inputEl.value?.focus())
}

// ─── 액션 ───
async function decide(approved: boolean, editedArgs: Record<string, unknown> | null = null) {
  if (approving.value) return
  approving.value = true
  try {
    await conv.approve(approved, editedArgs)
  } catch (e) {
    showToast(toApiError(e)?.message || t('common.error'))
  } finally {
    approving.value = false
  }
}
const approve = (editedArgs: Record<string, unknown> | null = null) => decide(true, editedArgs)
const reject = () => decide(false)
async function compareCards(cards: { id: number; name: string }[]) {
  if (busy.value || !cards.length) return
  const names = cards.slice(0, 3).map((c) => c.name).join(', ')
  await conv.send(t('compare.askAiMessage', { names, procedure: procedureName(conv.conditions?.procedureCode ?? null) }))
}
async function newConversation() {
  if (conv.streaming || startingConversation.value) return
  startingConversation.value = true
  try {
    const created = await conv.open()
    input.value = ''
    evidence.value = null
    requested.value = null
    search.compareIds = []
    await router.push(`/chat/${created.id}`)
  } catch {
    showToast(t('common.error'))
  } finally {
    startingConversation.value = false
  }
}
// 고객 상담 종료 (WAITING 이면 요청 취소). 종료 후 병원 대화 복귀는 아래 CLOSED watch 가 맡는다
const canEndConsult = computed(() => isHuman.value && !!consult.current && ['WAITING', 'ACTIVE'].includes(consultStatus.value))
const endConsultOpen = ref(false)
const endingConsult = ref(false)
async function endConsult() {
  const waiting = consultStatus.value === 'WAITING'
  endingConsult.value = true
  try {
    await consult.endByCustomer()
    endConsultOpen.value = false
    showToast(t(waiting ? 'chat.human.cancelled' : 'chat.human.ended'))
  } catch {
    showToast(t('common.error'))
  } finally {
    endingConsult.value = false
  }
}
async function cancelRequested() {
  if (!requested.value) return
  await reservations.cancel(requested.value.id)
  requested.value = { ...requested.value, status: 'CANCELLED' }
  showToast(t('chat.requested.cancelled'))
}
function saveMemory() {
  const fields = conv.memoryProposal?.fields
  conv.memoryProposal = null
  if (fields) void conv.send(null, { type: 'SAVE_PROFILE', fields })
}

// ─── 진입·전환 ───
/** 대화가 바뀌면 화면에만 있는 상태를 비운다 (이전 대화의 예약 카드·입력이 남지 않게) */
function resetLocal() {
  input.value = ''
  evidence.value = null
  requested.value = null
  consent.value = false
  concerns.value = []
  addingConcern.value = false
  pickingTopic.value = false
  shownOriginal.value = new Set()
  infoOpen.value = false
  endConsultOpen.value = false
}
let enterSeq = 0
async function enter() {
  const id = route.params.conversationId as string | undefined
  const seq = ++enterSeq
  loadFailed.value = false
  // 같은 대화로 돌아오는 경우(refresh)는 화면을 그대로 두고, 다른 대화를 불러올 때만 로딩 표시
  loading.value = !id || conv.conversationId !== id
  try {
    if (id) {
      if (conv.conversationId !== id) await conv.load(id)
      else {
        await conv.refresh(id)
        // 상담을 못 불러와도 대화 자체는 보여 준다
        if (conv.consultationId) await consult.open(conv.consultationId).catch(() => undefined)
      }
    } else {
      const hospitalId = route.query.hospitalId ? Number(route.query.hospitalId) : null
      // 메인 대화는 최근 것을 이어 감 (빈 대화가 쌓이지 않게)
      if (!hospitalId && !route.query.q) {
        const last = (await aiApi.conversations().catch(() => [])).find((c) => c.mode === 'MAIN')
        if (last) return void (await router.replace(`/chat/${last.id}`))
      }
      const created = await conv.open(hospitalId, conv.mode === 'MAIN' && hospitalId ? conv.conversationId : null)
      const q = typeof route.query.q === 'string' ? route.query.q : null
      await router.replace(`/chat/${created.id}`)
      // 홈 AI 입력창·비교표 "AI에게 물어보기"에서 넘어온 첫 질문
      if (q) await conv.send(q)
    }
  } catch (e) {
    // 없는 대화·남의 대화 링크만 새 메인 대화로. 그 밖의 오류(네트워크·5xx)는 재시도 화면 (상담 중 대화를 잃지 않게)
    const code = toApiError(e)?.code
    if (code !== 'NOT_FOUND' && code !== 'ACCESS_DENIED') return void (loadFailed.value = true)
    try {
      const created = await conv.open()
      await router.replace(`/chat/${created.id}`)
    } catch {
      loadFailed.value = true
    }
  } finally {
    if (seq === enterSeq) {
      loading.value = false
      // 대화를 열면 맨 아래(최신 메시지)부터
      await nextTick()
      scroller.value?.scrollTo({ top: scroller.value.scrollHeight })
    }
  }
}
onMounted(() => {
  void search.loadProcedures().catch(() => undefined)
  void enter()
})
watch(
  () => route.params.conversationId,
  (id, prev) => {
    if (id === prev) return
    resetLocal()
    void enter()
  },
)
watch(
  () => conv.openedConversation,
  (o) => {
    if (o) {
      conv.openedConversation = null
      void router.push(`/chat/${o.conversationId}`)
    }
  },
)
// 승인 카드가 바뀌면 동의 체크를 다시 받는다 (이전 요청의 동의를 재사용하지 않음)
watch(pending, () => (consent.value = false))
// 상담원이 상담을 종료하면 (STOMP CONSULTATION_STATUS · 재진입 시 조회) 병원 대화로 돌아가 AI 가 다시 답함
watch(
  () => consult.current?.status,
  (s) => {
    if (s === 'CLOSED' && consult.current?.id === conv.consultationId && conv.mode === 'HUMAN') conv.mode = aftercare.value ? 'AFTERCARE' : 'HOSPITAL'
  },
)
// 종료된 상담도 ID로 다시 불러와 요약·통역 기록을 유지한다.
watch(
  () => conv.consultationId,
  (cid) => {
    if (cid && consult.current?.id !== cid) void consult.open(cid).catch(() => undefined)
    if (!cid) consult.close()
  },
  { immediate: true },
)
// 예약 승인 후 DONE → 방금 요청한 예약 카드 (C4-2 요청 완료)
watch(
  () => conv.streaming,
  async (streaming) => {
    if (streaming || conv.approvedAction !== 'CREATE_RESERVATION') return
    conv.approvedAction = null
    await reservations.loadMine().catch(() => undefined)
    requested.value =
      reservations.mine.filter((r) => r.status === 'PENDING' && r.hospital.id === conv.hospital?.id).sort((a, b) => b.createdAt.localeCompare(a.createdAt))[0] ??
      null
  },
)
onBeforeUnmount(() => consult.close())

// 자동 스크롤: 맨 아래 근처(80px)일 때만 따라감 (04 ⑤)
function nearBottom() {
  const el = scroller.value
  return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 80
}
watch(
  () =>
    [conv.messages.length, conv.draft, conv.pendingAction, conv.cards.length, conv.activeTools.length, showTyping.value, consult.messages.length, conv.error, requested.value, showTopics.value, showConcerns.value] as const,
  async () => {
    const stick = nearBottom()
    await nextTick()
    // 답변이 흘러나오는 중엔 smooth 가 겹쳐 따라가기를 놓치므로 바로 이동
    if (stick) scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: conv.streaming ? 'auto' : 'smooth' })
  },
)
</script>

<template>
  <div class="chat">
    <TopAppBar chat :back="isHospital && conv.parentConversationId ? `/chat/${conv.parentConversationId}` : '/chats'">
      <template #title>
        <h1 class="t-body-16-sb ellipsis">{{ title }}</h1>
      </template>
      <template #subtitle>
        <AppBadge :tone="modeBadge.tone" :icon="modeBadge.icon">{{ modeBadge.label }}</AppBadge>
      </template>
      <template #right>
        <button v-if="!isHospital" type="button" class="icon-btn" :aria-label="t('chat.newConversation')"
          :title="t('chat.newConversation')" :disabled="conv.streaming || startingConversation" @click="newConversation">
          <AppIcon name="plus" />
        </button>
        <RouterLink to="/chats" class="icon-btn" :aria-label="t('chat.list.open')"><AppIcon name="message-circle" /></RouterLink>
        <button type="button" class="icon-btn" :aria-label="t('chat.info.title')" @click="infoOpen = true">
          <AppIcon name="info" />
        </button>
      </template>
    </TopAppBar>

    <AftercareHeader v-if="aftercare" :room="aftercare" />
    <AppBanner v-if="isHuman && consult.current && !consult.connected" type="reconnecting">{{ t('chat.reconnecting') }}</AppBanner>

    <!-- C4-T 상담 주제 바 -->
    <div v-if="!isHospital && conv.topic" class="topic-bar">
      <AppIcon name="sparkles" :size="16" />
      <span class="t-caption-12 secondary">{{ t('chat.topic.label') }}</span>
      <strong class="topic-bar__name t-caption-13">{{ topicLabel(conv.topic) }}</strong>
      <button v-if="!busy" type="button" class="topic-bar__change t-caption-12" @click="pickingTopic = true">
        {{ t('chat.topic.change') }}<AppIcon name="chevron-right" :size="14" />
      </button>
    </div>

    <div v-if="!isHospital && conditionChips.length" class="conditions" role="list" :aria-label="t('chat.cond.label')">
      <AppChip v-for="c in conditionChips" :key="c.key" type="condition" :label="c.label" role="listitem" @click="editCondition(c.label)">
        {{ c.value }}
      </AppChip>
    </div>

    <EmptyState v-if="loadFailed" class="load-failed" icon="alert-triangle" tone="danger" :title="t('common.error')">
      <AppButton variant="secondary" icon="refresh-cw" @click="enter">{{ t('common.retry') }}</AppButton>
    </EmptyState>
    <div v-else-if="loading" class="messages" role="status" :aria-label="t('common.loading')" aria-busy="true">
      <span class="bone bone--ai" /><span class="bone bone--user" /><span class="bone bone--ai bone--short" />
    </div>
    <div v-else ref="scroller" class="messages" aria-live="polite">
      <!-- 병원 대화: 메인 대화에서 이어받은 조건 (D-20) -->
      <section v-if="isHospital && conv.parentConversationId && conditionChips.length" class="inherit">
        <p class="inherit__head t-caption-12-sb">
          <AppIcon name="sparkles" :size="14" />
          <span>{{ t('chat.inherited') }}</span>
          <RouterLink :to="`/chat/${conv.parentConversationId}`" class="link">{{ t('chat.backToMain') }}</RouterLink>
        </p>
        <div class="inherit__tags">
          <AppBadge v-for="c in conditionChips" :key="c.key" tag>{{ c.value }}</AppBadge>
        </div>
      </section>

      <!-- C4-T 첫 진입: 환영 말풍선 (주제 카드는 아래) -->
      <ChatBubble v-if="!isHospital && !conv.messages.length" sender="ai" :name="t('chat.aiTitle')" :text="t('chat.welcome')" />
      <p v-else-if="!conv.messages.length && !conv.streaming" class="hello t-body-14">
        {{ t('chat.helloAgent', { hospital: conv.hospital?.name ?? '' }) }}
      </p>

      <template v-for="{ m, i } in timeline" :key="i">
        <!-- 상담원 대기 · 통역 채팅 · 종료 후 기록 (상담 요청 시각 자리) -->
        <template v-if="!m">
          <template v-if="consult.current">
            <ConsultSummaryCard collapsible :rows="consultRows" :questions="consult.current.summaryCard.questions" />
            <ChatBubble sender="system" :text="t('chat.human.requestedAt', { time: fmtTime(consult.current.createdAt) })" />
            <section v-if="consultStatus === 'WAITING'" class="waiting">
              <span class="waiting__icon"><AppIcon name="headphones" /></span>
              <p class="t-body-16-sb">{{ t('chat.human.waitingTitle') }}</p>
              <p class="t-body-14 secondary">{{ t('chat.human.waitingBody') }}</p>
            </section>
            <template v-for="cm in consult.messages" :key="cm.clientMsgId ?? cm.id">
              <ChatBubble v-if="cm.senderRole === 'SYSTEM'" sender="system" :text="cm.translatedText ?? cm.originalText" />
              <ChatBubble
                v-else-if="isMine(cm)"
                sender="me"
                :text="cm.originalText"
                :time="fmtTime(cm.createdAt)"
                :failed="cm.translationStatus === 'FAILED'"
              >
                <button
                  v-if="cm.translationStatus === 'FAILED'"
                  type="button"
                  class="status status--failed t-caption-12-sb"
                  @click="consult.retryTranslation(cm)"
                >
                  <AppIcon name="alert-triangle" :size="14" />{{ myStatus(cm) }}
                </button>
                <span v-else-if="myStatus(cm)" class="status t-caption-11">
                  <AppIcon v-if="cm.translationStatus === 'DONE'" name="languages" :size="14" />{{ myStatus(cm) }}
                </span>
              </ChatBubble>
              <ChatBubble v-else sender="counselor" :name="t('chat.counselor')" :text="cm.translatedText ?? cm.originalText">
                <p v-if="shownOriginal.has(cm.id) && !untranslated(cm)" class="original t-caption-12">{{ cm.originalText }}</p>
                <button v-if="!untranslated(cm)" type="button" class="status t-caption-11" @click="toggleOriginal(cm.id)">
                  <AppIcon name="languages" :size="14" />
                  {{ shownOriginal.has(cm.id) ? t('chat.human.hideOriginal') : t('chat.human.autoTranslated') }}
                </button>
              </ChatBubble>
            </template>
            <p v-if="consultStatus === 'WAITING'" class="t-caption-12 muted center">{{ t('chat.human.waitingNote') }}</p>
          </template>
        </template>
        <ChatBubble v-else-if="m.role === 'user'" sender="me" :text="m.text" :time="fmtTime(m.createdAt)" />
        <ChatBubble v-else-if="m.role === 'system'" sender="system" :text="m.text" />
        <ChatBubble v-else-if="m.role === 'counselor'" sender="counselor" :name="t('chat.counselor')" :text="m.text" />
        <div v-else class="group">
          <ChatBubble :sender="isHospital ? 'agent' : 'ai'" :name="assistantName" :text="m.text">
            <AppChip v-if="m.sources.length" type="evidence" @click="evidence = m.sources">
              {{ t('chat.evidenceCount', { n: m.sources.length }) }}
            </AppChip>
          </ChatBubble>
          <template v-if="m.cards.length">
            <p class="inset basis t-caption-12">
              <AppIcon name="info" :size="14" />
              {{
                t('chat.sortBasis', {
                  sort: t(`domain.sort.${conv.conditions?.sortBy ?? 'REVIEW_COUNT'}`),
                  procedure: procedureName(conv.conditions?.procedureCode ?? null),
                })
              }}
            </p>
            <HospitalCarousel
              :cards="m.cards"
              :procedure-name="procedureName(conv.conditions?.procedureCode ?? null)"
              @open="(id) => router.push(`/hospitals/${id}`)"
              @chat="(id) => conv.send(null, { type: 'SELECT_HOSPITAL', hospitalId: id })"
            />
            <div v-if="i === lastCardsIndex" class="inset row-actions">
              <AppButton variant="outline" size="s" :disabled="busy" @click="compareCards(m.cards)">
                {{ t('chat.compareN', { n: Math.min(3, m.cards.length) }) }}
              </AppButton>
              <AppButton variant="ghost" size="s" @click="inputEl?.focus()">{{ t('chat.changeConditions') }}</AppButton>
            </div>
          </template>
          <!-- C4-T 고민 관련 시술 정보 -->
          <template v-if="m.procedures?.length">
            <div class="inset procs">
              <ProcedureInfoCard v-for="p in m.procedures" :key="p.procedureCode" :info="p" />
            </div>
            <p class="inset t-caption-12 muted">{{ t('chat.concern.disclaimer') }}</p>
            <div v-if="i === lastProcIndex && !busy && !showConcerns" class="inset chips">
              <AppChip @click="findHospitals(m.procedures)">{{ t('chat.concern.find', m.procedures.length) }}</AppChip>
              <AppChip @click="addingConcern = true">{{ t('chat.concern.more') }}</AppChip>
            </div>
          </template>
        </div>
      </template>

      <!-- 스트리밍 중 -->
      <ChatBubble v-if="conv.draft" :sender="isHospital ? 'agent' : 'ai'" :name="assistantName" :text="conv.draft" />
      <ChatBubble v-else-if="showTyping" sender="typing" />
      <div v-if="conv.activeTools.length" class="inset progress">
        <AppChip v-for="tool in conv.activeTools" :key="tool.tool" type="progress">{{ tool.label }}</AppChip>
      </div>

      <!-- C4-T 피부 고민 선택 (여러 개) -->
      <section v-if="showConcerns" class="inset concerns">
        <div class="chips">
          <AppChip v-for="c in SKIN_CONCERNS" :key="c" :selected="concerns.includes(c)" @click="toggleConcern(c)">
            {{ t(`chat.concern.items.${c}`) }}
          </AppChip>
        </div>
        <AppButton size="s" :disabled="!concerns.length" @click="submitConcerns">{{ concerns.length ? t('chat.concern.done', { n: concerns.length }) : t('chat.concern.pick') }}</AppButton>
        <p class="t-caption-12 muted">{{ t('chat.concern.note') }}</p>
      </section>
      <TopicCarousel v-if="showTopics" @pick="pickTopic" />

      <!-- Edge ① 0건 → AI 가 정한 완화안 (D-35: 탭하면 문구를 message 로) -->
      <div v-if="conv.relaxOptions.length && !busy" class="inset relax">
        <button
          v-for="o in conv.relaxOptions.filter((x) => x.expectedCount > 0)"
          :key="o.option"
          type="button"
          class="relax__item"
          @click="conv.send(o.label)"
        >
          <span class="t-body-14-sb">{{ o.label }}</span>
          <span class="t-body-14-sb brand">{{ t('chat.relaxCount', { n: o.expectedCount }) }}</span>
          <AppIcon name="chevron-right" :size="18" />
        </button>
        <button type="button" class="link t-caption-13" @click="inputEl?.focus()">{{ t('chat.relaxManual') }}</button>
      </div>

      <!-- C4-2 예약 승인 카드 -->
      <div v-if="pending && pending.action !== 'REQUEST_CONSULTATION'" class="inset">
        <ApprovalCard :action="pending" :busy="approving" @approve="approve" @reject="reject" />
      </div>
      <!-- C4-3 상담 요청 요약 (동의는 아래 dock) -->
      <ConsultSummaryCard v-if="pending?.action === 'REQUEST_CONSULTATION'" :rows="pending.display.rows" :questions="pendingQuestions" />

      <!-- C4-2 요청 완료 · 승인 대기 -->
      <section v-if="requested" class="inset">
        <div class="requested">
          <div class="requested__badges">
            <AppBadge :tone="RESERVATION_TONE[requested.status]" dot>{{ t(`domain.status.${requested.status}`) }}</AppBadge>
            <AppBadge v-if="requested.status === 'PENDING' && remaining(requested.holdExpiresAt, now)" tone="warning" icon="clock">
              {{ t('domain.holdLeft', { time: remaining(requested.holdExpiresAt, now) }) }}
            </AppBadge>
          </div>
          <p class="t-body-16-sb">{{ fmtDateTime(requested.slot.startAt) }} · {{ requested.slot.doctorName }}</p>
          <p class="t-caption-13 secondary">
            {{ requested.procedure.name }}<template v-if="requested.priceOption"> · {{ fmtKrw(requested.priceOption.priceKrw) }}</template>
          </p>
          <p class="t-caption-12 muted">{{ t('chat.requested.note') }}</p>
          <div class="requested__actions">
            <AppButton variant="secondary" size="s" block @click="router.push('/reservations')">{{ t('chat.requested.view') }}</AppButton>
            <AppButton v-if="requested.status === 'PENDING'" variant="ghost" size="s" block @click="cancelRequested">
              {{ t('chat.requested.cancel') }}
            </AppButton>
          </div>
        </div>
      </section>

      <!-- 일정 카드 · 기억 제안 (04 ④) -->
      <div v-if="conv.tripPlan" class="inset">
        <TripPlanCard :plan="conv.tripPlan" :procedure-name="(c) => procedureName(c)" />
      </div>
      <section v-if="conv.memoryProposal && !busy" class="memory">
        <p class="t-body-14"><AppIcon name="sparkles" :size="16" class="brand" />{{ conv.memoryProposal.message }}</p>
        <div class="memory__actions">
          <AppButton variant="ghost" size="s" @click="conv.memoryProposal = null">{{ t('chat.memory.no') }}</AppButton>
          <AppButton size="s" @click="saveMemory">{{ t('chat.memory.yes') }}</AppButton>
        </div>
      </section>

      <!-- Edge ② 응답 실패 -->
      <ChatBubble v-if="conv.error" sender="error" :text="t('chat.failed')" @retry="conv.retry()" />

    </div>

    <div v-if="showTopics && !conv.messages.length" class="quick-replies">
      <AppChip v-for="q in QUICK" :key="q.key" @click="quickReply(q)">{{ t(`chat.quick.${q.key}`) }}</AppChip>
    </div>

    <!-- 하단: C4-3 동의 dock / 병원 대화 빠른 버튼 + 입력창 -->
    <footer v-if="pending?.action === 'REQUEST_CONSULTATION'" class="dock dock--consent">
      <label class="consent">
        <input v-model="consent" type="checkbox" />
        <span class="box" aria-hidden="true"><AppIcon v-if="consent" name="check" :size="14" /></span>
        <span class="t-body-14">{{ t('chat.consent.label') }}</span>
      </label>
      <p class="t-caption-12 muted consent__desc">{{ t('chat.consent.desc', { hospital: conv.hospital?.name ?? '' }) }}</p>
      <AppButton block :disabled="!consent" :loading="approving" @click="approve()">{{ t('chat.consent.submit') }}</AppButton>
      <AppButton variant="ghost" block :disabled="approving" @click="reject()">{{ t('chat.consent.decline') }}</AppButton>
      <p class="t-caption-12 muted center">{{ t('chat.consent.note') }}</p>
    </footer>
    <AftercareClosed v-else-if="aftercare && isAftercareClosed(aftercare)" />
    <footer v-else class="dock">
      <div v-if="isHospital && !isHuman && !pending && !conv.streaming" class="quick">
        <AppButton variant="outline" block @click="conv.send(t('chat.requestCounselor'))">{{ t('chat.connectCounselor') }}</AppButton>
        <AppButton v-if="conv.mode !== 'AFTERCARE'" block @click="router.push(`/hospitals/${conv.hospital?.id}/book`)">{{ t('chat.book') }}</AppButton>
      </div>
      <div v-if="canEndConsult" class="quick">
        <AppButton variant="outline" block @click="endConsultOpen = true">
          {{ consultStatus === 'WAITING' ? t('chat.human.cancelRequest') : t('chat.human.end') }}
        </AppButton>
      </div>
      <form class="input" @submit.prevent="submit">
        <textarea
          ref="inputEl"
          v-model="input"
          rows="1"
          class="input__field t-body-15"
          :placeholder="placeholder"
          :aria-label="placeholder"
          @keydown="onKey"
        />
        <button type="submit" class="input__send" :class="{ 'input__send--on': canSend }" :disabled="!canSend" :aria-label="t('chat.send')">
          <AppIcon name="send" :size="20" />
        </button>
      </form>
    </footer>

    <EvidenceSheet :open="!!evidence" :sources="evidence ?? []" @close="evidence = null" />
    <AppDialog :open="infoOpen" :title="t('chat.info.title')" :body="t('chat.info.body')">
      <template #actions><AppButton @click="infoOpen = false">{{ t('common.confirm') }}</AppButton></template>
    </AppDialog>
    <AppDialog
      :open="endConsultOpen"
      :title="consultStatus === 'WAITING' ? t('chat.human.cancelTitle') : t('chat.human.endTitle')"
      :body="consultStatus === 'WAITING' ? t('chat.human.cancelBody') : t('chat.human.endBody')"
    >
      <template #actions>
        <AppButton variant="secondary" :disabled="endingConsult" @click="endConsultOpen = false">{{ t('common.cancel') }}</AppButton>
        <AppButton variant="primary" :loading="endingConsult" @click="endConsult">
          {{ consultStatus === 'WAITING' ? t('chat.human.cancelRequest') : t('chat.human.end') }}
        </AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.chat { display: flex; flex-direction: column; height: 100dvh; }
.ellipsis { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.icon-btn { display: grid; place-items: center; border: 0; background: none; color: var(--icon-default); }
.conditions {
  display: flex;
  gap: var(--space-8);
  flex: none;
  padding: var(--space-8) var(--space-16);
  overflow-x: auto;
  border-bottom: 1px solid var(--border-default);
  scrollbar-width: none;
}
.topic-bar {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--space-6);
  padding: 10px var(--space-16);
  border-bottom: 1px solid var(--border-default);
  background: var(--brand-subtle);
  color: var(--icon-default);
}
.topic-bar__name { flex: 1; min-width: 0; overflow: hidden; color: var(--brand-text); text-overflow: ellipsis; white-space: nowrap; }
.topic-bar__change { display: inline-flex; align-items: center; gap: var(--space-2); padding: 0; border: 0; background: none; color: var(--text-secondary); }
.quick-replies { display: flex; flex: none; gap: var(--space-8); padding: var(--space-8) var(--space-16) var(--space-4); overflow-x: auto; background: var(--surface-card); scrollbar-width: none; }
.quick-replies::-webkit-scrollbar { display: none; }
.procs { display: flex; flex-direction: column; gap: var(--space-8); }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.concerns { display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-16); }
.messages { display: flex; flex: 1; flex-direction: column; gap: var(--space-16); padding: var(--space-16); overflow-y: auto; }
.messages > :first-child { margin-top: auto; }
.messages { scrollbar-width: none; }
.messages::-webkit-scrollbar { display: none; }
.hello { color: var(--text-tertiary); text-align: center; }
.group { display: flex; flex-direction: column; gap: var(--space-6); }
.inset { padding-left: 40px; }
.basis { display: flex; align-items: center; gap: var(--space-4); color: var(--text-tertiary); }
.row-actions, .progress { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.relax { display: flex; flex-direction: column; gap: var(--space-8); }
.relax__item {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-12) var(--space-16);
  border: 1px solid var(--brand-border);
  border-radius: var(--radius-md);
  background: var(--bg-default);
  text-align: left;
}
.relax__item > :first-child { flex: 1; }
.relax__item .icon { color: var(--icon-subtle); }
.brand { color: var(--brand-text); }
.link { align-self: flex-start; padding: 0; border: 0; background: none; color: var(--text-secondary); text-decoration: underline; }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.center { text-align: center; }

.inherit { display: flex; flex-direction: column; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); background: var(--bg-subtle); }
.inherit__head { display: flex; align-items: center; gap: var(--space-6); color: var(--text-secondary); }
.inherit__head .icon { color: var(--brand-primary); }
.inherit__head .link { margin-left: auto; color: var(--text-brand); text-decoration: none; }
.inherit__tags { display: flex; flex-wrap: wrap; gap: var(--space-4); }

.requested { display: flex; flex-direction: column; gap: var(--space-8); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); }
.requested__badges, .requested__actions { display: flex; gap: var(--space-8); }

.memory { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16); border-radius: var(--radius-md); background: var(--brand-subtle); }
.memory p { display: flex; gap: var(--space-6); }
.memory__actions { display: flex; justify-content: flex-end; gap: var(--space-8); }

.waiting { display: flex; flex-direction: column; align-items: center; gap: var(--space-8); padding: var(--space-24) var(--space-16); border-radius: var(--radius-lg); background: var(--status-info-bg); text-align: center; }
.waiting__icon { display: grid; place-items: center; width: 48px; height: 48px; margin-bottom: var(--space-4); border-radius: 50%; background: var(--bg-default); color: var(--chat-counselor-accent); }
.status { display: inline-flex; align-items: center; gap: var(--space-4); padding: 0; border: 0; background: none; color: var(--text-tertiary); }
.status--failed { color: var(--status-danger); }
.original { max-width: 264px; padding: var(--space-8) var(--space-12); border-radius: var(--radius-sm); background: var(--bg-muted); color: var(--text-secondary); }

.load-failed { flex: 1; }
.bone { display: block; height: 48px; border-radius: var(--radius-lg); background: var(--bg-muted); animation: shimmer 1.2s ease-in-out infinite; }
.bone--ai { width: 72%; }
.bone--user { width: 48%; align-self: flex-end; }
.bone--short { width: 40%; }
@keyframes shimmer { 50% { opacity: 0.5; } }
.dock { flex: none; border-top: 1px solid var(--border-default); background: var(--bg-default); padding-bottom: env(safe-area-inset-bottom); }
.quick { display: flex; gap: var(--space-8); padding: var(--space-12) var(--space-16) 0; }
.input { display: flex; align-items: flex-end; gap: var(--space-8); padding: 10px var(--space-12); }
.input__field {
  flex: 1;
  min-height: 44px;
  max-height: 120px;
  padding: 11px var(--space-16);
  border: 0;
  border-radius: 22px;
  background: var(--bg-muted);
  resize: none;
  outline: none;
  field-sizing: content;
}
.input__field::placeholder { color: var(--text-tertiary); }
.input__send { display: grid; place-items: center; flex: none; width: 44px; height: 44px; border: 0; border-radius: 50%; background: var(--bg-muted); color: var(--icon-subtle); }
.input__send--on { background: var(--brand-primary); color: var(--text-inverse); }
.dock--consent { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16) var(--space-16) var(--space-8); }
.consent { position: relative; display: flex; align-items: center; gap: var(--space-8); cursor: pointer; }
.consent input { position: absolute; opacity: 0; width: 1px; height: 1px; }
.box { display: grid; place-items: center; flex: none; width: 20px; height: 20px; border: 1.5px solid var(--border-strong); border-radius: var(--radius-xs); color: var(--text-inverse); }
.consent input:checked + .box { border-color: var(--brand-primary); background: var(--brand-primary); }
.consent input:focus-visible + .box { outline: 2px solid var(--border-focus); outline-offset: 2px; }
.consent__desc { margin-top: -8px; padding-left: 28px; }
</style>
