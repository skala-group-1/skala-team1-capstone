import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'
import { appHandlers } from './app'

// app 핸들러가 먼저 (같은 경로면 앞의 것이 응답: AI 대화는 시나리오 버전, /me 는 email 포함 버전)
export const worker = setupWorker(...appHandlers, ...handlers)

/** main.ts 가 dev + VITE_USE_MSW=true 일 때만 호출 */
export function startMocking() {
  // mock 이 없는 요청(정적 파일, vite HMR 등)은 그대로 통과
  return worker.start({ onUnhandledFrame: 'bypass', quiet: false })
}
