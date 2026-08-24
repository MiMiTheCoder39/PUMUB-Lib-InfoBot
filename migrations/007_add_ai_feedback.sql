-- Phase 4C-B.3: AI Feedback & Statistics
-- Additive tables for production hardening and quality metrics.

-- Table for storing granular user feedback on AI responses
CREATE TABLE IF NOT EXISTS `ai_feedback` (
  `feedback_id` int(11) NOT NULL AUTO_INCREMENT,
  `history_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `score` int(1) NOT NULL COMMENT '1 for positive, -1 for negative',
  `comment` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`feedback_id`),
  KEY `idx_feedback_user` (`user_id`),
  KEY `idx_feedback_history` (`history_id`),
  CONSTRAINT `fk_feedback_history` FOREIGN KEY (`history_id`) REFERENCES `chat_history` (`history_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_feedback_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing aggregated, non-PII feedback statistics
CREATE TABLE IF NOT EXISTS `feedback_stats` (
  `stat_id` int(11) NOT NULL AUTO_INCREMENT,
  `book_id` int(11) DEFAULT NULL,
  `faculty` varchar(100) DEFAULT NULL,
  `positive_count` int(11) NOT NULL DEFAULT 0,
  `negative_count` int(11) NOT NULL DEFAULT 0,
  `last_updated` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`stat_id`),
  UNIQUE KEY `idx_stat_book_faculty` (`book_id`, `faculty`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
