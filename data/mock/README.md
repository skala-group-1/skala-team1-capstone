# Mock 데이터셋 (SKALA 캡스톤, 가상 데이터)

> **이 폴더의 데이터는 모두 가상(fictional)이며 교육용입니다. 의료 조언이 아닙니다.**
> 병원·의사·사용자 이름과 주소·전화번호(`02-0000-XXXX`)는 모두 지어낸 값입니다. 실제 병원과 이름이 겹친다면 우연입니다.

외국인이 한국 피부과·성형외과를 비교하고, 번역 채팅으로 상담하고, 예약을 요청하는 서비스의 개발·데모용 데이터를 만듭니다.
Python 3 표준 라이브러리만 사용하며, 같은 `--base-date`와 `--seed`로 실행하면 항상 같은 결과가 나옵니다.

## 실행 방법

```bash
cd data/mock
python3 generate.py --base-date 2026-10-20 --seed 42 --out out/   # 생성
python3 validate.py                                               # 검증 (FK·업무 규칙·SQL 구조·RAG 문서)
```

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--base-date` | 오늘(KST) | 슬롯·예약·리뷰 날짜의 기준일. 슬롯은 기준일부터 21일치 |
| `--seed` | 42 | 난수 시드 |
| `--out` | `out/` | JSON·SQL 출력 위치 |
| `--rag-out` | `rag_docs/hospitals/` | 병원 FAQ 문서 출력 위치 |

PostgreSQL에 직접 넣어 보려면 (빈 DB 기준):

```bash
psql "$DSN" -v ON_ERROR_STOP=1 -f out/schema.sql
psql "$DSN" -v ON_ERROR_STOP=1 -f out/V100__seed.sql
# 또는 한 번에 검증까지
python3 validate.py --psql "$DSN"
```

Flyway를 쓴다면 `schema.sql`을 `V1__schema.sql` 같은 이름으로 마이그레이션 폴더에 두고 `V100__seed.sql`을 그 뒤에 실행하면 됩니다.

## 생성되는 파일

```
data/mock/
├── generate.py            # 생성기
├── validate.py            # 검증기
├── out/
│   ├── schema.sql         # 스키마 app·agent·rag, app 테이블 16개 + 뷰 app.hospital_review_stats, rag.documents·rag.chunks
│   ├── V100__seed.sql     # app 스키마 INSERT (트랜잭션 1개, identity 시퀀스 setval 포함)
│   ├── <table>.json       # 테이블별 JSON (users.json에는 평문 password 필드 포함)
│   └── _meta.json         # base_date, seed, 페르소나 병원 id, 테이블별 건수
└── rag_docs/              # RAG 문서 (영어, YAML front matter)
    ├── procedures/        # 시술 가이드 18개 (직접 작성)  doc_type=GUIDE
    ├── common/            # 공통 문서 4개 (직접 작성)    TRAVEL / PREP / AFTERCARE / FAQ
    └── hospitals/         # 병원 FAQ 50개 (generate.py 생성) doc_type=HOSPITAL_FAQ
