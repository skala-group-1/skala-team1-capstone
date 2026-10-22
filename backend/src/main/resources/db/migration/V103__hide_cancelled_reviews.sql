-- 예약이 취소되면 그 예약으로 쓴 리뷰는 숨긴다 (삭제하지 않음). 목록 쿼리(CatalogService.reviews)와 같은 조건.
-- 컬럼 이름·순서는 schema.sql(V1) 의 뷰와 같아야 CREATE OR REPLACE 가 된다.
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
    AND NOT EXISTS (SELECT 1 FROM app.reservations x WHERE x.id = r.reservation_id AND x.status = 'CANCELLED')
GROUP BY h.id;
