<script setup lang="ts">
// 운영 화면: 오늘의 시술 관리 안내를 지금 보내기 (매일 오전 9시 자동 실행과 같은 작업, 이미 보낸 방은 건너뜀)
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { aftercareOpsApi } from '@/api/aftercare'
import { showToast } from '@/composables/useToast'
import AppButton from '@/components/ui/AppButton.vue'

const { t } = useI18n()
const busy = ref(false)
const result = ref<{ checked: number; requested: number } | null>(null)

async function send() {
  busy.value = true
  try {
    result.value = await aftercareOpsApi.sendDailyGuides()
    showToast(t('aftercare.ops.done', result.value))
  } catch {
    showToast(t('aftercare.ops.failed'), 'error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="card">
    <header>
      <h2 class="t-title-18">{{ t('aftercare.ops.title') }}</h2>
      <p class="t-body-14 secondary">{{ t('aftercare.ops.body') }}</p>
    </header>
    <div class="row">
      <AppButton icon="send" :loading="busy" @click="send">{{ t('aftercare.ops.send') }}</AppButton>
      <span v-if="result" class="t-caption-13 secondary">{{ t('aftercare.ops.done', result) }}</span>
    </div>
  </section>
</template>

<style scoped>
.card { display: flex; flex-direction: column; gap: var(--space-12); padding: var(--space-16); border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-12); }
.secondary { color: var(--text-secondary); }
</style>
