<script setup lang="ts">
// 「화면 목록」 S1 문의함 + S2 통역 채팅 = S2-D 상담 콘솔 (Figma 2:8920, 대기 0건 39:3564)
// 왼쪽 문의함(대기·진행·종료) · 가운데 통역 채팅(번역문 우선 + 원문 토글 + ⚠️ 플래그) · 오른쪽 상담 정보(한국어 요약 카드)
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useConsultationStore } from '@/stores/consultation'
import { useAuthStore } from '@/stores/auth'
import { useNow } from '@/composables/useNow'
import { useNotificationRefresh } from '@/composables/useNotificationRefresh'
import { showToast } from '@/composables/useToast'
import { toApiError } from '@/api'
import { fmtTime } from '@/utils/format'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppChip from '@/components/ui/AppChip.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppBanner from '@/components/ui/AppBanner.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import type { ChatMessage, Consultation, ConsultationStatus } from '@/types/contract'

const route = useRoute()
const { t } = useI18n()
const store = useConsultationStore()
const auth = useAuthStore()
const now = useNow(30_000)

const filter = ref<ConsultationStatus | 'ALL'>('ALL')
const q = ref('')
const input = ref('')
const showAllOriginal = ref(false)
const shown = ref(new Set<number>())
const busy = ref(false)
const scroller = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)
const closeOpen = ref(false)
const listFailed = ref(false)

const selectedId = computed(() => (route.params.id ? Number(route.params.id) : null))
const current = computed(() => (store.current?.id === selectedId.value ? store.current : null))
// 표시용: 내가 맡은 진행 중 상담만 답장·종료 가능 (권한 판단은 backend)
const mine = computed(() => !!current.value && current.value.counselorId === auth.user?.id)
const canReply = computed(() => current.value?.status === 'ACTIVE' && mine.value)
const placeholder = computed(() => {
  if (!current.value) return ''
  if (current.value.status !== 'ACTIVE') return t('staff.console.acceptFirst')
  if (!mine.value) return t('staff.console.notMine')
  return sameLang.value ? t('staff.console.placeholderSame') : t('staff.console.placeholder', { lang: langName(current.value.customer.locale) })
})
const counts = computed(() => ({
  ALL: store.inbox.length,
  WAITING: store.inbox.filter((c) => c.status === 'WAITING').length,
  ACTIVE: store.inbox.filter((c) => c.status === 'ACTIVE').length,
  CLOSED: store.inbox.filter((c) => c.status === 'CLOSED').length,
}))
const visible = computed(() => {
  const text = q.value.trim().toLowerCase()
  return store.inbox
    .filter((c) => filter.value === 'ALL' || c.status === filter.value)
    .filter((c) => !text || c.customer.name.toLowerCase().includes(text) || c.summaryCard.procedure.toLowerCase().includes(text))
})
const groups = computed(() =>
  (['ACTIVE', 'WAITING', 'CLOSED'] as const)
    .map((s) => ({ status: s, items: visible.value.filter((c) => c.status === s) }))
    .filter((g) => g.items.length),
)
const waitMin = (c: Consultation) => Math.max(1, Math.round((now.value - new Date(c.createdAt).getTime()) / 60000))
const langName = (l: string) => t(`domain.langName.${l}`)
// D-43: 한국어 고객은 번역 없이 그대로 전달 → 번역 안내·원문 보기를 숨긴다
const sameLang = computed(() => current.value?.customer.locale === 'ko')
const untranslated = (m: ChatMessage) => m.translatedLang === m.originalLang
const hasTranslation = (m: ChatMessage) => m.translationStatus === 'DONE' && !!m.translatedText && !untranslated(m)
const flagged = computed(() => store.messages.filter((m) => m.senderRole === 'CUSTOMER' && m.flags.length))

