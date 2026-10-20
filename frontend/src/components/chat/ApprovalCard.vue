<script setup lang="ts">
// C4-2 승인 카드 (HITL): APPROVAL_REQUIRED 의 display(rows·notice) 그대로 표시. 가격·시간은 agent 가 도구 결과로 채운 값
// 수정은 pendingAction.editable 키만 (예약: note) → ApprovalRequest.editedArgs
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '../ui/AppIcon.vue'
import AppButton from '../ui/AppButton.vue'
import type { PendingAction } from '@/types/contract'

const props = defineProps<{ action: PendingAction; busy?: boolean }>()
const emit = defineEmits<{ approve: [editedArgs: Record<string, unknown> | null]; reject: [] }>()
const { t } = useI18n()

const editingNote = ref(false)
const note = ref(typeof props.action.args.note === 'string' ? props.action.args.note : '')
const canEditNote = computed(() => props.action.editable.includes('note'))
const primaryLabel = computed(() =>
  props.action.action === 'CANCEL_RESERVATION' ? t('chat.approval.cancelReservation') : t('chat.approval.request'),
)

function approve() {
  emit('approve', editingNote.value ? { note: note.value.trim() || null } : null)
}
</script>

<template>
  <section class="card" :aria-label="action.display.title">
    <header class="head">
      <AppIcon name="calendar" :size="20" class="brand" />
      <h3 class="t-body-16-sb">{{ action.display.title }}</h3>
    </header>
    <dl class="rows">
      <div v-for="row in action.display.rows" :key="row.label" class="row">
        <dt class="t-caption-13">{{ row.label }}</dt>
        <dd class="t-body-14-sb">{{ row.value }}</dd>
      </div>
    </dl>
    <label v-if="editingNote" class="note">
      <span class="t-caption-13">{{ t('chat.approval.note') }}</span>
      <textarea v-model="note" class="t-body-14" rows="3" maxlength="500" :placeholder="t('chat.approval.notePlaceholder')" />
    </label>
    <p v-if="action.display.notice" class="notice t-caption-13">
      <AppIcon name="clock" :size="16" />
      <span>{{ action.display.notice }}</span>
    </p>
    <div class="actions">
      <AppButton block :loading="busy" @click="approve">{{ primaryLabel }}</AppButton>
      <div class="actions__row">
        <AppButton v-if="canEditNote && !editingNote" variant="outline" block :disabled="busy" @click="editingNote = true">
          {{ t('chat.approval.edit') }}
        </AppButton>
        <AppButton variant="ghost" block :disabled="busy" @click="emit('reject')">{{ t('common.cancel') }}</AppButton>
      </div>
    </div>
  </section>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
  width: 100%;
  padding: var(--space-16);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
}
.head { display: flex; align-items: center; gap: var(--space-8); }
.brand { color: var(--brand-primary); }
/* 라벨 열은 가장 긴 라벨 폭 (영어 'Procedure' 등) */
.rows { display: grid; grid-template-columns: auto 1fr; gap: 10px var(--space-12); margin: 0; }
.row { display: contents; }
.row dt { min-width: 44px; color: var(--text-tertiary); }
.row dd { margin: 0; }
.note { display: flex; flex-direction: column; gap: var(--space-6); color: var(--text-secondary); }
.note textarea {
  padding: var(--space-12);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  resize: vertical;
  color: var(--text-primary);
}
.notice {
  display: flex;
  gap: var(--space-8);
  padding: var(--space-12);
  border-radius: var(--radius-sm);
  background: var(--status-info-bg);
  color: var(--status-info);
}
.notice .icon { flex: none; margin-top: 1px; }
.actions { display: flex; flex-direction: column; gap: var(--space-8); }
.actions__row { display: flex; gap: var(--space-8); }
</style>
