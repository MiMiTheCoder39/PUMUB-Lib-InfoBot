-- =====================================================================
-- Migration 004 — PDF Optional (Book System Phase 1)
-- Idempotent: safe to run multiple times.
-- Scope approved by user (2026-08-17):
--   * books.pdf_file becomes NULL-able so Physical-Only books can exist.
--   * No other column is touched; downloads table untouched (Phase 3
--     decides its fate after a dependency audit).
-- No data is modified or deleted.
-- =====================================================================

DELIMITER //

CREATE PROCEDURE IF NOT EXISTS _p4_apply()
BEGIN
  IF EXISTS (
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'pdf_file'
        AND IS_NULLABLE = 'NO') THEN
    ALTER TABLE books MODIFY COLUMN pdf_file VARCHAR(255) NULL;
  END IF;
END //

DELIMITER ;

CALL _p4_apply();
DROP PROCEDURE _p4_apply;

-- Verification output (informational only)
SELECT CONCAT('books: ', COUNT(*), ' rows; with pdf: ',
              SUM(pdf_file IS NOT NULL), ' / without pdf: ',
              SUM(pdf_file IS NULL)) AS books_pdf_summary FROM books;
SELECT CONCAT('is_physical: ', SUM(is_physical = 1),
              ' / digital-only: ', SUM(is_physical = 0 AND pdf_file IS NOT NULL),
              ' / physical-only: ', SUM(is_physical = 1 AND pdf_file IS NULL),
              ' / hybrid: ', SUM(is_physical = 1 AND pdf_file IS NOT NULL))
  AS books_state_summary FROM books;
