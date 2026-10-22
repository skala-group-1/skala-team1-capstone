<script setup lang="ts">
// Figma Chat Bubble: Me(오른쪽, 핑크) · Main AI · Hospital Agent · Counselor · Customer(S2) · System(가운데 pill) · Typing · Error
// 말풍선 아래 내용(카드·칩·번역 상태)은 기본 slot. 아바타 줄(왼쪽 40)에 맞춰 들여쓰기는 부모가 함
import AppIcon, { type IconName } from '../ui/AppIcon.vue'

const props = defineProps<{
  sender: 'me' | 'ai' | 'agent' | 'counselor' | 'customer' | 'system' | 'typing' | 'error'
  text?: string
  /** 오류 말풍선에서 "다시 시도"를 숨김 (다시 보내도 같은 결과인 오류) */
  noRetry?: boolean
  name?: string
  time?: string
  /** 번역 실패 등으로 말풍선 테두리 강조 */
  failed?: boolean
}>()
defineEmits<{ retry: [] }>()

const AVATAR: Partial<Record<typeof props.sender, IconName>> = {
  ai: 'sparkles',
  typing: 'sparkles',
  error: 'sparkles',
  agent: 'hospital',
  counselor: 'headphones',
  customer: 'user',
}
</script>

<template>
  <div v-if="sender === 'system'" class="system">
    <span class="system__pill t-caption-12">{{ text }}</span>
  </div>

  <div v-else-if="sender === 'me'" class="me">
    <div class="me__row">
      <span v-if="time" class="time t-caption-11">{{ time }}</span>
      <p class="bubble bubble--me t-body-15" :class="{ 'bubble--failed': failed }">{{ text }}</p>
    </div>
    <slot />
  </div>

  <div v-else class="other" :class="`other--${sender}`">
    <span class="avatar"><AppIcon :name="AVATAR[sender] ?? 'sparkles'" :size="18" /></span>
    <div class="other__content">
      <span v-if="name" class="name t-caption-12-sb">{{ name }}</span>
      <p v-if="sender === 'typing'" class="bubble bubble--typing" :aria-label="$t('chat.typing')">
        <i /><i /><i />
      </p>
      <p v-else-if="sender === 'error'" class="bubble bubble--error t-body-14">
        <AppIcon name="alert-triangle" :size="16" />
        <span>{{ text }}</span>
        <button v-if="!noRetry" type="button" class="retry hit t-caption-12-sb" @click="$emit('retry')">
          <AppIcon name="refresh-cw" :size="14" />{{ $t('common.retry') }}
        </button>
      </p>
      <p v-else class="bubble t-body-15" :class="`bubble--${sender}`">{{ text }}<slot name="streaming" /></p>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.system { display: flex; justify-content: center; }
.system__pill { padding: 6px var(--space-12); border-radius: var(--radius-full); background: var(--bg-muted); color: var(--chat-system-text); text-align: center; }

.me { display: flex; flex-direction: column; align-items: flex-end; gap: var(--space-4); }
.me__row { display: flex; align-items: flex-end; justify-content: flex-end; gap: var(--space-6); }
.time { flex: none; color: var(--text-tertiary); }

.other { display: flex; gap: var(--space-8); align-items: flex-start; }
.other__content { display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-4); min-width: 0; max-width: calc(100% - 40px); }
.avatar {
  display: grid;
  place-items: center;
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--brand-subtle);
  color: var(--chat-ai-accent);
}
.other--agent .avatar { background: var(--status-neutral-bg); color: var(--chat-agent-accent); }
.other--counselor .avatar { background: var(--status-info-bg); color: var(--chat-counselor-accent); }
.other--customer .avatar { background: var(--bg-muted); color: var(--icon-default); }
.name { color: var(--text-secondary); }

.bubble {
  max-width: 264px;
  padding: 10px 14px;
  border-radius: var(--radius-xs) var(--radius-lg) var(--radius-lg) var(--radius-lg);
  white-space: pre-wrap;
  word-break: break-word;
}
.bubble--me {
  border-radius: var(--radius-lg) var(--radius-xs) var(--radius-lg) var(--radius-lg);
  background: var(--chat-user-bubble);
  color: var(--chat-user-text);
}
.bubble--failed { outline: 1.5px solid var(--status-danger-solid); outline-offset: -1.5px; }
.bubble--ai { background: var(--chat-ai-bubble); }
.bubble--agent { background: var(--chat-agent-bubble); }
.bubble--counselor { background: var(--chat-counselor-bubble); }
.bubble--customer { border: 1px solid var(--border-default); background: var(--bg-default); }
.bubble--typing { display: flex; gap: var(--space-4); padding: 14px; background: var(--chat-ai-bubble); }
.bubble--typing i { width: 6px; height: 6px; border-radius: 50%; background: var(--text-secondary); animation: blink 1.2s infinite; }
.bubble--typing i:nth-child(2) { animation-delay: 0.2s; }
.bubble--typing i:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%, 100% { opacity: 0.25; } 40% { opacity: 1; } }
.bubble--error { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-8); background: var(--status-danger-bg); color: var(--status-danger); }
.retry { display: inline-flex; align-items: center; gap: var(--space-4); padding: 0; border: 0; background: none; color: inherit; }
</style>