function statusLine(m: ChatMessage) {
  if (m.translationStatus === 'PENDING') return t('chat.human.translating')
  if (m.translationStatus === 'FAILED') return t(m.id < 0 ? 'chat.human.sendFailed' : 'chat.human.failed')
  if (untranslated(m)) return ''
  return t('staff.console.sentIn', { lang: langName(current.value?.customer.locale ?? 'en') })
}
function toggle(id: number) {
  const s = new Set(shown.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  shown.value = s
}
function jumpTo(id: number) {
  document.getElementById(`msg-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

async function loadInbox() {
  listFailed.value = false
  try {
    await store.loadInbox()
  } catch {
    listFailed.value = true
  }
}
async function openSelected() {
  if (selectedId.value && store.current?.id !== selectedId.value) await store.open(selectedId.value).catch(() => showToast(t('staff.loadFailed'), 'error'))
  if (!selectedId.value) store.close()
}
/** 수락·종료 실패(다른 상담사가 먼저 수락 등) → 상담·문의함을 다시 불러와 화면을 서버 상태로 맞춘다 */
async function resync(id: number, e: unknown) {
  showToast(toApiError(e)?.message || t('common.error'), 'error')
  await store.open(id).catch(() => undefined)
  await loadInbox()
}
async function accept() {
  if (!current.value) return
  const id = current.value.id
  busy.value = true
  try {
    await store.accept(id)
    await loadInbox()
    await nextTick()
    inputEl.value?.focus()
  } catch (e) {
    await resync(id, e)
  } finally {
    busy.value = false
  }
}
async function finish() {
  if (!current.value) return
  const id = current.value.id
  busy.value = true
  try {
    await store.finish(id)
    await loadInbox()
    showToast(t('staff.console.closed'))
  } catch (e) {
    await resync(id, e)
  } finally {
    busy.value = false
    closeOpen.value = false
  }
}
async function submit() {
  const text = input.value.trim()
  if (!text || !canReply.value) return
  input.value = ''
  await store.send(text, 'COUNSELOR', 'ko')
}
function onKey(e: KeyboardEvent) {
  // keyCode 229: Safari 는 변환을 확정하는 Enter 에서 isComposing=false 로 들어온다 (ja·zh·ko 입력 중 전송 방지)
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) {
    e.preventDefault()
    void submit()
  }
}

onMounted(async () => {
  await loadInbox()
  await openSelected()
})
// 새 상담 요청·수락·종료 알림이 오면 문의함 갱신 (열어 둔 채팅은 그대로)
useNotificationRefresh(['CONSULTATION_REQUESTED', 'CONSULTATION_ACCEPTED', 'CONSULTATION_CLOSED'], loadInbox)
// 상담방을 바꾸면 쓰던 답장은 그 상담에 임시 저장하고 새 방 것을 꺼낸다 (다른 고객에게 잘못 보내지 않게)
const drafts = new Map<number, string>()
watch(selectedId, (id, prev) => {
  if (prev) drafts.set(prev, input.value)
  input.value = (id && drafts.get(id)) || ''
  shown.value = new Set()
  busy.value = false
  void openSelected()
})
watch(
  () => store.messages.length,
  async () => {
    await nextTick()
    scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
  },
)
onBeforeUnmount(() => store.close())
</script>

<template>
  <div class="console">
    <!-- 문의함 -->
    <section class="inbox">
      <header class="inbox__head">
        <h1 class="t-title-20">{{ t('staff.nav.inbox') }}</h1>
        <label class="search">
          <AppIcon name="search" :size="18" />
          <input v-model="q" class="t-body-14" :placeholder="t('staff.console.search')" :aria-label="t('staff.console.search')" />
        </label>
        <div class="chips">
          <AppChip v-for="s in ['ALL', 'WAITING', 'ACTIVE', 'CLOSED'] as const" :key="s" :selected="filter === s" @click="filter = s">
            {{ t(`staff.console.filters.${s}`) }}<template v-if="s !== 'CLOSED'"> {{ counts[s] }}</template>
          </AppChip>
        </div>
      </header>
      <div class="inbox__list">
        <EmptyState v-if="listFailed" icon="alert-triangle" tone="danger" :title="t('staff.loadFailed')">
          <AppButton variant="secondary" size="s" icon="refresh-cw" @click="loadInbox">{{ t('common.retry') }}</AppButton>
        </EmptyState>
        <EmptyState
          v-else-if="!visible.length"
          icon="message-circle"
          :title="filter === 'WAITING' ? t('staff.console.emptyWaiting') : t('staff.console.empty')"
          :description="filter === 'WAITING' ? t('staff.console.emptyWaitingBody') : ''"
        />
        <template v-for="g in groups" :key="g.status">
          <p class="group t-caption-12-sb">{{ t(`staff.console.groups.${g.status}`, { n: g.items.length }) }}</p>
          <RouterLink
            v-for="c in g.items"
            :key="c.id"
            :to="`/counselor/consultations/${c.id}`"
            class="item"
            :class="{ 'item--on': c.id === selectedId }"
          >
            <span class="avatar t-body-14-sb">{{ c.customer.name.slice(0, 1) }}</span>
            <span class="item__body">
              <span class="row">
                <span class="t-body-14-sb">{{ c.customer.name }}</span>
                <AppBadge tag>{{ t(`domain.lang.${c.customer.locale}`) }}</AppBadge>
                <span class="spacer" />
                <AppBadge v-if="c.status === 'WAITING'" tone="warning">{{ t('staff.console.waitMin', { n: waitMin(c) }) }}</AppBadge>
                <span v-else class="t-caption-12 muted">{{ fmtTime(c.createdAt) }}</span>
              </span>
              <!-- 잠시 숨김: 「대화에서 나온 질문」
              <span v-if="c.summaryCard.questions[0]" class="t-body-14 quote">“{{ c.summaryCard.questions[0] }}”</span>
              -->
              <span class="t-caption-12 muted">{{ c.summaryCard.procedure }} · {{ c.summaryCard.preferredDates }}</span>
            </span>
          </RouterLink>
        </template>
      </div>
      <p class="inbox__foot t-caption-12">{{ t('staff.console.consentOnly') }}</p>
    </section>

    <!-- 통역 채팅 -->
    <section class="chat">
      <EmptyState v-if="!current" icon="message-circle" :title="t('staff.console.pick')" :description="t('staff.console.pickBody')" />
      <template v-else>
        <header class="chat__head">
          <span class="avatar t-body-14-sb">{{ current.customer.name.slice(0, 1) }}</span>
          <div class="chat__who">
            <p class="row">
              <span class="t-body-16-sb">{{ current.customer.name }}</span>
              <AppBadge tag>{{ t(`domain.lang.${current.customer.locale}`) }}</AppBadge>
            </p>
            <p class="t-caption-12 muted">{{ t(sameLang ? 'staff.console.sameLanguage' : 'staff.console.autoTranslate', { lang: langName(current.customer.locale), time: fmtTime(current.createdAt) }) }}</p>
          </div>
          <label v-if="!sameLang" class="switch t-caption-13">
            {{ t('staff.console.showOriginal') }}
            <input v-model="showAllOriginal" type="checkbox" role="switch" />
            <span class="track" aria-hidden="true" />
          </label>
          <AppButton v-if="current.status === 'WAITING'" :loading="busy" @click="accept">{{ t('staff.console.accept') }}</AppButton>
          <AppButton v-else-if="current.status === 'ACTIVE' && mine" variant="outline" :disabled="busy" @click="closeOpen = true">{{ t('staff.console.close') }}</AppButton>
          <AppBadge v-else-if="current.status === 'ACTIVE'" tone="info">{{ t('staff.console.filters.ACTIVE') }}</AppBadge>
          <AppBadge v-else tone="neutral">{{ t('staff.console.filters.CLOSED') }}</AppBadge>
        </header>
        <AppBanner v-if="!store.connected" type="reconnecting">{{ t('chat.reconnecting') }}</AppBanner>
        <div ref="scroller" class="chat__messages">
          <template v-for="m in store.messages" :key="m.clientMsgId ?? m.id">
            <ChatBubble v-if="m.senderRole === 'SYSTEM'" sender="system" :text="m.translatedText ?? m.originalText" />
            <ChatBubble v-else-if="m.senderRole === 'COUNSELOR'" :id="`msg-${m.id}`" sender="me" :text="m.originalText" :time="fmtTime(m.createdAt)" :failed="m.translationStatus === 'FAILED'">
              <button v-if="m.translationStatus === 'FAILED'" type="button" class="status status--failed hit t-caption-12-sb" @click="store.retryTranslation(m)">
                <AppIcon name="alert-triangle" :size="14" />{{ statusLine(m) }}
              </button>
              <span v-else-if="statusLine(m)" class="status t-caption-11"><AppIcon name="languages" :size="14" />{{ statusLine(m) }}</span>
            </ChatBubble>
            <ChatBubble
              v-else
              :id="`msg-${m.id}`"
              sender="customer"
              :name="`${current.customer.name} · ${langName(m.originalLang)}`"
              :text="m.translationStatus === 'DONE' ? (m.translatedText ?? m.originalText) : m.originalText"
            >
              <p v-if="m.translationStatus === 'PENDING'" class="status t-caption-11">{{ t('chat.human.translating') }}</p>
              <!-- 번역 실패: 원문이 그대로 보이므로 실패를 알리고 다시 번역 -->
              <button v-else-if="m.translationStatus === 'FAILED'" type="button" class="status status--failed hit t-caption-12-sb" @click="store.retryTranslation(m)">
                <AppIcon name="alert-triangle" :size="14" />{{ t('staff.console.translateFailed') }}
              </button>
              <!-- 원문 보기는 번역이 끝난 메시지만 (번역 전·실패는 이미 원문이 보임) -->
              <p v-if="(showAllOriginal || shown.has(m.id)) && hasTranslation(m)" class="original t-caption-12">{{ t('staff.console.original') }} · {{ m.originalText }}</p>
              <div class="flags">
                <AppBadge v-if="m.flags.includes('MEDICAL_QUESTION')" tone="warning" icon="alert-triangle">{{ t('staff.console.flags.MEDICAL_QUESTION') }}</AppBadge>
                <AppBadge v-if="m.flags.includes('NUMBER_MISMATCH')" tone="warning" icon="alert-triangle">{{ t('staff.console.flags.NUMBER_MISMATCH') }}</AppBadge>
                <button v-if="!showAllOriginal && hasTranslation(m)" type="button" class="link hit t-caption-12-sb" @click="toggle(m.id)">
                  {{ shown.has(m.id) ? t('chat.human.hideOriginal') : t('staff.console.seeOriginal') }}
                </button>
              </div>
            </ChatBubble>
          </template>
        </div>
        <form class="chat__input" @submit.prevent="submit">
          <textarea
            ref="inputEl"
            v-model="input"
            rows="1"
            class="t-body-15"
            :disabled="!canReply"
            :placeholder="placeholder"
            :aria-label="placeholder"
            @keydown="onKey"
          />
          <button type="submit" class="send" :class="{ 'send--on': input.trim() && canReply }" :disabled="!input.trim() || !canReply" :aria-label="t('chat.send')">
            <AppIcon name="send" :size="20" />
          </button>
        </form>
        <p class="chat__hint t-caption-12">
          <span v-if="!sameLang"><AppIcon name="languages" :size="14" /> {{ t('staff.console.hint', { lang: langName(current.customer.locale) }) }}</span>
          <span>{{ t('staff.console.keys') }}</span>
        </p>
      </template>
    </section>

    <!-- 상담 정보 -->
    <aside v-if="current" class="info">
      <h2 class="t-title-18">{{ t('staff.console.info') }}</h2>
      <section class="card">
        <h3 class="t-body-16-sb"><AppIcon name="file-text" :size="18" class="brand" /> {{ t('staff.console.summary') }}</h3>
        <dl class="kv">
          <div><dt>{{ t('chat.summary.procedure') }}</dt><dd>{{ current.summaryCard.procedure }}</dd></div>
          <div><dt>{{ t('chat.summary.dates') }}</dt><dd>{{ current.summaryCard.preferredDates }}</dd></div>
          <div v-if="current.summaryCard.stayDays"><dt>{{ t('chat.summary.stay') }}</dt><dd>{{ t('chat.summary.days', { n: current.summaryCard.stayDays }) }}</dd></div>
          <div v-if="current.summaryCard.budget"><dt>{{ t('chat.summary.budget') }}</dt><dd>{{ current.summaryCard.budget }}</dd></div>
          <!-- 잠시 숨김: 「대화에서 나온 질문」
          <div v-if="current.summaryCard.questions.length"><dt>{{ t('staff.console.questions') }}</dt><dd>{{ current.summaryCard.questions.join(' · ') }}</dd></div>
          -->
          <div><dt>{{ t('staff.console.consent') }}</dt><dd>{{ t('staff.console.consentAt', { time: fmtTime(current.createdAt) }) }}</dd></div>
        </dl>
        <p class="t-caption-12 muted">{{ t('staff.console.aiSummarized') }}</p>
      </section>
      <section v-if="flagged.length" class="card">
        <h3 class="t-body-16-sb"><AppIcon name="alert-triangle" :size="18" class="warn" /> {{ t('staff.console.needsCheck') }} <AppBadge tone="warning">{{ flagged.length }}</AppBadge></h3>
        <button v-for="m in flagged" :key="m.id" type="button" class="flag-link t-caption-13" @click="jumpTo(m.id)">
          <span>{{ m.flags.map((f) => t(`staff.console.flags.${f}`)).join(' · ') }}</span>
          <span>{{ t('staff.console.toMessage', { time: fmtTime(m.createdAt) }) }} →</span>
        </button>
      </section>
      <section class="card">
        <h3 class="t-body-16-sb row">
          <AppIcon name="headphones" :size="18" class="brand" /> {{ t('staff.console.status') }}
          <span class="spacer" />
          <AppBadge :tone="current.status === 'ACTIVE' ? 'info' : current.status === 'WAITING' ? 'warning' : 'neutral'">{{ t(`staff.console.filters.${current.status}`) }}</AppBadge>
        </h3>
        <dl class="kv">
          <div><dt>{{ t('staff.console.assignee') }}</dt><dd>{{ current.counselorId ? (current.counselorId === auth.user?.id ? auth.user?.name : `#${current.counselorId}`) : '—' }}</dd></div>
          <div><dt>{{ t('staff.console.started') }}</dt><dd>{{ fmtTime(current.createdAt) }}</dd></div>
          <div><dt>{{ t('staff.console.customerLang') }}</dt><dd>{{ langName(current.customer.locale) }} ({{ current.customer.locale }})</dd></div>
          <div><dt>{{ t('booking.hospital') }}</dt><dd>{{ current.hospital.name }}</dd></div>
        </dl>
        <p class="t-caption-12 muted">{{ t('staff.console.closeNote') }}</p>
      </section>
      <p class="notice t-caption-13"><AppIcon name="info" :size="16" />{{ t(sameLang ? 'staff.console.noticeSame' : 'staff.console.notice') }}</p>
    </aside>
    <AppDialog :open="closeOpen" :title="t('staff.console.closeConfirm')" :body="t('staff.console.closeNote')">
      <template #actions>
        <AppButton variant="secondary" :disabled="busy" @click="closeOpen = false">{{ t('common.cancel') }}</AppButton>
        <AppButton variant="danger" :loading="busy" @click="finish">{{ t('staff.console.close') }}</AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.console { display: flex; height: 100%; background: var(--bg-default); }
.inbox { display: flex; flex: none; flex-direction: column; width: 340px; border-right: 1px solid var(--border-default); }
.inbox__head { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-24) var(--space-16) var(--space-12); }
.search { display: flex; align-items: center; gap: var(--space-8); height: 40px; padding: 0 var(--space-12); border-radius: var(--radius-md); background: var(--bg-muted); color: var(--icon-subtle); }
.search input { flex: 1; min-width: 0; border: 0; background: none; outline: none; color: var(--text-primary); }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-6); }
.inbox__list { flex: 1; overflow-y: auto; }
.group { padding: var(--space-12) var(--space-16) var(--space-4); color: var(--text-secondary); }
.item { position: relative; display: flex; gap: var(--space-12); padding: var(--space-16); border-bottom: 1px solid var(--border-default); }
.item:hover { background: var(--bg-subtle); }
.item--on { background: var(--brand-subtle); }
.item--on::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--brand-primary); }
.avatar { display: grid; place-items: center; flex: none; width: 36px; height: 36px; border-radius: 50%; background: var(--brand-subtle); color: var(--brand-text); }
.item__body { display: flex; flex: 1; flex-direction: column; gap: var(--space-4); min-width: 0; }
.row { display: flex; align-items: center; gap: var(--space-6); }
.spacer { flex: 1; }
.quote { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.muted { color: var(--text-tertiary); }
.brand { color: var(--brand-primary); }
.warn { color: var(--status-warning); }
.inbox__foot { padding: var(--space-12) var(--space-16); border-top: 1px solid var(--border-default); color: var(--text-tertiary); }

.chat { display: flex; flex: 1; flex-direction: column; min-width: 0; border-right: 1px solid var(--border-default); }
.chat > .empty { margin: auto; }
.chat__head { display: flex; align-items: center; gap: var(--space-12); padding: var(--space-12) var(--space-24); border-bottom: 1px solid var(--border-default); }
.chat__who { flex: 1; min-width: 0; }
.switch { position: relative; display: flex; align-items: center; gap: var(--space-8); color: var(--text-secondary); cursor: pointer; }
.switch input { position: absolute; opacity: 0; }
.track { position: relative; width: 36px; height: 20px; border-radius: 10px; background: var(--border-strong); transition: background 0.15s; }
.track::after { content: ''; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: var(--bg-default); transition: transform 0.15s; }
.switch input:checked + .track { background: var(--brand-primary); }
.switch input:checked + .track::after { transform: translateX(16px); }
.switch input:focus-visible + .track { outline: 2px solid var(--border-focus); outline-offset: 2px; }
.chat__messages { display: flex; flex: 1; flex-direction: column; gap: var(--space-16); padding: var(--space-24); overflow-y: auto; }
.status { display: inline-flex; align-items: center; gap: var(--space-4); padding: 0; border: 0; background: none; color: var(--text-tertiary); }
.status--failed { color: var(--status-danger); }
.original { max-width: 320px; padding: var(--space-8) var(--space-12); border-radius: var(--radius-sm); background: var(--bg-muted); color: var(--text-secondary); }
.flags { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-8); }
.link { padding: 0; border: 0; background: none; color: var(--text-brand); }
.chat__input { display: flex; align-items: flex-end; gap: var(--space-8); padding: var(--space-12) var(--space-24) var(--space-4); border-top: 1px solid var(--border-default); }
.chat__input textarea { flex: 1; min-height: 44px; max-height: 140px; padding: 11px var(--space-16); border: 0; border-radius: 22px; background: var(--bg-muted); resize: none; outline: none; field-sizing: content; }
.chat__input textarea:disabled { opacity: 0.6; }
.send { display: grid; place-items: center; width: 44px; height: 44px; border: 0; border-radius: 50%; background: var(--bg-muted); color: var(--icon-subtle); }
.send--on { background: var(--brand-primary); color: var(--text-inverse); }
.chat__hint { display: flex; justify-content: space-between; padding: 0 var(--space-24) var(--space-12); color: var(--text-tertiary); }
.chat__hint span { display: inline-flex; align-items: center; gap: var(--space-4); }

.info { display: flex; flex: none; flex-direction: column; gap: var(--space-16); width: 360px; padding: var(--space-24) var(--space-20); overflow-y: auto; background: var(--bg-subtle); }
.card { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.card h3 { display: flex; align-items: center; gap: var(--space-6); }
.kv { display: flex; flex-direction: column; gap: var(--space-8); margin: 0; }
.kv div { display: grid; grid-template-columns: 76px 1fr; font: 600 14px/20px var(--font-sans); }
.kv dt { font-weight: 400; color: var(--text-tertiary); }
.kv dd { margin: 0; }
.flag-link { display: flex; justify-content: space-between; gap: var(--space-8); padding: var(--space-12); border: 0; border-radius: var(--radius-md); background: var(--status-warning-bg); color: var(--status-warning); text-align: left; }
.notice { display: flex; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); background: var(--status-info-bg); color: var(--status-info); }
</style>
