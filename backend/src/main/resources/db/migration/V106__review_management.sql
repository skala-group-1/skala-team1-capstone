-- 병원 관리자 리뷰 관리 (H5-D): 병원 답글(리뷰당 1개) + 답글 번역 + 리뷰 숨김.
-- 숨김은 삭제가 아니다. 숨긴 리뷰는 고객 목록·통계·에이전트 조회에서 빠지고, 병원 관리자 화면에서 다시 보이게 할 수 있다.
ALTER TABLE app.reviews
    ADD COLUMN hidden_at     timestamptz,
    ADD COLUMN hidden_by     bigint REFERENCES app.users(id),
    ADD COLUMN hidden_reason varchar(20) CHECK (hidden_reason IN ('PRIVACY','ABUSE','FALSE_INFO','SPAM','OTHER')),
    ADD COLUMN hidden_detail varchar(300);

CREATE TABLE app.review_replies (
    review_id  bigint PRIMARY KEY REFERENCES app.reviews(id) ON DELETE CASCADE,
    author_id  bigint NOT NULL REFERENCES app.users(id),
    lang       varchar(5) NOT NULL DEFAULT 'ko' CHECK (lang IN ('ko','en','zh','ja')),
    content    text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 답글 번역 (translator 가 review.translated 로 돌려줌, kind = REPLY). 답글을 고치면 지우고 다시 받는다
CREATE TABLE app.review_reply_translations (
    review_id bigint NOT NULL REFERENCES app.review_replies(review_id) ON DELETE CASCADE,
    lang      varchar(5) NOT NULL CHECK (lang IN ('ko','en','zh','ja')),
    content   text NOT NULL,
    PRIMARY KEY (review_id, lang)
);

-- 통계 뷰에서도 숨긴 리뷰를 뺀다 (컬럼 이름·순서는 V103 과 같아야 CREATE OR REPLACE 가 된다)
CREATE OR REPLACE VIEW app.hospital_review_stats AS
SELECT h.id                                              AS hospital_id,
       count(r.id)                                       AS review_count,
       round(avg(r.rating)::numeric, 2)                  AS avg_rating,
       count(r.id) FILTER (WHERE r.age_group = '20s')    AS age_20s_count,
       count(r.id) FILTER (WHERE r.age_group = '30s')    AS age_30s_count,
       count(r.id) FILTER (WHERE r.age_group = '40s')    AS age_40s_count,
       count(r.id) FILTER (WHERE r.age_group = '50s')    AS age_50s_count,
       count(r.id) FILTER (WHERE r.gender = 'F')         AS female_count,
       count(r.id) FILTER (WHERE r.gender = 'M')         AS male_count,
       count(r.id) FILTER (WHERE r.gender = 'X')         AS other_gender_count
FROM app.hospitals h
LEFT JOIN app.reviews r ON r.hospital_id = h.id
    AND r.hidden_at IS NULL
    AND NOT EXISTS (SELECT 1 FROM app.reservations x WHERE x.id = r.reservation_id AND x.status = 'CANCELLED')
GROUP BY h.id;
