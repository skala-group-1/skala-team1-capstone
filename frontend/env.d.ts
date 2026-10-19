/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 공개 API prefix. 개발·운영 모두 /api (프록시) */
  readonly VITE_API_BASE: string
  /** true 면 MSW 로 backend 없이 동작 (dev 전용, 운영 빌드에서는 무시) */
  readonly VITE_USE_MSW: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
