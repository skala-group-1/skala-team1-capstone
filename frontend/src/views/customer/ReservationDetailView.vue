<script setup lang="ts">
// 「화면 목록」 C9 예약 상세 (/reservations/:id)
// - 반려 → 대안 시간 선택 (Figma 1:4618, POST accept-alternative)
// - 확정 → 방문 안내 (1:4684, 지도 링크 D-34)
// - 만료 → 다시 요청하기 (Edge ⑥ 1:7576, D-37: 같은 슬롯이 비었는지 확인 → C8 확인 시트에 같은 조건)
// - 승인 대기 → 홀드 타이머 · 요청 취소
// - 확정 → 리뷰 쓰기 (예약당 1회, reviewable/reviewId 는 backend 가 계산)
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { catalogApi, reservationApi, toApiError } from '@/api'
import { useReservationStore } from '@/stores/reservation'
import { useNow } from '@/composables/useNow'
import { useNotificationRefresh } from '@/composables/useNotificationRefresh'
import { showToast } from '@/composables/useToast'
import { fmtDate, fmtDateTime, fmtKrw, fmtTime, mapUrl, remaining, seoulDate } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppBadge, { RESERVATION_TONE } from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ReviewSheet from '@/components/booking/ReviewSheet.vue'
import AftercareCard from '@/components/aftercare/AftercareCard.vue'
import type { HospitalDetail, Reservation, Review } from '@/types/contract'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const store = useReservationStore()
const now = useNow()

const r = ref<Reservation | null>(null)
const hospital = ref<HospitalDetail | null>(null)
const failed = ref(false)
const altId = ref<number | null>(null)
const busy = ref(false)
const confirmCancel = ref(false)
const reviewOpen = ref(false)
/** 만료: 같은 슬롯이 아직 비었는지 (GET slots 그날) */
const slotStillOpen = ref<boolean | null>(null)

const number = computed(() => (r.value ? `R-${String(r.value.id).padStart(4, '0')}` : ''))
const priceText = computed(() => {
  const o = r.value?.priceOption
  if (!o) return t('common.needsCheck')
  return `${fmtKrw(o.priceKrw)} · ${o.product}${o.dose ? ` ${o.dose}` : ''} · ${o.vatIncluded ? t('compare.vatIn') : t('compare.vatEx')}`
})
const todayHours = computed(() => {
  if (!r.value || !hospital.value) return null
  const key = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Seoul', weekday: 'short' }).format(new Date(r.value.slot.startAt)).toLowerCase().slice(0, 3)
  const h = hospital.value.openHours[key as 'mon']
  return h ? `${h.open} – ${h.close}` : null
})
const expiredAt = computed(() => (r.value ? new Date(new Date(r.value.createdAt).getTime() + 30 * 60_000).toISOString() : ''))

