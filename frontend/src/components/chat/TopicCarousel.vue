<script setup lang="ts">
// Figma 02 C4-T Topic Card × 3 (가로 캐러셀). 주제 묶음 1개 = 카드 1장, Topic Option 3개. 누르면 그 주제로 대화 시작
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon, { type IconName } from '../ui/AppIcon.vue'
import type { ConsultTopic } from '@/types/contract'

const emit = defineEmits<{ pick: [topic: ConsultTopic] }>()
const { t } = useI18n()

const GROUPS: { key: string; icon: IconName; topics: ConsultTopic[] }[] = [
  { key: 'skin', icon: 'sparkles', topics: ['SKIN_CONCERN', 'PROCEDURE_INFO', 'RECOVERY'] },
  { key: 'hospital', icon: 'hospital', topics: ['HOSPITAL_SEARCH', 'HOSPITAL_COMPARE', 'COUNSELOR_CHAT'] },
  { key: 'booking', icon: 'calendar', topics: ['BOOK', 'MY_RESERVATIONS', 'CANCEL_RESERVATION'] },
]
const NEW: ConsultTopic[] = ['SKIN_CONCERN', 'HOSPITAL_SEARCH']

const track = ref<HTMLElement | null>(null)
const atEnd = ref(false)
function onScroll() {
  const el = track.value
  if (el) atEnd.value = el.scrollLeft + el.clientWidth >= el.scrollWidth - 4
}
function next() {
  const card = track.value?.children[0] as HTMLElement | undefined
  track.value?.scrollBy({ left: (card?.offsetWidth ?? 264) + 8, behavior: 'smooth' })
}
</script>

<template>
  <div class="topics">
    <div ref="track" class="topics__track" role="list" :aria-label="t('chat.topic.pick')" @scroll.passive="onScroll">
      <article v-for="g in GROUPS" :key="g.key" class="card" role="listitem">
        <header class="card__head">
          <div class="card__copy">
            <p class="t-caption-12 secondary">{{ t(`chat.topic.groups.${g.key}.eyebrow`) }}</p>
            <h3 class="card__title t-body-16-sb">{{ t(`chat.topic.groups.${g.key}.title`) }}</h3>
          </div>
          <span class="card__icon"><AppIcon :name="g.icon" /></span>
        </header>
        <div class="card__body">
          <p class="t-body-14 secondary">{{ t('chat.topic.pick') }}</p>
          <button v-for="topic in g.topics" :key="topic" type="button" class="option t-body-14" @click="emit('pick', topic)">
            {{ t(`chat.topic.items.${topic}`) }}
            <span v-if="NEW.includes(topic)" class="new t-caption-11">{{ t('chat.topic.new') }}</span>
          </button>
        </div>
      </article>
    </div>
    <button v-if="!atEnd" type="button" class="topics__next" :aria-label="t('chat.topic.next')" @click="next">
      <AppIcon name="chevron-right" :size="20" />
    </button>
  </div>
</template>

<style scoped>
.topics { position: relative; margin-right: -16px; }
.topics__track {
  display: flex;
  gap: var(--space-8);
  padding: 0 var(--space-16) 0 40px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scroll-padding-left: 40px;
  scrollbar-width: none;
}
.topics__track::-webkit-scrollbar { display: none; }
.topics__next {
  position: absolute;
  top: 128px;
  right: 12px;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--border-default);
  border-radius: 22px;
  background: var(--surface-card);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  color: var(--icon-default);
}

.card {
  display: flex;
  flex: none;
  flex-direction: column;
  width: 264px;
  overflow: hidden;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
  scroll-snap-align: start;
}
.card__head { display: flex; align-items: center; gap: var(--space-8); padding: 18px var(--space-16); background: var(--brand-subtle); }
.card__copy { display: flex; flex: 1; flex-direction: column; gap: var(--space-2); min-width: 0; }
.card__title { white-space: pre-line; }
.card__icon { display: grid; place-items: center; flex: none; width: 48px; height: 48px; border-radius: 50%; background: var(--surface-card); color: var(--icon-default); }
.card__body { display: flex; flex-direction: column; gap: var(--space-8); padding: 14px var(--space-16) var(--space-16); }
.secondary { color: var(--text-secondary); }

.option {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-6);
  height: 44px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--text-primary);
}
.option:active { background: var(--bg-muted); }
.new { padding: 1px var(--space-6); border-radius: var(--radius-full); background: var(--brand-primary); color: var(--text-inverse); }
</style>
