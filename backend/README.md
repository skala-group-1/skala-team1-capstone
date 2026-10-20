# backend (Spring Boot 3)

인증·인가, 업무 API(`/api/**`), business-mcp용 내부 API(`/internal/**`), AI 작업 중계(SSE), 통역 채팅(STOMP), RabbitMQ 연동.
API 상세는 Notion **「Backend API 상세 명세」**, 필드·enum 기준은 **「공통 계약서」**, 인증은 **「인증·인가 설계」**를 따릅니다.

## 한눈에 보기 (개발자가 아니어도)

| 기능 | 무엇을 하나요 |
| --- | --- |
| 로그인 | 4가지 역할(고객/상담사/병원관리자/운영자)로 로그인. 로그인해야 모든 기능 사용 |
| 병원 찾기 | 시술·지역·날짜·예산·언어로 조건에 맞는 병원을 정렬해 보여줌 (추천 아님) |
| 예약 | 고객이 시간을 골라 요청 → 30분간 자리 잡힘 → 병원이 승인/반려. 30분 지나면 자동 만료 |
| AI 상담 중계 | 고객 질문을 AI(agent)에게 큐로 전달하고, AI가 답하는 과정을 실시간(SSE)으로 화면에 흘려보냄. 예약 같은 중요한 행동은 고객 승인 후에만 |
| 상담사 통역 채팅 | 고객 ↔ 병원 상담사 실시간 채팅(STOMP). 메시지는 AI 번역 워커가 번역 |
| 일정 계산 | "출국 전에 회복까지 끝낼 수 있나?"를 병원별로 계산 (의료 판단 아님) |
| 알림 | 예약 승인·반려·상담 수락 등을 상대방에게 실시간 알림 |
| 안전장치 | 남의 예약·다른 병원 상담방 접근 차단 + 감사 로그, 중복 요청·동시 예약 방지 |

## 버전

| 항목 | 버전 |
| --- | --- |
| Java | 21 (Gradle toolchain) |
| Gradle | 9.8.1 (wrapper, `./gradlew`) |
| Spring Boot | 3.5.16 |
| jjwt / springdoc | 0.12.7 / 2.8.17 |
| Testcontainers | 2.0.5 (Docker Engine 29+ 대응) |

## 실행

```bash
# 저장소 루트에서 (JDK 설치 불필요)
cp .env.example .env
docker compose up -d --build postgres rabbitmq backend
```

로컬 개발: `docker compose up -d postgres rabbitmq` 후 `cd backend && ./gradlew bootRun` (루트 `.env` 자동 읽음).

- Swagger: http://localhost:8080/swagger-ui — 로그인 응답의 `accessToken`을 Authorize에 입력
- RabbitMQ 관리 콘솔: http://localhost:15672 (guest/guest) — 큐·DLQ 확인
- 테스트: `./gradlew test` — Docker 필요 (Postgres + RabbitMQ 컨테이너를 띄워 통합 테스트 47건)

## DB 마이그레이션 (Flyway, schema `app`)

| 버전 | 원천 | 내용 |
| --- | --- | --- |
| V1 | `data/mock/out/schema.sql` (빌드 시 복사) | 전체 스키마 |
| V2 | `src/main/resources/db/migration/` | 계약서 정합: 예약 상태 `EXPIRED`, `reservations.price_option_id` |
| V100 | `data/mock/out/V100__seed.sql` (빌드 시 복사) | mock 데이터 |
| V101 | `src/main/resources/db/migration/` | AI·채팅 컬럼: 대화 조건, 작업 결과 카드·이벤트 번호, 메시지 중복 방지 키 |

- **새 backend 마이그레이션은 V102부터** 추가합니다. (V3~V99로 만들면 이미 v100까지 적용된 DB에서 "순서가 어긋난 마이그레이션"으로 기동이 실패합니다.)
- mock 데이터는 `data/mock/generate.py`가 단일 원천입니다. seed를 재생성하면 체크섬이 바뀌므로 `docker compose down -v` 후 다시 기동합니다.
- backend 없이 DB만 채우려면 저장소 루트에서 `docker compose run --rm db-seed` (같은 Flyway 11.7.2 + 같은 파일이라 이후 backend 기동 시 이력이 이어짐).