async function load() {
  failed.value = false
  try {
    r.value = await reservationApi.get(Number(route.params.id))
    altId.value = r.value.alternatives[0]?.id ?? null
    hospital.value = await catalogApi.hospital(r.value.hospital.id).catch(() => null)
    if (r.value.status === 'EXPIRED') {
      const day = seoulDate(r.value.slot.startAt)
      const open = await catalogApi.slots(r.value.hospital.id, { procedure: r.value.procedure.code, dateFrom: day, dateTo: day }).catch(() => [])
      slotStillOpen.value = open.some((s) => s.id === r.value!.slot.id)
    }
  } catch {
    failed.value = true
  }
}
async function acceptAlt() {
  if (!r.value || !altId.value) return
  busy.value = true
  store.startBooking()
  try {
    const created = await store.acceptAlternative(r.value.id, altId.value)
    showToast(t('reservations.altRequested'))
    await router.replace(`/reservations/${created.id}`)
    await load()
  } catch (e) {
    showToast(toApiError(e)?.code === 'SLOT_UNAVAILABLE' ? t('reservations.altGone') : t('common.error'), 'error')
    await load()
  } finally {
    busy.value = false
  }
}
async function cancel() {
  if (!r.value) return
  confirmCancel.value = false
  busy.value = true
  try {
    await store.cancel(r.value.id)
    r.value = { ...r.value, status: 'CANCELLED' }
    showToast(t('reservations.cancelled'))
  } catch (e) {
    showToast(toApiError(e)?.message || t('common.error'), 'error')
    await load()
  } finally {
    busy.value = false
  }
}
/** D-37: 비었으면 C8 확인 단계(같은 병원·시간·시술·옵션·메모), 아니면 날짜·시간부터 */
function requestAgain() {
  if (!r.value) return
  const x = r.value
  const query: Record<string, string> = { procedure: x.procedure.code, date: seoulDate(x.slot.startAt) }
  if (x.priceOption) query.option = String(x.priceOption.id)
  if (x.note) query.note = x.note
  if (slotStillOpen.value) query.slot = String(x.slot.id)
  void router.push({ path: `/hospitals/${x.hospital.id}/book`, query })
}
function onReviewed(review: Review) {
  reviewOpen.value = false
  if (r.value) r.value = { ...r.value, reviewable: false, reviewId: review.id }
  showToast(t('reservations.review.done'))
}
function openReviews() {
  if (r.value) void router.push({ path: `/hospitals/${r.value.hospital.id}`, query: { tab: 'reviews' } })
}
function openHospitalChat() {
  if (r.value) void router.push({ path: '/chat', query: { hospitalId: r.value.hospital.id } })
}
onMounted(load)
// 보고 있는 예약이 승인·반려·만료되면 다시 불러옴
useNotificationRefresh(['RESERVATION_CONFIRMED', 'RESERVATION_REJECTED', 'RESERVATION_EXPIRED', 'RESERVATION_CANCELLED'], (n) => {
  if (n.payload.reservationId === Number(route.params.id)) return load()
})
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('reservations.detailTitle')" back="/reservations" />
    <EmptyState v-if="failed" icon="alert-triangle" tone="danger" :title="t('reservations.loadFailed')">
      <AppButton variant="secondary" icon="refresh-cw" @click="load">{{ t('common.retry') }}</AppButton>
    </EmptyState>

    <div v-else-if="!r" class="skeleton-list" role="status" :aria-label="t('common.loading')" aria-busy="true">
      <span class="bone" style="height: 160px" /><span class="bone" style="height: 120px" />
    </div>
    <template v-else>
      <div class="body">
        <!-- 요약 카드 -->
        <section class="card">
          <div class="row-between">
            <AppBadge :tone="RESERVATION_TONE[r.status]" dot>{{ t(`domain.status.${r.status}`) }}</AppBadge>
            <AppBadge v-if="r.status === 'PENDING' && remaining(r.holdExpiresAt, now)" tone="warning" icon="clock">
              {{ t('domain.holdLeft', { time: remaining(r.holdExpiresAt, now) }) }}
            </AppBadge>
          </div>
          <template v-if="r.status === 'CONFIRMED'">
            <p class="t-title-22">{{ fmtDateTime(r.slot.startAt) }}</p>
            <p class="t-body-14 secondary">{{ r.hospital.name }} · {{ r.procedure.name }}</p>
          </template>
          <template v-else>
            <p class="t-title-18">{{ r.hospital.name }}</p>
            <p v-if="r.status === 'REJECTED'" class="t-caption-13 secondary">{{ r.procedure.name }}<template v-if="r.priceOption"> · {{ r.priceOption.product }} · {{ fmtKrw(r.priceOption.priceKrw) }}</template></p>
          </template>
          <p v-if="r.status === 'REJECTED'" class="t-caption-13 struck">
            <AppIcon name="calendar" :size="14" /><s>{{ t('reservations.requestedTime', { at: fmtDateTime(r.slot.startAt) }) }}</s>
          </p>
          <p class="t-caption-12 muted">{{ t('booking.kstNote') }}</p>
          <dl v-if="r.status !== 'REJECTED'" class="kv">
            <div v-if="r.status !== 'CONFIRMED'"><dt>{{ t('booking.procedure') }}</dt><dd>{{ r.procedure.name }}</dd></div>
            <div v-if="r.status !== 'CONFIRMED'"><dt>{{ t('reservations.wishTime') }}</dt><dd>{{ fmtDateTime(r.slot.startAt) }}</dd></div>
            <div><dt>{{ t('booking.doctor') }}</dt><dd>{{ r.slot.doctorName }}</dd></div>
            <div><dt>{{ t('booking.price') }}</dt><dd>{{ priceText }}</dd></div>
            <div><dt>{{ t('reservations.number') }}</dt><dd>{{ number }}</dd></div>
            <div v-if="r.note"><dt>{{ t('reservations.note') }}</dt><dd>{{ r.note }}</dd></div>
          </dl>
          <div v-if="r.status === 'REJECTED' && r.rejectReason" class="reason">
            <p class="t-caption-12-sb">{{ t('reservations.rejectReason') }}</p>
            <p class="t-body-14">{{ r.rejectReason }}</p>
          </div>
        </section>

        <!-- 반려 → 대안 시간 -->
        <section v-if="r.status === 'REJECTED'" class="card">
          <h2 class="t-body-16-sb">{{ t('reservations.alternatives') }}</h2>
          <p class="t-caption-12 muted">{{ t('reservations.altNote') }}</p>
          <label v-for="s in r.alternatives" :key="s.id" class="radio" :class="{ 'radio--on': altId === s.id }">
            <input v-model="altId" type="radio" name="alt" :value="s.id" />
            <span class="dot" aria-hidden="true" />
            <span class="radio__text">
              <span class="t-body-14-sb">{{ fmtDateTime(s.startAt) }}</span>
              <span class="t-caption-12 muted">{{ s.doctorName }}</span>
            </span>
          </label>
          <p v-if="!r.alternatives.length" class="t-body-14 muted">{{ t('reservations.noAlternatives') }}</p>
        </section>

        <!-- 확정 → 방문 안내 -->
        <section v-if="r.status === 'CONFIRMED'" class="card">
          <h2 class="t-body-16-sb">{{ t('reservations.visit.title') }}</h2>
          <p v-if="hospital?.address" class="guide"><AppIcon name="map-pin" :size="18" /><span class="t-body-14-sb">{{ hospital.address }}</span></p>
          <p class="guide">
            <AppIcon name="clock" :size="18" />
            <span>
              <span class="t-body-14-sb">{{ t('reservations.visit.arrive') }}</span>
              <span v-if="todayHours" class="t-caption-12 muted">{{ t('reservations.visit.hours', { day: fmtDate(r.slot.startAt), hours: todayHours }) }}</span>
            </span>
          </p>
          <p v-if="hospital?.hasInterpreter" class="guide">
            <AppIcon name="languages" :size="18" />
            <span>
              <span class="t-body-14-sb">{{ t('reservations.visit.interpreter') }}</span>
              <span class="t-caption-12 muted">{{ t('reservations.visit.interpreterNote') }}</span>
            </span>
          </p>
          <p class="guide">
            <AppIcon name="file-text" :size="18" />
            <span>
              <span class="t-body-14-sb">{{ t('reservations.visit.passport') }}</span>
              <span class="t-caption-12 muted">{{ t('reservations.visit.passportNote') }}</span>
            </span>
          </p>
          <div class="btns">
            <a v-if="hospital?.address" :href="mapUrl(hospital.address)" target="_blank" rel="noopener" class="btn-link t-caption-13">{{ t('hospital.openMap') }}</a>
            <button type="button" class="btn-link t-caption-13" @click="openHospitalChat">{{ t('reservations.visit.chat') }}</button>
          </div>
        </section>
        <p v-if="r.status === 'CONFIRMED'" class="t-caption-12 muted">{{ t('reservations.visit.policy') }}</p>
        <AftercareCard v-if="r.status === 'CONFIRMED' || r.status === 'PENDING'" :reservation-id="r.id" />

        <!-- 확정 → 리뷰 쓰기 / 작성 완료 (취소하면 리뷰는 병원 목록에서 숨겨지므로 카드도 안 보임) -->
        <section v-if="r.reviewable" class="card">
          <h2 class="t-body-16-sb">{{ t('reservations.review.title') }}</h2>
          <p class="t-caption-13 secondary">{{ t('reservations.review.body') }}</p>
          <AppButton variant="outline" icon="star" block @click="reviewOpen = true">{{ t('reservations.review.write') }}</AppButton>
        </section>
        <section v-else-if="r.status === 'CONFIRMED' && r.reviewId" class="card reviewed">
          <p class="row-between t-body-14-sb"><AppIcon name="check" :size="18" />{{ t('reservations.review.written') }}</p>
          <button type="button" class="btn-link t-caption-13" @click="openReviews">{{ t('reservations.review.see') }}</button>
        </section>

        <!-- 만료 → 진행 기록 + 다시 요청 -->
        <template v-if="r.status === 'EXPIRED'">
          <section class="card">
            <h2 class="t-body-14-sb">{{ t('reservations.timeline.title') }}</h2>
            <ol class="timeline">
              <li><span class="t-body-14">{{ t('reservations.timeline.requested') }}</span><span class="t-caption-12 muted">{{ fmtDate(r.createdAt) }} {{ fmtTime(r.createdAt) }}</span></li>
              <li class="gray"><span class="t-body-14">{{ t('reservations.timeline.noReply') }}</span><span class="t-caption-12 muted">{{ fmtTime(r.createdAt) }} – {{ fmtTime(expiredAt) }}</span></li>
              <li class="dark"><span class="t-body-14">{{ t('reservations.timeline.expired') }}</span><span class="t-caption-12 muted">{{ fmtDate(expiredAt) }} {{ fmtTime(expiredAt) }}</span></li>
            </ol>
          </section>
          <p class="info t-caption-13"><AppIcon name="info" :size="16" />{{ t('reservations.expiredBody') }}</p>
          <p v-if="slotStillOpen" class="open t-caption-13"><AppIcon name="check" :size="16" />{{ t('reservations.stillOpen', { at: fmtDateTime(r.slot.startAt) }) }}</p>
          <p v-else-if="slotStillOpen === false" class="info t-caption-13"><AppIcon name="info" :size="16" />{{ t('reservations.slotTaken') }}</p>
        </template>
      </div>

      <footer v-if="r.status === 'REJECTED'" class="bottom">
        <AppButton variant="outline" size="l" block @click="router.push('/explore')">{{ t('reservations.otherHospital') }}</AppButton>
        <AppButton size="l" block :disabled="!altId" :loading="busy" @click="acceptAlt">{{ t('booking.conflict.request') }}</AppButton>
      </footer>
      <footer v-else-if="r.status === 'EXPIRED'" class="bottom">
        <AppButton variant="outline" size="l" block @click="router.push('/explore')">{{ t('reservations.otherHospital') }}</AppButton>
        <AppButton size="l" block @click="requestAgain">{{ slotStillOpen ? t('reservations.requestAgain') : t('reservations.pickOtherTime') }}</AppButton>
      </footer>
      <footer v-else-if="r.status === 'CONFIRMED' || r.status === 'PENDING'" class="bottom">
        <AppButton variant="danger" size="l" block :loading="busy" @click="confirmCancel = true">
          {{ r.status === 'PENDING' ? t('chat.requested.cancel') : t('reservations.cancel') }}
        </AppButton>
      </footer>
    </template>

    <ReviewSheet v-if="r" :open="reviewOpen" :reservation="r" @close="reviewOpen = false" @done="onReviewed" />
    <AppDialog :open="confirmCancel" @close="confirmCancel = false" :title="t('reservations.cancelTitle')" :body="t('reservations.cancelBody')">
      <template #actions>
        <AppButton variant="secondary" @click="confirmCancel = false">{{ t('reservations.keep') }}</AppButton>
        <AppButton variant="danger" @click="cancel">{{ r?.status === 'PENDING' ? t('chat.requested.cancel') : t('reservations.cancel') }}</AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100dvh; background: var(--bg-subtle); }
