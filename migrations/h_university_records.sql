-- ============================================================
-- Phase H — Official University Records master table
-- ============================================================
-- This table is the authoritative source of truth for registration
-- identity verification. It is SEPARATE from the `users` table
-- (which stores login accounts). Existing user accounts are NOT
-- migrated into this table and remain intact.
--
-- Contents are managed by the university registrar / library admin
-- (official enrollment records), NOT by applicants.
--
-- Fields are limited to what the project genuinely requires:
--   university email, university ID, full name, faculty reference,
--   department (free text, where the faculties reference is not
--   enough), year of study, role, active/inactive status.
-- ============================================================

CREATE TABLE IF NOT EXISTS university_records (
  record_id        INT(11)      NOT NULL AUTO_INCREMENT,
  university_email VARCHAR(150) NOT NULL COMMENT 'Official university email (exact)',
  university_id    VARCHAR(50)  NOT NULL COMMENT 'Official university ID (e.g. MUB-1350, CS-2024-001, T-001)',
  full_name        VARCHAR(150) NOT NULL COMMENT 'Official full name as recorded by the university',
  faculty_id       INT(11)      NULL     DEFAULT NULL COMMENT 'FK -> faculties (where applicable)',
  department       VARCHAR(150) NULL     DEFAULT NULL COMMENT 'Department free text (where applicable, when not covered by faculties)',
  year             VARCHAR(10)  NULL     DEFAULT NULL COMMENT 'Year of study (e.g. 1, 2, 3, 4)',
  role             ENUM('student','teacher') NOT NULL DEFAULT 'student' COMMENT 'Official role',
  is_active        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '1 = eligible to register / 0 = ineligible',
  created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (record_id),
  UNIQUE KEY uniq_records_email (university_email),
  UNIQUE KEY uniq_records_id (university_id),
  KEY idx_records_active (is_active),
  CONSTRAINT fk_records_faculty
    FOREIGN KEY (faculty_id) REFERENCES faculties (faculty_id)
    ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
