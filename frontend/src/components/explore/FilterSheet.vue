<script setup lang="ts">
// C5-1 필터 바텀시트 (Figma 1:6203): 시술 · 지역(다중) · 최대 가격 · 희망 날짜 · 상담 언어 → "N곳 보기"
// 가격은 검색 API 에 priceMax 만 있어서 상한 하나만 둔다 (13-2). 하단 숫자는 같은 조건 search(size=1).total
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BottomSheet from '../ui/BottomSheet.vue'
import AppChip from '../ui/AppChip.vue'
import AppButton from '../ui/AppButton.vue'
import AppIcon from '../ui/AppIcon.vue'
import { catalogApi } from '@/api'
import { fmtKrw, seoulDate } from '@/utils/format'
import { AREA_CODES, type AreaCode, type HospitalSearchQuery, type Locale, type Procedure } from '@/types/contract'

const props = defineProps<{ open: boolean; query: HospitalSearchQuery; procedures: Procedure[] }>()
const today = seoulDate()
const emit = defineEmits<{ close: []; apply: [q: Partial<HospitalSearchQuery>] }>()
const { t } = useI18n()

const PRICE_STEP = 100_000
const PRICE_MAX = 5_000_000
const draft = reactive<Partial<HospitalSearchQuery>>({})
const count = ref<number | null>(null)

watch(
  () => props.open,
  (open) => {
    if (!open) return
    Object.assign(draft, {
      procedure: props.query.procedure,
      areas: [...(props.query.areas ?? [])],
      priceMax: props.query.priceMax,
      dateFrom: props.query.dateFrom,
      dateTo: props.query.dateTo,
      language: props.query.language,
    })
  },
)
let timer: ReturnType<typeof setTimeout> | undefined
watch(
  draft,
  () => {
    clearTimeout(timer)
    timer = setTimeout(async () => {
      count.value = await catalogApi
        .searchHospitals({ ...props.query, ...draft, page: 0, size: 1 })
        .then((p) => p.total)
        .catch(() => null)
    }, 250)
  },
  { deep: true },
)

function toggleArea(a: AreaCode) {
  const list = draft.areas ?? []
  draft.areas = list.includes(a) ? list.filter((x) => x !== a) : [...list, a]
}
function reset() {
  Object.assign(draft, { areas: [], priceMax: undefined, dateFrom: undefined, dateTo: undefined, language: undefined })
}
const languages: Locale[] = ['en', 'zh', 'ja']
</script>

<template>
  <BottomSheet :open="open" :title="t('explore.filter.title')" @close="emit('close')">
    <section class="group">
      <h3 class="t-body-14-sb">{{ t('explore.filter.procedure') }}</h3>
      <div class="chips">
        <AppChip
          v-for="p in procedures"
          :key="p.code"
          :selected="draft.procedure === p.code"
          @click="draft.procedure = draft.procedure === p.code ? undefined : p.code"
        >
          {{ p.name }}
        </AppChip>
      </div>
    </section>
    <section class="group">
      <h3 class="t-body-14-sb">{{ t('explore.filter.area') }} <span class="t-caption-12 muted">{{ t('explore.filter.multi') }}</span></h3>
      <div class="chips">
        <AppChip v-for="a in AREA_CODES" :key="a" :selected="draft.areas?.includes(a)" @click="toggleArea(a)">
          {{ t(`domain.area.${a}`) }}
        </AppChip>
      </div>
    </section>
    <section class="group">
      <h3 class="t-body-14-sb">{{ t('explore.filter.price') }} <span class="t-caption-12 muted">{{ t('explore.filter.priceUnit') }}</span></h3>
      <p class="t-body-16-sb">{{ draft.priceMax ? t('explore.filter.upTo', { price: fmtKrw(draft.priceMax) }) : t('explore.filter.any') }}</p>
      <input
        class="range"
        type="range"
        :min="PRICE_STEP"
        :max="PRICE_MAX"
        :step="PRICE_STEP"
        :value="draft.priceMax ?? PRICE_MAX"
        :aria-label="t('explore.filter.price')"
        @input="(e) => (draft.priceMax = Number((e.target as HTMLInputElement).value) >= PRICE_MAX ? undefined : Number((e.target as HTMLInputElement).value))"
      />
    </section>
    <section class="group">
      <h3 class="t-body-14-sb">{{ t('explore.filter.dates') }}</h3>
      <div class="dates">
        <label class="date">
          <AppIcon name="calendar" :size="18" />
          <input v-model="draft.dateFrom" type="date" :min="today" :aria-label="t('explore.filter.dateFrom')" />
        </label>
        <label class="date">
          <AppIcon name="calendar" :size="18" />
          <input v-model="draft.dateTo" type="date" :min="draft.dateFrom || today" :aria-label="t('explore.filter.dateTo')" />
        </label>
      </div>
    </section>
    <section class="group">
      <h3 class="t-body-14-sb">{{ t('explore.filter.language') }}</h3>
      <div class="chips">
        <AppChip v-for="l in languages" :key="l" :selected="draft.language === l" @click="draft.language = draft.language === l ? undefined : l">
          {{ t(`domain.lang.${l}`) }}
        </AppChip>
      </div>
    </section>
    <template #footer>
      <AppButton variant="ghost" size="l" @click="reset">{{ t('explore.filter.reset') }}</AppButton>
      <AppButton size="l" block :disabled="count === 0" @click="emit('apply', { ...draft })">
        {{ count == null ? t('explore.filter.apply') : t('explore.filter.showN', { n: count }) }}
      </AppButton>
    </template>
  </BottomSheet>
</template>

<style scoped>
.group { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-12) 0; }
.muted { color: var(--text-tertiary); font-weight: 400; }
.chips { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.range { width: 100%; accent-color: var(--brand-primary); }
.dates { display: flex; gap: var(--space-8); }
.date { display: flex; flex: 1; align-items: center; gap: var(--space-8); height: 48px; padding: 0 var(--space-12); border: 1px solid var(--border-default); border-radius: var(--radius-md); color: var(--icon-default); }
.date input { flex: 1; min-width: 0; border: 0; background: none; outline: none; color: var(--text-primary); }
</style>
