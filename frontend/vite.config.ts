import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 개발 서버: 5173 (「공통 계약서」 9장). 운영(docker)은 nginx 80 이 /api, /ws 를 backend 로 프록시한다.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      // MSW 가 쓰는 mock 데이터 (저장소 단일 원천: data/mock/out). 직접 수정 금지 → generate.py 로 재생성
      '@mock': fileURLToPath(new URL('../data/mock/out', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    fs: {
      // frontend/ 밖의 data/mock/out 을 dev 서버가 읽을 수 있게 허용
      allow: ['..'],
    },
    proxy: {
      // VITE_USE_MSW=false 일 때 실제 backend(8080)로 붙는다. SSE 도 같은 경로(/api/ai/tasks/{id}/stream)
      '/api': { target: 'http://localhost:8080', changeOrigin: true },
      // STOMP (「API·이벤트 명세」 4장)
      '/ws': { target: 'ws://localhost:8080', ws: true },
    },
  },
})
