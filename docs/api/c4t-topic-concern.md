# C4-T AI 상담 주제 선택 → 피부 고민 시술 정보 — API 명세 (제안)

> 상태: **FE 제안 / 공통 계약서 반영 전**. 이름은 FE(`frontend/src/types/contract.ts`)와 MSW mock(`frontend/src/mocks/app.ts`)에 이미 이 형태로 들어가 있다.
> 이름을 바꾸면 FE도 같이 바꿔야 하니 리뷰 때 확정해 주세요. 기존 규칙(JSON camelCase, DB snake_case, 금액 정수 KRW)을 그대로 따른다.
> Figma: 02 Screens › `C4-T · AI 상담 주제 선택 → 피부 고민 시술 추천 (NEW)`

## 0. 화면 흐름과 호출

| # | 화면 | 사용자 동작 | 호출 |
| --- | --- | --- | --- |
| ㉠ | 첫 진입: 환영 말풍선 + 주제 카드 캐러셀 (3장 × 버튼 3개) + 빠른 답장 칩 | 주제 버튼 탭 | `POST /api/ai/tasks` `action: SELECT_TOPIC` |
| ㉡ | 상단 "상담 주제" 바, AI 질문, 고민 칩(여러 개 선택), "N개 선택 완료" | 완료 탭 | `POST /api/ai/tasks` `action: FIND_BY_CONCERNS` |
| ㉢ | 관련 시술 정보 카드, 면책 문구, 다음 행동 칩 | "병원 찾기" 칩 / 직접 입력 | 기존 `POST /api/ai/tasks` (`message`만) |

- 새 REST 엔드포인트는 없다. 기존 `POST /api/ai/tasks` + SSE에 **action 2개, SSE 이벤트 1개, 필드 2개**만 추가한다.
- "주제 바꾸기"를 누르면 캐러셀이 다시 나오고, 다른 주제를 고르면 `SELECT_TOPIC`을 다시 보낸다(덮어쓰기).
- 고민 칩 대신 말로 써도 된다("기미·잡티, 모공이요. 다운타임은 짧게요."). 이 경우 `action` 없이 `message`만 오고, topic이 `SKIN_CONCERN`이면 agent가 고민을 뽑아서 ㉢처럼 답한다.

## 1. Enum 추가

```ts
type ConsultTopic =
  | 'SKIN_CONCERN'        // 피부 고민으로 시술 찾기
  | 'PROCEDURE_INFO'      // 시술 정보·가격 알아보기
  | 'RECOVERY'            // 회복 기간·주의사항
  | 'HOSPITAL_SEARCH'     // 조건으로 병원 찾기
  | 'HOSPITAL_COMPARE'    // 병원 비교하기
  | 'COUNSELOR_CHAT'      // 병원 상담사와 통역 채팅
  | 'BOOK'                // 예약 요청하기
  | 'MY_RESERVATIONS'     // 내 예약 조회
  | 'CANCEL_RESERVATION'  // 예약 취소

type SkinConcern =
  | 'PIGMENTATION'      // 기미·잡티
  | 'PORES'             // 모공
  | 'ACNE_SCAR'         // 여드름·흉터
  | 'WRINKLE_FIRMNESS'  // 주름·탄력
  | 'TONE_TEXTURE'      // 피부톤·결
  | 'REDNESS'           // 홍조
  | 'FACE_CONTOUR'      // 얼굴 라인
```

화면 문구(라벨)는 FE i18n이 갖고 있고, 서버는 코드만 주고받는다.

## 2. DTO 변경

### 2-1. `ProcedureInfo` (신규)

```ts
interface ProcedureInfo {
  procedureCode: ProcedureCode
  name: string              // Accept-Language 로 고른 시술명 (app.procedures.name_*)
  description: string       // app.procedures.description_ko|en (zh/ja 는 en 대체)
  concerns: SkinConcern[]   // 사용자가 고른 고민 중 이 시술과 매핑된 것 (카드 태그)
  durationMin: number       // app.procedures.duration_min
  downtimeDays: number      // app.procedures.downtime_days
  minPriceKrw: number | null  // 해당 시술 app.price_options.price_krw 최저 (등록 0건이면 null)
  maxPriceKrw: number | null  // 같은 조건 최고
}
```

```json
{
  "procedureCode": "PICO_TONING",
  "name": "피코토닝",
  "description": "피코초 레이저로 색소와 피부톤 개선을 돕는 시술입니다.",
  "concerns": ["PIGMENTATION"],
  "durationMin": 20,
  "downtimeDays": 0,
  "minPriceKrw": 50000,
  "maxPriceKrw": 589000
}
```

