/** 1초마다 갱신되는 현재 시각 (홀드 타이머 mm:ss, 04 ⑤ "홀드 타이머") */
import { onBeforeUnmount, ref } from 'vue'

export function useNow(intervalMs = 1000) {
  const now = ref(Date.now())
  const id = setInterval(() => (now.value = Date.now()), intervalMs)
  onBeforeUnmount(() => clearInterval(id))
  return now
}
