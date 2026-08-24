-- Phase 1: Add FULLTEXT indexes for Hybrid Retrieval
1. -- Supporting keyword-based relevance scoring on metadata.

ALTER TABLE `books` ADD FULLTEXT INDEX `idx_books_fulltext` (`title`, `author_name`, `description`);
ALTER TABLE `books` ADD FULLTEXT INDEX `idx_books_title_isbn` (`title`, `isbn`);
