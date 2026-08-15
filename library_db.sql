-- ============================================================
--  Digital Library Management System
--  Database: digital_library_db
--  Engine: MySQL (XAMPP / phpMyAdmin)
--
--  HOW TO IMPORT:
--   1. XAMPP Control Panel -> Start Apache + MySQL
--   2. http://localhost/phpmyadmin
--   3. "New" -> Database name: digital_library_db -> Create
--      (or just run this file directly; it creates the DB itself)
--   4. Click "Import" tab -> choose this file -> Go
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";

CREATE DATABASE IF NOT EXISTS digital_library_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE digital_library_db;

-- ============================================================
-- 1. FACULTIES
-- ============================================================
DROP TABLE IF EXISTS faculties;
CREATE TABLE faculties (
    faculty_id   INT AUTO_INCREMENT PRIMARY KEY,
    faculty_name VARCHAR(150) NOT NULL,
    department   VARCHAR(150) DEFAULT NULL,   -- e.g. CS, CT, Civil, EP, EC, Mechanical
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- 2. ROLES (Admin / Student) — kept simple as ENUM on users,
--    table not required but role lookup view-friendly if needed
-- ============================================================

-- ============================================================
-- 3. USERS  (Admin + Student share this table, differentiated by role)
-- ============================================================
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,
    student_id     VARCHAR(50) DEFAULT NULL UNIQUE,   -- NULL for admin accounts
    name           VARCHAR(150) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    username       VARCHAR(100) NOT NULL UNIQUE,
    password       VARCHAR(255) NOT NULL,             -- hashed (werkzeug.security)
    role           ENUM('admin','student','teacher') NOT NULL DEFAULT 'student',
    faculty_id     INT DEFAULT NULL,
    profile_image  VARCHAR(255) DEFAULT NULL,
    is_active      TINYINT(1) NOT NULL DEFAULT 1,      -- Activate/Deactivate Account
    last_login     TIMESTAMP NULL DEFAULT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_faculty FOREIGN KEY (faculty_id)
        REFERENCES faculties(faculty_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 4. CATEGORIES
-- ============================================================
DROP TABLE IF EXISTS categories;
CREATE TABLE categories (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,        -- Programming, Networking, Database...
    description   VARCHAR(255) DEFAULT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- 5. AUTHORS
-- ============================================================
DROP TABLE IF EXISTS authors;
CREATE TABLE authors (
    author_id   INT AUTO_INCREMENT PRIMARY KEY,
    author_name VARCHAR(150) NOT NULL,
    bio         TEXT DEFAULT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- 6. BOOKS  (covers e-book / thesis / journal / research paper via resource_type)
-- ============================================================
DROP TABLE IF EXISTS books;
CREATE TABLE books (
    book_id        INT AUTO_INCREMENT PRIMARY KEY,
    title          VARCHAR(255) NOT NULL,
    isbn           VARCHAR(20) DEFAULT NULL,
    author_name    VARCHAR(255) DEFAULT NULL,
    author_id      INT DEFAULT NULL,
    category_id    INT DEFAULT NULL,
    faculty_id     INT DEFAULT NULL,
    description    TEXT DEFAULT NULL,
    resource_type  ENUM('book','ebook','thesis','journal','research_paper','reference_book','teachers_guide') NOT NULL DEFAULT 'book',
    pdf_file       VARCHAR(255) NOT NULL,              -- stored filename in static/uploads/books
    cover_image    VARCHAR(255) DEFAULT NULL,           -- stored filename in static/uploads/covers
    qr_code        VARCHAR(255) DEFAULT NULL,           -- stored filename in static/uploads/qrcodes
    total_copies   INT NOT NULL DEFAULT 0,              -- for physical borrow tracking
    available_copies INT NOT NULL DEFAULT 0,
    publish_date   DATE DEFAULT NULL,
    view_count     INT NOT NULL DEFAULT 0,              -- Most Viewed Books report
    download_count INT NOT NULL DEFAULT 0,              -- Most Downloaded Books report
    upload_date    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_books_author   FOREIGN KEY (author_id)   REFERENCES authors(author_id)     ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_books_category FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_books_faculty  FOREIGN KEY (faculty_id)  REFERENCES faculties(faculty_id)   ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_books_title (title)
) ENGINE=InnoDB;

-- ============================================================
-- 7. DOWNLOADS (Download History)
-- ============================================================
DROP TABLE IF EXISTS downloads;
CREATE TABLE downloads (
    download_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    book_id       INT NOT NULL,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_downloads_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_downloads_book FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 8. READ HISTORY (View History — separate from downloads)
-- ============================================================
DROP TABLE IF EXISTS read_history;
CREATE TABLE read_history (
    history_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    book_id     INT NOT NULL,
    read_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_readhistory_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_readhistory_book FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 9. BOOKMARKS / FAVORITES
-- ============================================================
DROP TABLE IF EXISTS bookmarks;
CREATE TABLE bookmarks (
    bookmark_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    book_id     INT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bookmarks_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_bookmarks_book FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE KEY uq_user_book (user_id, book_id)   -- same book ကို တစ်ကြိမ်ထက်ပိုပြီး bookmark မလုပ်နိုင်အောင်
) ENGINE=InnoDB;

-- ============================================================
-- 10. ANNOUNCEMENTS
-- ============================================================
DROP TABLE IF EXISTS announcements;
CREATE TABLE announcements (
    announcement_id INT AUTO_INCREMENT PRIMARY KEY,
    title            VARCHAR(255) NOT NULL,
    content          TEXT NOT NULL,
    created_by       INT DEFAULT NULL,            -- admin user_id
    date             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_announcements_admin FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 11. BORROW MANAGEMENT (Physical Books)
-- ============================================================
DROP TABLE IF EXISTS borrow_requests;
CREATE TABLE borrow_requests (
    borrow_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    book_id       INT NOT NULL,
    request_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approve_date  TIMESTAMP NULL DEFAULT NULL,
    due_date      DATE DEFAULT NULL,
    return_date   TIMESTAMP NULL DEFAULT NULL,
    status        ENUM('pending','approved','borrowed','overdue','returned','rejected') NOT NULL DEFAULT 'pending',
    borrow_id_code VARCHAR(20) DEFAULT NULL UNIQUE,
    borrow_qr      VARCHAR(255) DEFAULT NULL,
    borrowed_date  TIMESTAMP NULL DEFAULT NULL,
    issued_date    TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_borrow_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_borrow_book FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 12. FINE MANAGEMENT (linked to borrow_requests)
-- ============================================================
DROP TABLE IF EXISTS fines;
CREATE TABLE fines (
    fine_id     INT AUTO_INCREMENT PRIMARY KEY,
    borrow_id   INT NOT NULL,
    user_id     INT NOT NULL,
    amount      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    reason      VARCHAR(255) DEFAULT 'Late Return',
    is_paid     TINYINT(1) NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at     TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_fines_borrow FOREIGN KEY (borrow_id) REFERENCES borrow_requests(borrow_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_fines_user   FOREIGN KEY (user_id)   REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 13. NOTIFICATIONS (New Books, Announcements, Due-date reminders)
-- ============================================================
DROP TABLE IF EXISTS notifications;
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL,
    title            VARCHAR(255) NOT NULL,
    message          TEXT NOT NULL,
    type             ENUM('new_book','announcement','due_reminder','system') NOT NULL DEFAULT 'system',
    is_read          TINYINT(1) NOT NULL DEFAULT 0,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- SEED DATA (initial records so the app is testable immediately)
-- ============================================================

-- Faculties
INSERT INTO faculties (faculty_name, department) VALUES
('Faculty of Computing', 'Computer Science (CS)'),
('Faculty of Computing', 'Computer Technology (CT)'),
('Faculty of Engineering', 'Civil'),
('Faculty of Engineering', 'EP'),
('Faculty of Engineering', 'EC'),
('Faculty of Engineering', 'Mechanical');

-- Categories
INSERT INTO categories (category_name, description) VALUES
('Programming', 'Programming languages and software development'),
('Networking', 'Computer networks and protocols'),
('Database', 'Database systems and management'),
('Mathematics', 'Mathematics and applied math'),
('English', 'English language and literature');

-- Authors
INSERT INTO authors (author_name) VALUES
('Thomas H. Cormen'),
('Andrew S. Tanenbaum'),
('Raghu Ramakrishnan'),
('James Stewart');

-- Admin account
-- Login: username = admin | password = admin123
-- (hash generated via werkzeug.security.generate_password_hash)
INSERT INTO users (student_id, name, email, username, password, role, faculty_id, is_active)
VALUES (NULL, 'System Administrator', 'admin@library.edu.mm', 'admin',
        'scrypt:32768:8:1$LKmUFyYURpc6utQs$a516cd1866ed7d7c5518b91fa3db1b30f2ad1fc904e743db681da228f8e8227ae8376a9ed6102aebff320d4f46da2bc7fd81abf808263e53534b1d57a4f5939f',
        'admin', NULL, 1);

-- Sample student account
-- Login: username = student01 | password = student123
INSERT INTO users (student_id, name, email, username, password, role, faculty_id, is_active)
VALUES ('CS-2024-001', 'Test Student', 'student@library.edu.mm', 'student01',
        'scrypt:32768:8:1$xzaxxAk51Ii4XRif$33acc0e5e3347fab8de6eb29ba77d6e4f22142874133958550c4fa080d0b24fdacb64bdc27492f69bc514fb32d88b831e78daaa2411cd56b17540d0d70e4015b',
        'student', 1, 1);

-- Sample announcement
INSERT INTO announcements (title, content, created_by)
VALUES ('Welcome to the Digital Library', 'The Digital Library Management System is now live for all students and staff.', 1);

