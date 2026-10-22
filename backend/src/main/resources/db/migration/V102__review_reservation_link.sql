-- 고객 리뷰 작성: 리뷰가 어느 예약에 대한 것인지 연결 (예약 1건당 리뷰 1건)
-- seed 리뷰는 예약과 연결되지 않으므로 NULL 허용. UNIQUE 는 NULL 끼리는 겹쳐도 된다.
ALTER TABLE app.reviews ADD COLUMN IF NOT EXISTS reservation_id bigint REFERENCES app.reservations(id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_reviews_reservation ON app.reviews (reservation_id);