```

## 테이블 건수 (`--base-date 2026-10-20 --seed 42`)

| 테이블 | 건수 | 비고 |
| --- | ---: | --- |
| hospitals | 50 | GANGNAM 14, SINSA 10, APGUJEONG 7, CHEONGDAM 5, MYEONGDONG 8, HONGDAE 4, JAMSIL 2 / DERMA 18, PLASTIC 20, BOTH 12 |
| users | 13 | 고객 6, 상담사 3, 병원 관리자 3, 운영자 1 |
| procedures | 18 | SKIN 10, SURGERY 8 |
| doctors | 159 | 병원당 2~4명 (1~3번 병원은 4명) |
| price_options | 678 | 병원당 시술 5~10개, 시술당 옵션 1~3개 |
| slots | 14,244 | 21일 × 30분 단위, 10:00~18:00 안에서 영업시간과 겹치는 구간만 생성. 약 30~50%는 BOOKED |
| reservations | 20 | PENDING 6, CONFIRMED 7, REJECTED 4, CANCELLED 3 |
| reviews | 2,111 | 병원당 5~80개, 평점은 긍정 쪽으로 치우침 (평균 약 4.1) |
| glossary | 66 | 한·영·중·일 용어 |
| conversations | 2 | 아래 상담 2건과 연결된 HUMAN 모드 대화 |
| consultations | 2 | 1번 병원: WAITING 1건(일본어), ACTIVE 1건(중국어) |
| chat_messages | 6 | ACTIVE 상담의 zh↔ko 번역 메시지 |
| ai_tasks, notifications, audit_logs, refresh_tokens | 0 | 테이블만 생성 |
| rag.documents, rag.chunks | 0 | 테이블만 생성 (RAG 적재 파이프라인이 `rag_docs/`를 넣을 자리) |

## 데모 계정

모든 계정의 비밀번호는 `Passw0rd!` 입니다.

| id | 이메일 | 역할 | 언어/국적 | 소속 병원 |
| ---: | --- | --- | --- | --- |
| 1 | customer.en1@demo.local | CUSTOMER | en / US | - |
| 2 | customer.en2@demo.local | CUSTOMER | en / GB | - |
| 3 | customer.zh1@demo.local | CUSTOMER | zh / CN | - (페르소나 사용자, 진행 중 상담 1건) |
| 4 | customer.zh2@demo.local | CUSTOMER | zh / TW | - |
| 5 | customer.ja1@demo.local | CUSTOMER | ja / JP | - (대기 중 상담 1건) |
| 6 | customer.ja2@demo.local | CUSTOMER | ja / JP | - |
| 7 | counselor.h1@demo.local | COUNSELOR | ko | 1 |
| 8 | admin.h1@demo.local | HOSPITAL_ADMIN | ko | 1 |
| 9 | counselor.h2@demo.local | COUNSELOR | ko | 2 |
| 10 | admin.h2@demo.local | HOSPITAL_ADMIN | ko | 2 |
| 11 | counselor.h3@demo.local | COUNSELOR | ko | 3 |
| 12 | admin.h3@demo.local | HOSPITAL_ADMIN | ko | 3 |
| 13 | operator@demo.local | OPERATOR | ko | - |

**비밀번호 해시 주의:** 표준 라이브러리만으로는 BCrypt를 만들 수 없어서 `password_hash`에는 `{bcrypt}PLACEHOLDER`가 들어갑니다.
백엔드 시더가 기동 시 `{bcrypt}PLACEHOLDER`인 행을 찾아 `Passw0rd!`를 BCrypt로 다시 해시해야 로그인됩니다. 평문은 `users.json`의 `password` 필드에만 있고 SQL에는 들어가지 않습니다.

## 데모 시나리오용 데이터

- **1번 병원** (강남, BOTH, ko/en/zh/ja, 통역 있음, 일요일 진료): 매몰법·절개법 쌍꺼풀, 사각턱 보톡스 등 10개 시술. 상담사·관리자 계정, 상담 2건, 예약 8건이 몰려 있습니다.
- **2번 병원** (명동, DERMA): 피부 시술 10개 전부. **3번 병원** (신사, PLASTIC): 수술 8개 + 사각턱 보톡스.
- **페르소나** "중국인 사용자, 쌍꺼풀, 강남 또는 명동, 일주일 안": 강남·명동 + 중국어 지원 + `DOUBLE_EYELID_*` 제공 병원이 8곳(1, 7, 11, 12, 15, 41, 48, 49번, 11번이 명동)이며, 기준일+1~+7일 매일 예약 가능한 슬롯이 있습니다. `validate.py`가 이를 확인합니다.
- **예약 상태와 슬롯 상태:** PENDING → 슬롯 `HELD`(`hold_expires_at` = 요청 시각 + 30분), CONFIRMED → `BOOKED`, REJECTED·CANCELLED → 슬롯이 풀려 `AVAILABLE`. REJECTED 예약의 `alternative_slot_ids`는 같은 병원의 AVAILABLE 슬롯입니다. 예약과 연결되지 않은 BOOKED 슬롯은 "다른 경로로 들어온 예약"으로 간주합니다.

## RAG 문서

모든 문서는 YAML front matter(`doc_id`, `title`, `doc_type`, `procedure_code` 또는 `hospital_id`, `lang: en`, `source: "SKALA capstone fictional dataset"`, `version: 1`)로 시작하고, 그 다음 줄에 `> Fictional educational content. Not medical advice.`가 있습니다.

- 시술 가이드 18개: `## Overview` ~ `## Questions to ask your doctor` 7개 섹션 고정
- 공통 문서 4개: 한국 방문 FAQ, 준비 체크리스트, 일반 사후 관리, 부가세 환급·결제 안내 (제도는 바뀔 수 있으니 확인하라는 단서 포함)
- 병원 FAQ 50개: 영업시간, 지원 언어, 위치, 통역, 시술별 시작 가격, 의료진, 예약 정책("모든 예약은 병원 승인 필요, 슬롯 30분 홀드")

## 알아둘 점

- PENDING 예약의 홀드 만료 시각은 기준일 오전(09~11시) + 30분입니다. 만료 처리 배치가 돌면 데모 시점에는 이미 만료된 상태일 수 있으니, 데모 당일 날짜로 다시 생성하거나 시연 직전에 새 예약을 만드세요.
- 명세상 `conversations`는 비워 두는 테이블이지만, 상담 2건이 `conversation_id`를 참조하므로 연결 대화 2건만 넣었습니다. `conversations.consultation_id` ↔ `consultations.conversation_id`는 순환 FK라 둘 다 `DEFERRABLE INITIALLY DEFERRED`입니다.
- `schema.sql`은 `gen_random_uuid()` 기본값 때문에 `pgcrypto` 확장을 만듭니다 (PG 13 이상이면 없어도 동작).
- `rag.chunks.embedding`이 `vector(1536)`이라 **pgvector 확장이 설치된 PostgreSQL**이 필요합니다 (예: `pgvector/pgvector:pg17` 도커 이미지). `agent` 스키마는 비어 있는 상태로 만들어집니다.
- `app.conversations.parent_conversation_id`(nullable, 자기 참조 FK)가 있으며 시드 데이터에서는 모두 NULL입니다.
- 가격은 서울 시세를 대략 흉내 낸 값일 뿐 실제 가격이 아닙니다.
- 검증: `validate.py` 전체 통과, 로컬 PostgreSQL 17에 `schema.sql` + `V100__seed.sql` 적재 성공을 확인했습니다 (로컬에 pgvector가 없어 이 테스트에서만 `vector(1536)`을 `real[]`로 바꿔 적재).
