<script setup lang="ts">
// Figma Text Field: 라벨(Caption 13) + 48 박스(반경 12) + 오류(Caption 12 danger) / 도움말(tertiary)
// State: Default(border/default) · Focus(border/focus 1.5) · Error(status/danger 1.5). options 를 주면 select
import { useId } from 'vue'
import AppIcon from './AppIcon.vue'

const model = defineModel<string>({ default: '' })
defineProps<{
  label: string
  type?: string
  placeholder?: string
  autocomplete?: string
  error?: string | null
  /** 오류 표시는 하되 문구는 다른 곳에서 (로그인 401: 두 칸 모두 빨간 테두리) */
  invalid?: boolean
  hint?: string
  options?: { value: string; label: string }[]
  required?: boolean
  /** date 입력 최댓값 (생년월일: 오늘) */
  max?: string
}>()
const id = useId()
</script>

<template>
  <div class="field">
    <label :for="id" class="field__label t-caption-13">{{ label }}</label>
    <div class="field__box" :class="{ 'field__box--error': error || invalid }">
      <select v-if="options" :id="id" v-model="model" class="field__input" :required="required" :aria-invalid="!!error || invalid">
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <input
        v-else
        :id="id"
        v-model="model"
        class="field__input"
        :type="type ?? 'text'"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :required="required"
        :max="max"
        :aria-invalid="!!error || invalid"
        :aria-describedby="error || hint ? `${id}-msg` : undefined"
      />
      <AppIcon v-if="options" name="chevron-down" :size="18" class="field__chevron" />
    </div>
    <p v-if="error" :id="`${id}-msg`" class="field__error t-caption-12" role="alert">
      <slot name="error-icon" />{{ error }}
    </p>
    <p v-else-if="hint" :id="`${id}-msg`" class="field__hint t-caption-12">{{ hint }}</p>
  </div>
</template>

<style scoped>
.field { display: flex; flex-direction: column; gap: var(--space-6); }
.field__label { color: var(--text-secondary); }
.field__box {
  position: relative;
  display: flex;
  align-items: center;
  height: 48px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-default);
}
.field__box:focus-within { border: 1.5px solid var(--border-focus); }
.field__box--error,
.field__box--error:focus-within { border: 1.5px solid var(--status-danger); }
.field__input {
  flex: 1;
  width: 100%;
  height: 100%;
  padding: 0 14px;
  border: 0;
  border-radius: inherit;
  background: transparent;
  font: 400 15px/22px var(--font-sans);
  color: var(--text-primary);
  outline: none;
  appearance: none;
}
.field__input::placeholder { color: var(--text-tertiary); }
.field__chevron { position: absolute; right: 14px; color: var(--icon-default); pointer-events: none; }
.field__error { display: flex; align-items: center; gap: var(--space-4); color: var(--status-danger); }
.field__hint { color: var(--text-tertiary); }
</style>
