-- 12 공통 계약서·06 문서와 mock schema.sql 의 차이 보정 (backend 소유 마이그레이션)
-- 1) ReservationStatus 에 EXPIRED 추가 (30분 홀드 만료 스케줄러)
-- 2) reservations.price_option_id 추가 (CreateReservationRequest.priceOptionId)
ALTER TABLE app.reservations DROP CONSTRAINT IF EXISTS reservations_status_check;
ALTER TABLE app.reservations
    ADD CONSTRAINT reservations_status_check
    CHECK (status IN ('PENDING','CONFIRMED','REJECTED','EXPIRED','CANCELLED'));

ALTER TABLE app.reservations
    ADD COLUMN IF NOT EXISTS price_option_id bigint REFERENCES app.price_options(id);