- 정렬: 고른 고민 순서 → 같은 고민 안에서는 `procedure_concerns.sort_order`. **순위·추천 점수는 넣지 않는다.**
- 가격·시간은 DB 값만. 효과·적합성 문구를 만들지 않는다(카드 아래 면책 문구는 FE 고정 문구).

### 2-2. `Conversation` — `topic` 추가

```ts
interface Conversation {
  // ...기존 필드
  topic: ConsultTopic | null   // 메인 대화에서 마지막으로 고른 주제. 병원 대화(HOSPITAL/HUMAN)는 항상 null
}
```

`GET /api/ai/conversations`, `GET /api/ai/conversations/{id}`, `POST /api/ai/conversations` 응답 모두에 포함. FE는 이 값으로 상단 "상담 주제" 바와 고민 칩 표시 여부를 정한다.

### 2-3. `ConversationMessage` — `procedures` 추가

```ts
interface ConversationMessage {
  // ...기존 필드 (role, text, sources, cards, createdAt)
  procedures?: ProcedureInfo[]   // PROCEDURE_INFO 를 보낸 assistant 메시지에만. 없으면 생략 또는 []
}
```

`cards`와 같은 방식으로 저장·재조회한다. 새로고침 후에도 ㉢ 카드가 그대로 보여야 한다.

## 3. `POST /api/ai/tasks` — action 추가

요청 바디 형식(`CreateTaskRequest`)은 그대로이고, `TaskAction` 유니온에 2개를 추가한다.

```ts
type TaskAction =
  | /* 기존 SELECT_HOSPITAL · RELAX · SET_SORT · SAVE_PROFILE */
  | { type: 'SELECT_TOPIC'; topic: ConsultTopic }
  | { type: 'FIND_BY_CONCERNS'; concerns: SkinConcern[] }
```

### 3-1. SELECT_TOPIC

```http
POST /api/ai/tasks
{
  "conversationId": "7c1e…",
  "message": "피부 고민으로 시술 찾기",
  "action": { "type": "SELECT_TOPIC", "topic": "SKIN_CONCERN" }
}
→ 202 { "taskId": "…" }
```

backend
- `conversations.mode = 'MAIN'`이 아니면 `409 INVALID_STATE_TRANSITION`.
- `topic`이 enum 밖이면 `400 VALIDATION_FAILED` (`details.fields[0].field = "action.topic"`).
- **task를 큐에 넣기 전에** `conversations.topic`을 저장한다. 다음 `GET` 결과가 바로 바뀌어야 한다.
- `message`는 기존처럼 user 메시지로 기록한다(화면의 오른쪽 말풍선). 화면 가운데 "'…' 상담을 시작했어요" 안내는 FE만 표시하고 저장하지 않는다.

agent (SSE)
- `SKIN_CONCERN`: 고민을 묻는 짧은 답변만 보낸다(`TOKEN…` → `DONE`). 도구 호출은 없다. 예: "어떤 피부 고민이 있으세요? 해당하는 걸 모두 골라주세요. 고른 고민과 관련된 시술 정보를 알려드려요."
- 나머지 주제: 그 주제에 맞게 첫 안내를 보낸다(필요하면 역질문). 주제는 이후 턴의 시스템 컨텍스트로 쓴다.

### 3-2. FIND_BY_CONCERNS

```http
POST /api/ai/tasks
{
  "conversationId": "7c1e…",
  "message": "기미·잡티, 모공",
  "action": { "type": "FIND_BY_CONCERNS", "concerns": ["PIGMENTATION", "PORES"] }
}
→ 202 { "taskId": "…" }
```

backend
- `concerns`가 1~7개이고 중복이 없고 모두 enum 값인지 검사한다. 아니면 `400 VALIDATION_FAILED` (`field = "action.concerns"`).
- `conversations.topic`이 `SKIN_CONCERN`이 아니어도 막지 않는다(칩 없이 "다른 고민 추가"로 바로 올 수 있음).

agent (SSE 순서)

```
STATUS        {"status":"RUNNING"}
TOOL_START    {"tool":"business_find_procedures_by_concern","label":"관련 시술 찾는 중…"}
TOOL_END      {"tool":"business_find_procedures_by_concern","ok":true}
PROCEDURE_INFO {"procedures":[ProcedureInfo, ...]}
TOKEN …       "관련 시술 2가지예요. 시간·가격은 등록된 병원 정보 기준이에요."
DONE          {"answer":"…","sources":[]}
```

- 매핑된 시술이 0건이면 `PROCEDURE_INFO`를 보내지 않고 안내 문구만 보낸 뒤 `DONE`.
- 답변에 시술 효과·적합 여부를 쓰지 않는다. 개수와 "등록된 정보 기준"이라는 안내만 쓴다.

