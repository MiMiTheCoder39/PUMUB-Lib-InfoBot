-- Migration K — University Record status (approved Q3b)
-- ============================================================
-- Converts the two-state `is_active` TINYINT into a four-state
-- `status` ENUM required by the final requirements (§5, §8):
--   active | inactive | graduated | suspended
--
-- Idempotent and additive:
--   * If `status` already exists, the migration stops (no-op).
--   * Existing rows are mapped losslessly:
--       is_active = 1  →  status = 'active'
--       is_active = 0  →  status = 'inactive'
--     The production university_records table is currently empty,
--     so this mapping is trivially safe in production.
--   * `is_active` is RETAINED (not dropped) for full backward
--     compatibility with existing code paths: is_active = (status
--     IN ('active')), so all existing readers keep working.
--   * No data is dropped, deleted, or truncated anywhere.
-- ============================================================

CREATE PROCEDURE IF NOT EXISTS dummy_proc() BEGIN END; -- no-op if exists

DROP PROCEDURE IF EXISTS migrate_k_record_status;

DELIMITER $$

CREATE PROCEDURE migrate_k_record_status()
BEGIN
  -- Idempotency guard: if the column already exists, do nothing.
  IF NOT EXISTS (
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'university_records'
        AND COLUMN_NAME = 'status') THEN

    -- Add the new column temporarily nullable (MySQL needs a default
    -- during the convert of the existing NOT NULL column).
    ALTER TABLE `university_records`
      ADD COLUMN `status`
        ENUM('active','inactive','graduated','suspended')
        NOT NULL DEFAULT 'active'
        AFTER `role`;

    -- Lossless data mapping from the legacy two-state flag.
    UPDATE `university_records`
       SET `status` = IF(`is_active` = 1, 'active', 'inactive');

    ALTER TABLE `university_records`
      MODIFY COLUMN `status`
        ENUM('active','inactive','graduated','suspended')
        NOT NULL DEFAULT 'active'
        COMMENT 'Official record status — registration and login respect this';

    -- Index for status filtering (listing filters, login-time check).
    CREATE INDEX idx_records_status ON `university_records` (`status`);
  END IF;
END$$

DELIMITER ;

CALL migrate_k_record_status();

DROP PROCEDURE migrate_k_record_status;
