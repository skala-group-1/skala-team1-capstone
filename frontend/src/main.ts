import './styles/tokens.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import { i18n } from './i18n'

async function enableMocking() {
  // dev + VITE_USE_MSW=true 일 때만. 운영 빌드에서는 import.meta.env.DEV=false 라 mocks 코드와 mock JSON 이 번들에서 빠진다
  if (!import.meta.env.DEV || import.meta.env.VITE_USE_MSW !== 'true') return
  const { startMocking } = await import('./mocks/browser')
  await startMocking()
}

void enableMocking().then(() => {
  createApp(App).use(createPinia()).use(router).use(i18n).mount('#app')
})
