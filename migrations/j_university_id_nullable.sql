-- Migration J — university_records.university_id becomes NULLABLE
-- Teacher records carry no university ID (students keep MUB-XXXX).
-- The existing UNIQUE KEY uniq_records_id safely permits any number of NULLs
-- in MySQL/InnoDB, so two teachers with NULL id never collide.
-- Idempotent: re-running is harmless.
-- (Phase H/I security architecture unchanged; no data deleted.)

ALTER TABLE `university_records`
  MODIFY COLUMN `university_id` VARCHAR(50) NULL
    COMMENT 'Official university ID (e.g. MUB-1350). NULL for teachers.';
