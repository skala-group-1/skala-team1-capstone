<script setup lang="ts">
// 「화면 목록」 C4 AI 채팅 — 메인 AI(MAIN) · 병원 대화(HOSPITAL) · 상담원 연결(HUMAN) 공용 (Figma 02 C4 섹션 + Edge ①②③ + 04 ④ 일정/기억)
// SSE 는 conversation 스토어 reducer, HUMAN 모드 메시지는 consultation 스토어(STOMP)
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { aiApi } from '@/api'
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
import HospitalCarousel from '@/components/chat/HospitalCarousel.vue'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import ApprovalCard from '@/components/chat/ApprovalCard.vue'
import ConsultSummaryCard from '@/components/chat/ConsultSummaryCard.vue'
import EvidenceSheet from '@/components/chat/EvidenceSheet.vue'
import TripPlanCard from '@/components/chat/TripPlanCard.vue'
import type { ChatMessage, Conditions, Locale, Reservation, Source } from '@/types/contract'

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

// ─── 모드 ───
const isHospital = computed(() => conv.mode !== 'MAIN')
const isHuman = computed(() => conv.mode === 'HUMAN')
const consultStatus = computed(() => consult.current?.status ?? 'WAITING')
const title = computed(() => (isHospital.value ? (conv.hospital?.name ?? '') : t('chat.aiTitle')))
const modeBadge = computed(() => {
  if (!isHospital.value) return { tone: 'brand' as const, icon: 'sparkles' as const, label: t('chat.mode.ai') }
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
const lastCardsIndex = computed(() => conv.messages.map((m) => m.cards.length > 0).lastIndexOf(true))
const showTyping = computed(() => conv.streaming && !conv.draft && !conv.pendingAction)
const pending = computed(() => conv.pendingAction)
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

// ─── 입력 ───
const placeholder = computed(() => {
  if (isHuman.value) return consultStatus.value === 'WAITING' ? t('chat.input.waiting') : t('chat.input.human')
  return isHospital.value ? t('chat.input.agent') : t('chat.input.ai')
})
const canSend = computed(() => input.value.trim().length > 0 && (isHuman.value || !conv.streaming))
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
async function approve(editedArgs: Record<string, unknown> | null = null) {
  approving.value = true
  try {
    await conv.approve(true, editedArgs)
  } finally {
    approving.value = false
  }
}
async function reject() {
  await conv.approve(false, null, null)
}
function compareCards(cards: { id: number }[]) {
  search.compareIds = cards.slice(0, 3).map((c) => c.id)
  void router.push({ path: '/compare', query: { ids: search.compareIds.join(','), procedure: conv.conditions?.procedureCode ?? undefined } })
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
async function enter() {
  const id = route.params.conversationId as string | undefined
  try {
    if (id) {
      if (conv.conversationId !== id) await conv.load(id)
      else {
        await conv.refresh(id)
        if (conv.mode === 'HUMAN' && conv.consultationId) await consult.open(conv.consultationId)
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
  } catch {
    // 대화를 못 불러오면 새 메인 대화로
    const created = await conv.open()
    await router.replace(`/chat/${created.id}`)
  }
}
onMounted(() => {
  void search.loadProcedures().catch(() => undefined)
  void enter()
})
watch(() => route.params.conversationId, (id, prev) => id !== prev && void enter())
watch(
  () => conv.openedConversation,
  (o) => {
    if (o) {
      conv.openedConversation = null
      void router.push(`/chat/${o.conversationId}`)
    }
  },
)
// 상담원이 상담을 종료하면 (STOMP CONSULTATION_STATUS · 재진입 시 조회) 병원 대화로 돌아가 AI 가 다시 답함
watch(
  () => consult.current?.status,
  (s) => {
    if (s === 'CLOSED' && conv.mode === 'HUMAN') conv.mode = 'HOSPITAL'
  },
)
// HUMAN 모드 → 상담 STOMP 구독
watch(
  () => [conv.mode, conv.consultationId] as const,
  ([mode, cid]) => {
    if (mode === 'HUMAN' && cid && consult.current?.id !== cid) void consult.open(cid).catch(() => undefined)
    if (mode !== 'HUMAN') consult.close()
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
  () => [conv.messages.length, conv.draft, conv.pendingAction, conv.cards.length, consult.messages.length, conv.error, requested.value] as const,
  async () => {
    const stick = nearBottom()
    await nextTick()
    if (stick) scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
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
        <RouterLink to="/chats" class="icon-btn" :aria-label="t('chat.list.open')"><AppIcon name="message-circle" /></RouterLink>
        <button type="button" class="icon-btn" :aria-label="t('chat.info.title')" @click="infoOpen = true">
          <AppIcon name="info" />
        </button>
      </template>
    </TopAppBar>

    <AppBanner v-if="isHuman && consult.current && !consult.connected" type="reconnecting">{{ t('chat.reconnecting') }}</AppBanner>

    <div v-if="!isHospital && conditionChips.length" class="conditions" role="list" :aria-label="t('chat.cond.label')">
      <AppChip v-for="c in conditionChips" :key="c.key" type="condition" :label="c.label" role="listitem" @click="editCondition(c.label)">
        {{ c.value }}
      </AppChip>
    </div>

    <div ref="scroller" class="messages" aria-live="polite">
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

      <p v-if="!conv.messages.length && !conv.streaming" class="hello t-body-14">
        {{ isHospital ? t('chat.helloAgent', { hospital: conv.hospital?.name ?? '' }) : t('chat.helloAi') }}
      </p>

      <template v-for="(m, i) in conv.messages" :key="i">
        <ChatBubble v-if="m.role === 'user'" sender="me" :text="m.text" :time="fmtTime(m.createdAt)" />
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
              <AppButton variant="outline" size="s" @click="compareCards(m.cards)">
                {{ t('chat.compareN', { n: Math.min(3, m.cards.length) }) }}
              </AppButton>
              <AppButton variant="ghost" size="s" @click="inputEl?.focus()">{{ t('chat.changeConditions') }}</AppButton>
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

      <!-- Edge ① 0건 → AI 가 정한 완화안 (D-35: 탭하면 문구를 message 로) -->
      <div v-if="conv.relaxOptions.length && !conv.streaming" class="inset relax">
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
      <section v-if="conv.memoryProposal && !conv.streaming" class="memory">
        <p class="t-body-14"><AppIcon name="sparkles" :size="16" class="brand" />{{ conv.memoryProposal.message }}</p>
        <div class="memory__actions">
          <AppButton variant="ghost" size="s" @click="conv.memoryProposal = null">{{ t('chat.memory.no') }}</AppButton>
          <AppButton size="s" @click="saveMemory">{{ t('chat.memory.yes') }}</AppButton>
        </div>
      </section>

      <!-- Edge ② 응답 실패 -->
      <ChatBubble v-if="conv.error" sender="error" :text="t('chat.failed')" @retry="conv.retry()" />

      <!-- HUMAN: 상담원 대기 · 연결됨 (통역 채팅) -->
      <template v-if="isHuman && consult.current">
        <ConsultSummaryCard collapsible :rows="consultRows" :questions="consult.current.summaryCard.questions" />
        <ChatBubble sender="system" :text="t('chat.human.requestedAt', { time: fmtTime(consult.current.createdAt) })" />
        <section v-if="consultStatus === 'WAITING'" class="waiting">
          <span class="waiting__icon"><AppIcon name="headphones" /></span>
          <p class="t-body-16-sb">{{ t('chat.human.waitingTitle') }}</p>
          <p class="t-body-14 secondary">{{ t('chat.human.waitingBody') }}</p>
        </section>
        <template v-for="m in consult.messages" :key="m.clientMsgId ?? m.id">
          <ChatBubble v-if="m.senderRole === 'SYSTEM'" sender="system" :text="m.translatedText ?? m.originalText" />
          <ChatBubble
            v-else-if="isMine(m)"
            sender="me"
            :text="m.originalText"
            :time="fmtTime(m.createdAt)"
            :failed="m.translationStatus === 'FAILED'"
          >
            <button
              v-if="m.translationStatus === 'FAILED'"
              type="button"
              class="status status--failed t-caption-12-sb"
              @click="consult.retryTranslation(m)"
            >
              <AppIcon name="alert-triangle" :size="14" />{{ myStatus(m) }}
            </button>
            <span v-else-if="myStatus(m)" class="status t-caption-11">
              <AppIcon v-if="m.translationStatus === 'DONE'" name="languages" :size="14" />{{ myStatus(m) }}
            </span>
          </ChatBubble>
          <ChatBubble v-else sender="counselor" :name="t('chat.counselor')" :text="m.translatedText ?? m.originalText">
            <p v-if="shownOriginal.has(m.id) && !untranslated(m)" class="original t-caption-12">{{ m.originalText }}</p>
            <button v-if="!untranslated(m)" type="button" class="status t-caption-11" @click="toggleOriginal(m.id)">
              <AppIcon name="languages" :size="14" />
              {{ shownOriginal.has(m.id) ? t('chat.human.hideOriginal') : t('chat.human.autoTranslated') }}
            </button>
          </ChatBubble>
        </template>
        <p v-if="consultStatus === 'WAITING'" class="t-caption-12 muted center">{{ t('chat.human.waitingNote') }}</p>
      </template>
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
      <p class="t-caption-12 muted center">{{ t('chat.consent.note') }}</p>
    </footer>
    <footer v-else class="dock">
      <div v-if="isHospital && !isHuman && !pending && !conv.streaming" class="quick">
        <AppButton variant="outline" block @click="conv.send(t('chat.requestCounselor'))">{{ t('chat.connectCounselor') }}</AppButton>
        <AppButton block @click="router.push(`/hospitals/${conv.hospital?.id}/book`)">{{ t('chat.book') }}</AppButton>
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
