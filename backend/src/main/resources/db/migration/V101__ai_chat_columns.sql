-- 16 Backend API 상세 명세 11장: AI 작업·채팅에 필요한 컬럼 추가
-- 1) conversations.conditions : 에이전트가 정리한 검색 조건(CONDITIONS 이벤트) 저장, 병원 대화창에 복사
ALTER TABLE app.conversations ADD COLUMN IF NOT EXISTS conditions jsonb;

-- 2) ai_tasks : 요청 action, 결과 카드(대화 기록 재구성용), 마지막으로 받은 이벤트 번호(중복 무시용)
ALTER TABLE app.ai_tasks ADD COLUMN IF NOT EXISTS action jsonb;
ALTER TABLE app.ai_tasks ADD COLUMN IF NOT EXISTS result_cards jsonb;
ALTER TABLE app.ai_tasks ADD COLUMN IF NOT EXISTS last_seq integer NOT NULL DEFAULT 0;
ALTER TABLE app.ai_tasks ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_ai_tasks_user ON app.ai_tasks (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_status ON app.ai_tasks (status, updated_at);

-- 3) chat_messages : 클라이언트 메시지 ID(같은 메시지 재전송 시 중복 저장 방지), flags 는 배열이 기본
ALTER TABLE app.chat_messages ADD COLUMN IF NOT EXISTS client_msg_id uuid;
CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_messages_client_msg
    ON app.chat_messages (consultation_id, client_msg_id) WHERE client_msg_id IS NOT NULL;
ALTER TABLE app.chat_messages ALTER COLUMN flags SET DEFAULT '[]'::jsonb;

-- 4) 예약 만료 스케줄러·대시보드 조회용 인덱스
CREATE INDEX IF NOT EXISTS idx_reservations_pending_hold ON app.reservations (hold_expires_at) WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON app.notifications (user_id) WHERE read_at IS NULL;
