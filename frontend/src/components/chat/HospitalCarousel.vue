<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import HospitalCard from '../HospitalCard.vue'
import type { HospitalCard as Card } from '@/types/contract'

defineProps<{ cards: Card[]; procedureName?: string | null }>()
const emit = defineEmits<{ open: [id: number]; chat: [id: number] }>()
const { t } = useI18n()
const track = ref<HTMLElement | null>(null)
const dragging = ref(false)
let pointer: { id: number; x: number; left: number } | null = null
let suppressClick = false
function move(direction: number) {
  const el = track.value
  const first = el?.children[0] as HTMLElement | undefined
  const second = el?.children[1] as HTMLElement | undefined
  if (!el || !first) return
  const step = second ? second.offsetLeft - first.offsetLeft : first.offsetWidth
  el.scrollBy({ left: direction * step, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
}
function pointerDown(event: PointerEvent) {
  suppressClick = false
  if (event.pointerType !== 'mouse' || event.button !== 0 || !track.value) return
  pointer = { id: event.pointerId, x: event.clientX, left: track.value.scrollLeft }
}
function pointerMove(event: PointerEvent) {
  const el = track.value
  if (!pointer || pointer.id !== event.pointerId || !el) return
  const distance = event.clientX - pointer.x
  if (!dragging.value && Math.abs(distance) < 6) return
  dragging.value = true
  suppressClick = true
  el.setPointerCapture(event.pointerId)
  el.scrollLeft = pointer.left - distance
  event.preventDefault()
}
function pointerEnd() {
  pointer = null
  dragging.value = false
}
function click(event: MouseEvent) {
  // A drag ending over a card must not open a hospital conversation.
  if (suppressClick) {
    event.preventDefault()
    event.stopPropagation()
    suppressClick = false
  }
}
</script>

<template>
  <div class="carousel">
    <div
      ref="track" class="cards" :class="{ dragging }" role="list" tabindex="0" :aria-label="t('chat.cards.browse')"
      @keydown.left.self.prevent="move(-1)" @keydown.right.self.prevent="move(1)"
      @pointerdown="pointerDown" @pointermove="pointerMove" @pointerup="pointerEnd" @pointercancel="pointerEnd"
      @lostpointercapture="pointerEnd" @click.capture="click" @dragstart.prevent
    >
      <HospitalCard
        v-for="card in cards" :key="card.id" :card="card" role="listitem" variant="compact"
        :procedure-name="procedureName" @open="emit('open', card.id)" @chat="emit('chat', card.id)"
      />
    </div>
  </div>
</template>

<style scoped>
.carousel { min-width: 0; }
.cards { display: flex; gap: var(--space-12); margin: 0 -16px; padding: var(--space-4) var(--space-16); overflow-x: auto; scrollbar-width: none; }
.cards::-webkit-scrollbar { display: none; }
@media (pointer: fine) { .cards { cursor: grab; user-select: none; } }
.cards.dragging { cursor: grabbing; }
</style>