## 패키지

```
com.skala.capstone
├── auth/          로그인·토큰(JWT)·보안 필터, 데모 비밀번호 설정
├── user/          내 정보 조회·언어 변경
├── catalog/       병원 검색·상세·슬롯·리뷰·비교 (/api 와 /internal 이 공유)
├── reservation/   예약 상태머신, 30분 만료 스케줄러, 병원관리자 승인·반려·대시보드
├── notification/  알림 저장·실시간 푸시 (notify 큐)
├── ai/            AI 대화창·작업 접수·agent 이벤트 처리·SSE 중계
├── consultation/  상담 요청·수락·종료, 통역 채팅(STOMP), 번역 큐 처리
├── trip/          출국 전 회복 가능 일정 계산
├── docs/          근거 문서 원문 (agent 경유)
├── ops/           운영자: 감사 로그·실패 작업
└── common/        오류 형식, 추적 ID, 다국어 메시지, RabbitMQ 구성·발행, 감사 로그
```

## API 목록

| 영역 | 공개 (`/api`, JWT 필수 — `/api/auth/**` 제외) |
| --- | --- |
| 인증 | `POST /api/auth/signup` `login` `refresh` `logout`, `GET/PATCH /api/me` |
| 탐색 | `GET /api/procedures`, `GET /api/hospitals/search`, `GET /api/hospitals/{id}`, `/slots`, `/reviews`, `POST /api/hospitals/compare` |
| 예약(고객) | `POST /api/reservations`, `GET /api/reservations/me`, `GET /api/reservations/{id}`, `POST .../{id}/cancel`, `POST .../{id}/accept-alternative` |
| 병원관리자 | `GET /api/hospital-admin/dashboard`, `GET /api/hospital-admin/reservations`, `POST .../reservations/{id}/approve`, `POST .../reservations/{id}/reject` |
| AI | `POST/GET /api/ai/conversations`, `GET /api/ai/conversations/{id}`, `POST/GET /api/ai/tasks`, `GET /api/ai/tasks/{id}`, `GET /api/ai/tasks/{id}/stream`(SSE), `POST /api/ai/tasks/{id}/approval` |
| 상담 | `GET /api/consultations/{id}`, `GET/POST /api/consultations/{id}/messages`, `POST .../messages/{msgId}/retry-translation` |
| 상담사 | `GET /api/counselor/consultations`, `POST .../{id}/accept`, `POST .../{id}/close` |
| 알림 | `GET /api/notifications`, `POST /api/notifications/{id}/read`, `POST /api/notifications/read-all` |
| 기타 | `GET /api/docs/{docId}`, `GET /api/ops/audit-logs`, `GET /api/ops/ai-tasks` |

| 내부 (`/internal`, `X-Service-Token` + `X-Acting-User-Id`) — business-mcp·agent 용 |
| --- |
| `GET /internal/procedures/normalize`, `GET /internal/hospitals/search`, `/{id}`, `/{id}/doctors`, `/{id}/prices`, `/{id}/slots`, `POST /internal/hospitals/compare` |
| `GET /internal/reservations/mine`, `POST /internal/reservations`, `POST /internal/reservations/{id}/cancel` |
| `POST /internal/consultations`, `POST /internal/conversations`, `POST /internal/trip-plans` |

실시간: STOMP `/ws` — SEND `/app/consultations/{id}/send`, SUBSCRIBE `/topic/consultations/{id}`, `/user/queue/notifications`, `/user/queue/errors`

## RabbitMQ

backend가 기동 시 exchange `capstone.direct`, 작업 큐, DLQ, 5초·15초 지연 재시도 큐를 선언합니다 (목록·인자는 「Backend API 상세 명세」 10장).
다른 곳(infra `definitions.json`, agent)에서 같은 큐를 선언하려면 **인자가 완전히 같아야** 합니다.

## 아직 안 한 것

- `GET/DELETE /api/me/ai-profile` (P1, agent 장기 기억 API 확정 후)
- 로그인 5회 실패 잠금 (P1)
