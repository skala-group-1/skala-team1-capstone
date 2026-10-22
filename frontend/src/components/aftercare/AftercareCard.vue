<script setup lang="ts">
// 확정 예약 상세의 "시술 사후관리" 카드 → 사후관리 채팅방 열기 (예약 1건당 방 1개)
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { aftercareApi } from '@/api/aftercare'
import { showToast } from '@/composables/useToast'
import AppButton from '@/components/ui/AppButton.vue'

const props = defineProps<{ reservationId: number }>()
const { t } = useI18n()
const router = useRouter()
const busy = ref(false)

async function open() {
  busy.value = true
  try {
    const room = await aftercareApi.open(props.reservationId)
    await router.push(`/chat/${room.conversationId}`)
  } catch {
    showToast(t('aftercare.openFailed'), 'error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="card">
    <h2 class="t-body-16-sb">{{ t('aftercare.title') }}</h2>
    <p class="t-caption-13 secondary">{{ t('aftercare.body') }}</p>
    <AppButton variant="outline" icon="message-circle" block :loading="busy" @click="open">{{ t('aftercare.open') }}</AppButton>
  </section>
</template>

<style scoped>
/* 예약 상세 .card 와 같은 모양 */
.card { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.secondary { color: var(--text-secondary); }
</style>
