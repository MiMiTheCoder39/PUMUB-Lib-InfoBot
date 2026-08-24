-- Phase F migration: secure in-app password-reset token storage.
-- Schema addition approved in Phase A.
-- Storage notes:
--   * The raw token is NEVER stored — only its SHA-256 hash.
--   * One live token per account: creating a new token removes the old one.
--   * used_at records when a token was redeemed; tokens are deleted after use
--     or after expiry, so no plaintext or stale secrets accumulate.
CREATE TABLE IF NOT EXISTS `reset_tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `token_hash` varchar(64) NOT NULL COMMENT 'SHA-256 of the raw 32-byte token',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` timestamp NOT NULL COMMENT '15 minutes after created_at',
  `used_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_reset` (`user_id`),
  KEY `idx_token_hash` (`token_hash`),
  CONSTRAINT `fk_reset_users` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