## 4. SSE 이벤트 추가 — `PROCEDURE_INFO`

| 이벤트 | data | FE 처리 |
| --- | --- | --- |
| `PROCEDURE_INFO` | `{ "procedures": ProcedureInfo[] }` | `conversation.procedures`에 저장 → `DONE` 때 assistant 메시지에 붙여 카드 렌더 (`RESULT_CARDS`와 같은 방식) |

- 종료 이벤트가 아니다. 이 이벤트 뒤에 반드시 `DONE`(또는 `FAILED`)이 온다.
- `seq`/`Last-Event-ID` 규칙은 기존 이벤트와 같다.

## 5. 내부 API (business-mcp → backend)

agent 도구 `business_find_procedures_by_concern(concerns: list[str]) -> list[ProcedureInfo(snake_case)]`가 호출한다.

```http
GET /internal/procedures/by-concerns?concerns=PIGMENTATION&concerns=PORES
Accept-Language: ko
→ 200
[
  {
    "procedureCode": "PICO_TONING", "name": "피코토닝", "description": "…",
    "concerns": ["PIGMENTATION"], "durationMin": 20, "downtimeDays": 0,
    "minPriceKrw": 50000, "maxPriceKrw": 589000
  },
  {
    "procedureCode": "REJURAN", "name": "리쥬란 힐러", "description": "…",
    "concerns": ["PORES"], "durationMin": 40, "downtimeDays": 2,
    "minPriceKrw": 149000, "maxPriceKrw": 810000
  }
]
```

- 매핑·가격 집계는 **backend**가 한다. business-mcp는 그대로 전달만 한다(업무 규칙 복제 금지).
- MCP 도구 입출력은 snake_case (`procedure_code`, `min_price_krw` …).

## 6. DB (backend Flyway V2~V99)

```sql
ALTER TABLE app.conversations
  ADD COLUMN topic varchar(30)
  CHECK (topic IN ('SKIN_CONCERN','PROCEDURE_INFO','RECOVERY','HOSPITAL_SEARCH','HOSPITAL_COMPARE',
                   'COUNSELOR_CHAT','BOOK','MY_RESERVATIONS','CANCEL_RESERVATION'));

CREATE TABLE app.procedure_concerns (
  concern        varchar(30) NOT NULL
                 CHECK (concern IN ('PIGMENTATION','PORES','ACNE_SCAR','WRINKLE_FIRMNESS','TONE_TEXTURE','REDNESS','FACE_CONTOUR')),
  procedure_code varchar(40) NOT NULL REFERENCES app.procedures(code),
  sort_order     smallint    NOT NULL DEFAULT 0,
  PRIMARY KEY (concern, procedure_code)
);
```

매핑 seed는 `data/mock/generate.py`에 추가한 뒤 재생성하고 `validate.py`를 통과시킨다(JSON/SQL 직접 수정 금지). FE mock이 쓰는 초안:

| concern | procedure_code |
| --- | --- |
| PIGMENTATION | PICO_TONING |
| PORES | REJURAN |
| ACNE_SCAR | REJURAN |
| WRINKLE_FIRMNESS | ULTHERAPY, THERMAGE, FOREHEAD_BOTOX |
| TONE_TEXTURE | PICO_TONING, REJURAN |
| REDNESS | PICO_TONING |
| FACE_CONTOUR | SHURINK, JAW_BOTOX |

> 이 매핑은 의료 판단이 아니라 "관련 시술 정보 묶음"이다. 실제 값은 RAG 시술 가이드 문서 기준으로 담당자가 확정한다.

## 7. 확인이 필요한 것

1. **문구와 규칙 충돌**: Figma 섹션 제목과 빠른 답장 칩에 "시술 **추천**"이 있다. "AI는 추천하지 않는다" 규칙과 맞추려면 "시술 정보" 같은 문구로 바꾸는 게 좋을지 디자인과 확인이 필요하다. (FE는 지금 Figma 문구 그대로 넣음)
2. **NEW 배지**: "피부 고민으로 시술 찾기" 말고 "조건으로 병원 찾기"에도 붙어 있다. 의도한 건지 확인.
3. **"내 예약 / 예약 취소" 주제**: 지금은 다른 주제처럼 `SELECT_TOPIC`을 보내고 agent가 안내한다. 빠른 답장 "내 예약"은 `/reservations` 화면으로 바로 이동한다. agent가 예약 조회까지 처리할지 정해야 한다.
4. **`description` 다국어**: `app.procedures`에 `description_zh/ja`가 없다. 지금은 en으로 대체한다.
