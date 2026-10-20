/**
 * 04 ② Toast: 한 번에 하나만, 3초 (액션이 있으면 5초). 위치는 셸이 정함 (고객: 탭 바 위 16 · 직원: 오른쪽 아래 24)
 */
import { reactive } from 'vue'

export type ToastType = 'success' | 'error' | 'info'
interface ToastState {
  id: number
  type: ToastType
  message: string
  actionLabel?: string
  onAction?: () => void
}

export const toastState = reactive<{ current: ToastState | null }>({ current: null })
let seq = 0
let timer: ReturnType<typeof setTimeout> | undefined

export function showToast(message: string, type: ToastType = 'success', action?: { label: string; run: () => void }) {
  clearTimeout(timer)
  const id = ++seq
  toastState.current = { id, type, message, actionLabel: action?.label, onAction: action?.run }
  timer = setTimeout(() => {
    if (toastState.current?.id === id) toastState.current = null
  }, action ? 5000 : 3000)
}

export function hideToast() {
  clearTimeout(timer)
  toastState.current = null
}