.body { display: flex; flex: 1; flex-direction: column; gap: var(--space-12); padding: var(--space-16) var(--space-16) 100px; }
.card { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.row-between { display: flex; align-items: center; gap: var(--space-8); }
.secondary { color: var(--text-secondary); }
.muted { color: var(--text-tertiary); }
.struck { display: flex; align-items: center; gap: var(--space-6); color: var(--text-tertiary); }
.kv { display: flex; flex-direction: column; gap: var(--space-8); margin: 0; }
.kv div { display: grid; grid-template-columns: 72px 1fr; font: 600 14px/20px var(--font-sans); }
.kv dt { font-weight: 500; color: var(--text-tertiary); }
.kv dd { margin: 0; }
.reason { display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-12); border-radius: var(--radius-sm); background: var(--status-danger-bg); color: var(--status-danger); }
.reason .t-body-14 { color: var(--text-primary); }
.radio { position: relative; display: flex; align-items: center; gap: var(--space-12); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-md); cursor: pointer; }
.radio input { position: absolute; opacity: 0; }
.radio--on { border: 1.5px solid var(--brand-primary); background: var(--brand-subtle); }
.radio__text { display: flex; flex-direction: column; gap: var(--space-2); }
.dot { flex: none; width: 20px; height: 20px; border: 1.5px solid var(--border-strong); border-radius: 50%; background: var(--bg-default); }
.radio--on .dot { border: 6px solid var(--brand-primary); }
.guide { display: flex; gap: var(--space-8); color: var(--icon-default); }
.guide > span { display: flex; flex-direction: column; color: var(--text-primary); }
.btns { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-8); }
.reviewed .row-between { color: var(--status-success); }
.btn-link { display: grid; place-items: center; height: 36px; border: 1px solid var(--border-strong); border-radius: var(--radius-sm); background: var(--bg-default); color: var(--text-primary); }
.timeline { display: flex; flex-direction: column; gap: var(--space-12); margin: 0; padding: 0 0 0 var(--space-16); list-style: none; }
.timeline li { position: relative; display: flex; flex-direction: column; }
.timeline li::before { content: ''; position: absolute; left: -16px; top: 6px; width: 8px; height: 8px; border-radius: 50%; background: var(--brand-primary); }
.timeline li.gray::before { background: var(--border-strong); }
.timeline li.dark::before { background: var(--text-tertiary); }
.info, .open { display: flex; gap: var(--space-8); padding: var(--space-12); border-radius: var(--radius-md); }
.info { background: var(--bg-muted); color: var(--text-secondary); }
.open { background: var(--status-success-bg); color: var(--status-success); }
.bottom {
  position: fixed;
  bottom: 0;
  left: 50%;
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
