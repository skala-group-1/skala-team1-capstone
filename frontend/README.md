# frontend — Vue 3 (고객·상담사·병원관리자 웹, 앱 사이즈 390px)

> 지금은 **골격**입니다. 화면은 무스타일 placeholder 이고, 해야 할 일은 코드에 `// TODO(fe):` 주석으로 적어 두었습니다.
> 기준 문서: Notion `12 공통 계약서`(타입), `07 API·이벤트 명세`(엔드포인트·SSE·STOMP), `08 화면 목록`(화면·라우트), `11 인증`(토큰·가드)

## 실행

```bash
cd frontend
cp .env.example .env.local     # VITE_USE_MSW=true 면 backend 없이 동작
npm install
npm run dev                    # http://localhost:5173
npm run build                  # vue-tsc 타입체크 + 빌드
```

- Node 22 이상
- 로그인 화면에 데모 계정(`customer.zh1@demo.local` / `Passw0rd!`)이 미리 채워져 있습니다. 상담사·병원관리자 계정으로 로그인하면 각 역할 홈으로 갑니다 (계정 목록은 루트 README)

### MSW ↔ 실제 backend 전환

| `.env.local` | 동작 |
| --- | --- |
| `VITE_USE_MSW=true` | 브라우저 안의 MSW 가 `/api/**` 를 가로채 `data/mock/out/*.json` 으로 응답 (backend 불필요) |
| `VITE_USE_MSW=false` | vite 가 `/api`, `/ws` 를 `localhost:8080` backend 로 프록시 (`docker compose up postgres rabbitmq backend`) |

MSW 로 구현된 API: 로그인·refresh·로그아웃·me, 시술 목록, 병원 검색·상세·슬롯, AI 대화 생성·작업 생성 + 가짜 SSE(STATUS→TOKEN×3→RESULT_CARDS→DONE).
나머지(예약·상담·알림·병원관리자)는 `src/mocks/handlers.ts` 하단 TODO 참고. 운영 빌드에는 MSW 코드와 mock JSON 이 포함되지 않습니다.

## 폴더 구조

```
src/
├─ types/contract.ts   12 계약서 enum·DTO·SSE 이벤트·오류 타입 (계약 변경 시 Notion 12 먼저 → 여기)
├─ api/
│  ├─ http.ts          axios: Bearer·Accept-Language, 401 TOKEN_EXPIRED → refresh 1회(동시 요청 공유) → 재시도
│  ├─ session.ts       access token 메모리 보관 (localStorage 금지, 11 문서)
│  ├─ auth.ts catalog.ts ai.ts reservations.ts consultations.ts notifications.ts hospitalAdmin.ts
│  ├─ sse.ts           AI 작업 스트림 (fetch-event-source + Authorization + Last-Event-ID)
│  └─ stomp.ts         상담 채팅·알림 (CONNECT 헤더 JWT)
├─ mocks/              MSW (db.ts: snake_case 행 → camelCase DTO, handlers.ts, browser.ts)
├─ stores/             auth · conversation(SSE reducer) · search · reservation · consultation · notification
├─ router/             08 라우트 + 가드 (비로그인은 /onboarding·/login·/signup 만, 역할 불일치 → 역할 홈)
├─ i18n/               en / zh / ja / ko(스태프)
├─ components/         PagePlaceholder (디자인 오면 삭제)
└─ views/              common · customer(C*) · counselor(S*) · hospitalAdmin(H*) · ops(O1)
```

## 담당자가 할 일 (TODO 찾기)

```bash
grep -rn "TODO(fe)" src
```

큰 줄기:
1. **C4 채팅** (`views/customer/ChatView.vue` + `stores/conversation.ts`) — 데모 시나리오 A·B 의 핵심. SSE 이벤트별 UI(진행 칩, 조건 칩, 카드, 승인 카드, 모드 배지)
2. 탐색·비교·상세·예약 시트 (C5~C9) — API 는 backend PR #1 에 이미 있음
3. 상담사 S1·S2 (STOMP) / 병원관리자 H1·H2
4. MSW 핸들러 나머지 (예약·상담·알림)
5. 디자인 적용

## 디자인 적용 가이드 (연우님 디자인 확정 후)

- 화면 ID(C1, C4-2, S2 …)를 Figma 프레임 이름과 맞춥니다. 각 view 파일 상단 주석의 ID 를 보면 됩니다
- `PagePlaceholder` 를 지우고 실제 마크업으로 교체. 공용 UI(카드, 바텀시트, 칩)는 `src/components/` 에
- 스토어·API 코드는 화면과 분리돼 있으니 디자인 작업 중에 건드릴 필요가 없습니다
- 문구는 하드코딩하지 말고 `src/i18n/locales/*.ts` 에 키 추가 (4개 언어 키 구조 동일, en 이 기준 타입)
- "추천" 표현 금지 → "조건에 맞는 병원" (D-01)

## Docker

```bash
docker build -f frontend/Dockerfile -t capstone-frontend .   # 저장소 루트에서
```
nginx(80)가 정적 파일을 서빙하고 `/api`, `/ws` 를 `backend:8080` 으로 프록시합니다 (SSE 버퍼링 off). compose 등록은 INFRA-03 에서.
