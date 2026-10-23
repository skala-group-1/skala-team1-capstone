-- 병원 관리자의 상담사 관리 (H4-D): 상담 언어 · 새 문의 받기 · 활성 여부 · 마지막 로그인.
-- 고객·운영자에게도 컬럼은 생기지만 쓰지 않는다 (active 는 모든 계정의 로그인 차단에 쓰인다).
ALTER TABLE app.users
    ADD COLUMN languages     text[]      NOT NULL DEFAULT ARRAY['ko']::text[],
    ADD COLUMN accepting_new boolean     NOT NULL DEFAULT true,
    ADD COLUMN active        boolean     NOT NULL DEFAULT true,
    ADD COLUMN last_login_at timestamptz;

ALTER TABLE app.users ADD CONSTRAINT users_languages_check
    CHECK (languages <@ ARRAY['ko','en','zh','ja']::text[] AND cardinality(languages) > 0);

-- 기존 상담사의 상담 언어는 소속 병원의 상담 가능 언어로 채운다
UPDATE app.users u
SET languages = h.supported_languages
FROM app.hospitals h
WHERE u.role = 'COUNSELOR' AND u.hospital_id = h.id
  AND h.supported_languages <@ ARRAY['ko','en','zh','ja']::text[] AND cardinality(h.supported_languages) > 0;
