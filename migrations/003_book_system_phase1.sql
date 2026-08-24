-- =====================================================================
-- Migration 003 — Book System Phase 1 (Data Model)
-- Idempotent: safe to run multiple times.
-- Scope approved by user (2026-08-17):
--   * books: is_physical, publisher, edition, publication_year
--   * categories: nullable faculty_id (department linkage for dependent
--     Department→Category selection, client + server enforced)
--   * resource_type: UNTOUCHED (full deprecation is a separate approved scope)
--   * downloads table: UNTOUCHED (historical records preserved)
-- =====================================================================

DELIMITER //

CREATE PROCEDURE IF NOT EXISTS _p1_apply()
BEGIN
  -- ------------------------------------------------------------
  -- 1) books: new availability + bibliographic columns
  -- ------------------------------------------------------------
  IF NOT EXISTS (
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'is_physical') THEN
    ALTER TABLE books ADD COLUMN is_physical TINYINT(1) NOT NULL DEFAULT 0
                      AFTER resource_type;
  END IF;

  IF NOT EXISTS (
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'publisher') THEN
    ALTER TABLE books ADD COLUMN publisher VARCHAR(150) NULL
                      AFTER author_id;
  END IF;

  IF NOT EXISTS (
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'edition') THEN
    ALTER TABLE books ADD COLUMN edition VARCHAR(50) NULL
                      AFTER publisher;
  END IF;

  IF NOT EXISTS (
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'publication_year') THEN
    ALTER TABLE books ADD COLUMN publication_year YEAR NULL
                      AFTER edition;
  END IF;

  -- ------------------------------------------------------------
  -- 2) Seed is_physical for existing rows
  --    Existing semantics: books with total_copies > 0 are borrowable
  --    (physical stock). Set is_physical=1 for them to preserve the
  --    current borrow/physical behaviour exactly. Books with no copies
  --    (digital-only entries, if any) stay is_physical=0.
  --    No data is lost: total_copies/available_copies remain the source
  --    of physical stock counts.
  -- ------------------------------------------------------------
  UPDATE books SET is_physical = 1 WHERE total_copies > 0;

  -- ------------------------------------------------------------
  -- 3) categories: department linkage (nullable)
  -- ------------------------------------------------------------
  IF NOT EXISTS (
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'categories' AND COLUMN_NAME = 'faculty_id') THEN
    ALTER TABLE categories ADD COLUMN faculty_id INT NULL
                           AFTER category_name;
    ALTER TABLE categories
      ADD CONSTRAINT fk_categories_faculty
      FOREIGN KEY (faculty_id) REFERENCES faculties (faculty_id)
      ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;

  -- Existing 5 categories intentionally LEFT UNASSIGNED (NULL = usable
  -- under any department) to avoid fabricating linkage data.
  -- Admins assign department linkage through the Category management UI
  -- in a later phase. Server-side enforcement treats NULL categories as
  -- valid for every department.
END //

DELIMITER ;

CALL _p1_apply();
DROP PROCEDURE _p1_apply;

-- Verification output (informational only)
SELECT CONCAT('books: ', COUNT(*), ' rows; is_physical seeded: ',
              SUM(is_physical)) AS books_summary FROM books;
SELECT CONCAT('categories: ', COUNT(*), ' rows; linked: ',
              SUM(faculty_id IS NOT NULL), ' / unassigned: ',
              SUM(faculty_id IS NULL)) AS categories_summary FROM categories;
