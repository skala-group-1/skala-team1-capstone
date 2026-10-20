<script lang="ts">
// Figma Badge/Status · Badge/Mode · Badge/Hold (pill 24) · Badge/Tag (언어 태그 20)
// tone 은 status 토큰 이름
import type { ReservationStatus } from '@/types/contract'

export type BadgeTone = 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'muted' | 'agent'

/** Badge/Status 5종 (승인 대기·예약 확정·반려·취소·만료) */
export const RESERVATION_TONE: Record<ReservationStatus, BadgeTone> = {
  PENDING: 'warning',
  CONFIRMED: 'success',
  REJECTED: 'danger',
  CANCELLED: 'neutral',
  EXPIRED: 'muted',
}
</script>

<script setup lang="ts">
import AppIcon, { type IconName } from './AppIcon.vue'

withDefaults(defineProps<{ tone?: BadgeTone; dot?: boolean; icon?: IconName; tag?: boolean }>(), { tone: 'neutral' })
</script>

<template>
  <span v-if="tag" class="tag t-caption-11"><slot /></span>
  <span v-else class="badge t-caption-12-sb" :class="`badge--${tone}`">
    <span v-if="dot" class="badge__dot" aria-hidden="true" />
    <AppIcon v-if="icon" :name="icon" :size="14" />
    <slot />
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-4);
  height: 24px;
  padding: 0 var(--space-8);
  border-radius: var(--radius-full);
  white-space: nowrap;
  flex: none;
}
.badge__dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.badge--brand { background: var(--brand-subtle); color: var(--brand-text); }
.badge--success { background: var(--status-success-bg); color: var(--status-success); }
.badge--warning { background: var(--status-warning-bg); color: var(--status-warning); }
.badge--danger { background: var(--status-danger-bg); color: var(--status-danger); }
.badge--info { background: var(--status-info-bg); color: var(--status-info); }
.badge--neutral { background: var(--status-neutral-bg); color: var(--status-neutral); }
.badge--muted { background: var(--status-neutral-bg); color: var(--text-tertiary); }
.badge--agent { background: var(--status-neutral-bg); color: var(--chat-agent-accent); }

.tag {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 var(--space-6);
  border-radius: var(--radius-xs);
  background: var(--bg-muted);
  color: var(--text-secondary);
  white-space: nowrap;
}
</style>
