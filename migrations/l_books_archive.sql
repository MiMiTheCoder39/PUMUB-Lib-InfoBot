-- ============================================================
-- Migration l_books_archive — Books safe-delete lifecycle
-- ============================================================
-- Adds books.is_archived (soft-archive flag). Archived books are
-- hidden from catalog / search / recommendations and managed by
-- the admin through Archive -> Restore -> dependency-checked
-- Permanent Delete.
--
-- Idempotent: safe to run multiple times.
-- Local sandbox order: run on sandbox first -> verify -> regression.
-- Production: APPLY LATER, after owner approval. DO NOT run here.
-- ============================================================

DROP PROCEDURE IF EXISTS _l_add_books_archive_column;

DELIMITER $$
CREATE PROCEDURE _l_add_books_archive_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'is_archived'
  ) THEN
    ALTER TABLE books
      ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0 AFTER is_physical,
      ADD INDEX idx_books_archived (is_archived);
    SELECT 'l_books_archive: is_archived column ADDED' AS result;
  ELSE
    SELECT 'l_books_archive: is_archived column already exists (no-op)' AS result;
  END IF;
END$$
DELIMITER ;

CALL _l_add_books_archive_column();
DROP PROCEDURE IF EXISTS _l_add_books_archive_column;
