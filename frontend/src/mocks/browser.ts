import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers)

/** main.ts 가 dev + VITE_USE_MSW=true 일 때만 호출 */
export function startMocking() {
  // mock 이 없는 요청(정적 파일, vite HMR 등)은 그대로 통과
  return worker.start({ onUnhandledFrame: 'bypass', quiet: false })
}
