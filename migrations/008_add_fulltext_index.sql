-- Migration: Add missing FULLTEXT index for hybrid search
-- This index is required for the MATCH(...) AGAINST(...) query in models/book_model.py

ALTER TABLE books ADD FULLTEXT idx_books_fulltext (title, author_name, description);
