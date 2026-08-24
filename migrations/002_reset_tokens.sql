-- Migration 002 — Secure password-reset token table (Phase F).
-- Stores single-use, 15-minute-expiry reset tokens hashed with scrypt
-- (identical family to Phase B/C password hashing).
-- If the table already exists the migration is a no-op (idempotent).

CREATE TABLE IF NOT EXISTS `reset_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `token_hash` varchar(255) NOT NULL COMMENT 'scrypt:32768:8: hash of the raw token',
  `expires_at` timestamp NOT NULL,
  `used` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_reset_user` (`user_id`),
  CONSTRAINT `fk_reset_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
COMMENT 'Phase F — secure in-app password reset tokens';
