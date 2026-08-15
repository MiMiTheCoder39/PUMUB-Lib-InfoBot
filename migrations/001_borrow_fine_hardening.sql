-- Borrow/Fine hardening migration for digital_library_db
-- Run only after reviewing the preflight queries against production.
-- This migration does not drop tables or delete rows.

USE digital_library_db;

-- Preflight: resolve duplicate final fines before adding the unique key.
-- Expected result: zero rows.
SELECT borrow_id, COUNT(*) AS fine_count
FROM fines
GROUP BY borrow_id
HAVING COUNT(*) > 1;

-- Add payment method storage if it is not already present.
SET @sql = IF(
  EXISTS(
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'fines' AND COLUMN_NAME = 'payment_method'
  ),
  'SELECT 1',
  'ALTER TABLE fines ADD COLUMN payment_method VARCHAR(32) NULL AFTER paid_at'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Enforce one final fine per borrow after the preflight is confirmed clean.
SET @sql = IF(
  EXISTS(
    SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'fines' AND INDEX_NAME = 'uq_fines_borrow'
  ),
  'SELECT 1',
  'ALTER TABLE fines ADD UNIQUE KEY uq_fines_borrow (borrow_id)'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Store the borrow identity on notifications so scheduled reminders can be deduplicated.
SET @sql = IF(
  EXISTS(
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notifications' AND COLUMN_NAME = 'borrow_id'
  ),
  'SELECT 1',
  'ALTER TABLE notifications ADD COLUMN borrow_id INT NULL AFTER user_id'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS(
    SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notifications' AND INDEX_NAME = 'idx_notifications_borrow_type'
  ),
  'SELECT 1',
  'ALTER TABLE notifications ADD INDEX idx_notifications_borrow_type (borrow_id, type, created_at)'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Expand the enum to match existing borrow/fine notification code.
ALTER TABLE notifications
  MODIFY COLUMN type ENUM(
    'new_book','announcement','due_reminder','system',
    'borrow_request','borrow_approved','borrow_issued','borrow_returned',
    'borrow_overdue','fine_added','fine_paid'
  ) NOT NULL DEFAULT 'system';

-- Postflight checks.
SHOW COLUMNS FROM fines LIKE 'payment_method';
SHOW INDEX FROM fines WHERE Key_name = 'uq_fines_borrow';
SHOW COLUMNS FROM notifications LIKE 'borrow_id';
SHOW COLUMNS FROM notifications LIKE 'type';
