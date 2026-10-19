# backend (Spring Boot 3)

인증·인가, 업무 API(`/api/**`), business-mcp용 내부 API(`/internal/**`). 계약은 Notion **12 공통 계약서**, 인증은 **11 인증·인가 설계**를 따릅니다.

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
# 1) 저장소 루트에서 DB만 띄우고
docker compose up -d postgres rabbitmq
# 2) 로컬에서 실행 (루트의 .env 를 자동으로 읽음)
cd backend && ./gradlew bootRun
```

또는 저장소 루트에서 `docker compose up -d --build backend` (JDK 설치 불필요).

- Swagger: http://localhost:8080/swagger-ui
- 테스트: `./gradlew test` — Docker가 실행 중이어야 함 (pgvector:pg16 컨테이너에 Flyway 적용 후 통합 테스트)

## DB 마이그레이션 (Flyway, schema `app`)

| 버전 | 원천 | 내용 |
| --- | --- | --- |
| V1 | `data/mock/out/schema.sql` (빌드 시 복사) | 전체 스키마 |
| V2 | `src/main/resources/db/migration/` | 계약서 정합: 예약 상태 `EXPIRED`, `reservations.price_option_id` |
| V100 | `data/mock/out/V100__seed.sql` (빌드 시 복사) | mock 데이터 |

- mock 데이터는 `data/mock/generate.py`가 단일 원천입니다. backend 전용 스키마 변경은 **V3~V99**로 이 폴더에 추가하세요.
- seed를 재생성하면 체크섬이 바뀌므로 `docker compose down -v` 후 다시 기동합니다.
- backend 없이 DB만 채우려면 저장소 루트에서 `docker compose run --rm db-seed` (같은 Flyway 11.7.2 + 같은 파일이라 이후 backend 기동 시 이력이 이어짐). V3 이상을 추가하면 db-seed 에도 자동 반영됩니다.

## 패키지

```
com.skala.capstone
├── auth/      JwtProvider, JwtAuthenticationFilter, InternalServiceTokenFilter, SecurityConfig,
│              AuthController(signup/login/refresh/logout), RefreshTokenService(회전·재사용 감지), PasswordSeeder
├── user/      User 엔티티, GET /api/me
├── catalog/   CatalogService(검색·상세·슬롯·리뷰·비교·시술 정규화) ← /api 와 /internal 컨트롤러가 공유
└── common/    error(오류 코드·다국어 메시지), web(X-Trace-Id, locale, 페이지), security(CurrentUser, AuditLogger), config
```

## 구현된 API

| 공개 (`/api`, JWT 필수 — `/api/auth/**` 제외) | 내부 (`/internal`, `X-Service-Token` + `X-Acting-User-Id`) |
| --- | --- |
| `POST /api/auth/signup` `login` `refresh` `logout` | `GET /internal/procedures/normalize?text=&locale=` |
| `GET /api/me` | `GET /internal/hospitals/search` (Conditions 쿼리 + `limit`) |
| `GET /api/procedures` | `GET /internal/hospitals/{id}?lite=` |
| `GET /api/hospitals/search` | `GET /internal/hospitals/{id}/doctors?procedureCode=` |
| `GET /api/hospitals/{id}` | `GET /internal/hospitals/{id}/prices?procedureCode=` |
| `GET /api/hospitals/{id}/slots` | `GET /internal/hospitals/{id}/slots` (최대 20) |
| `GET /api/hospitals/{id}/reviews` | `POST /internal/hospitals/compare` |
| `POST /api/hospitals/compare` | |

검색 규칙: 시술 지정 시 그 시술 가격이 있는 병원만(최저가 = `minPriceKrw`), 날짜 지정 시 입국일~출국일에 AVAILABLE 슬롯이 있는 병원만, 슬롯은 그 시술 담당 의사(specialties) 기준. 정렬 `REVIEW_COUNT`(기본) `RATING` `PRICE` `DISTANCE`(좌표 없으면 서울시청 기준).

## 다음 작업 (13 착수 가이드 순서)

예약 상태머신·만료 스케줄러·멱등키 → AI 작업 큐·SSE → 상담·STOMP·번역 큐·알림·병원관리자 API → `/internal/trip-plans`
