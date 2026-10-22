-- 시술 사후관리 대화방: 확정 예약 1건당 대화 1개 (mode AFTERCARE).
-- 상담사 연결 중에는 HUMAN 으로 바뀌고, 상담이 끝나면 aftercare_rooms 에 있는 대화는 AFTERCARE 로 돌아간다.
ALTER TABLE app.conversations DROP CONSTRAINT conversations_mode_check;
ALTER TABLE app.conversations ADD CONSTRAINT conversations_mode_check
    CHECK (mode IN ('MAIN','HOSPITAL','HUMAN','AFTERCARE'));

CREATE TABLE app.aftercare_rooms (
    conversation_id uuid PRIMARY KEY REFERENCES app.conversations(id),
    reservation_id  bigint NOT NULL UNIQUE REFERENCES app.reservations(id),
    created_at      timestamptz NOT NULL DEFAULT now()
);
