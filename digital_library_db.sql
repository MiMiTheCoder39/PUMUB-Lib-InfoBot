-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Aug 14, 2026 at 04:02 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `digital_library_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `announcements`
--

CREATE TABLE `announcements` (
  `announcement_id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `content` text NOT NULL,
  `created_by` int(11) DEFAULT NULL,
  `date` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `announcements`
--

INSERT INTO `announcements` (`announcement_id`, `title`, `content`, `created_by`, `date`) VALUES
(1, 'Welcome to the Digital Library', 'The Digital Library Management System is now live for all students and staff.', 1, '2026-08-09 17:54:27'),
(3, 'အထွေထွေစည်းမျဉ်းများ', '-Digital Library ကို စည်းကမ်းတကျနှင့် တာဝန်ယူမှုရှိစွာ အသုံးပြုရမည်။\r\n-မိမိ၏ Account အချက်အလက်များကို အခြားသူများအား မျှဝေခြင်းမပြုရ။\r\n-စာအုပ်များကို ပညာရေးနှင့် လေ့လာရေးအတွက်သာ အသုံးပြုရမည်။\r\n-မူပိုင်ခွင့်ရှိသော စာအုပ်များကို ခွင့်ပြုချက်မရှိဘဲ ဖြန့်ဝေခြင်း၊ ပြန်လည်တင်ခြင်း မပြုရ။\r\n-စာကြည့်တိုက် စီမံခန့်ခွဲသူ၏ သတ်မှတ်ချက်များကို လိုက်နာရမည်။', 1, '2026-08-12 17:05:25'),
(4, 'စာအုပ်ငှားရမ်းခြင်း', '-Physical Book များကို Digital Library မှတစ်ဆင့် Borrow Request ပြုလုပ်ရမည်။\r\n-Admin မှ ခွင့်ပြုပြီးမှသာ စာအုပ်ကို ငှားရမ်းနိုင်မည်။\r\n-သတ်မှတ်ထားသော Due Date မတိုင်မီ စာအုပ်ကို ပြန်အပ်ရမည်။\r\n-သတ်မှတ်ရက်ကျော်လွန်ပါက Library Policy အရ ဒဏ်ကြေးပေးဆောင်ရနိုင်သည်။\r\n-ငှားရမ်းထားသော စာအုပ်များကို ဂရုတစိုက် ထိန်းသိမ်းအသုံးပြုရမည်။', 1, '2026-08-12 17:06:42'),
(5, 'ကျောင်းသားများအတွက်(Student Rules)', '-မိမိ၏ ကိုယ်ပိုင် Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-စာအုပ်မငှားမီ သတ်မှတ်ထားသော ပြန်အပ်ရမည့်ရက်ကို စစ်ဆေးရမည်။', 1, '2026-08-12 17:07:41'),
(6, 'ဆရာ/ဆရာမများအတွက်(Teacher Rules)', '-မိမိ၏ Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-သတ်မှတ်ထားသော ငှားရမ်းကာလအတွင်း စာအုပ်များကို ပြန်လည်အပ်နှံရမည်။', 1, '2026-08-12 17:08:39'),
(7, 'အရေးကြီးချက်', '⚠️ အရေးကြီးချက် စာကြည့်တိုက် စည်းမျဉ်းများကို မလိုက်နာပါက Library Service များ အသုံးပြုခွင့်ကို ကန့်သတ်ခြင်း သိုမဟုတ် Admin မှ သတ်မှတ်ထားသော အခြားအရေးယူမှုများ ပြုလုပ်နိုင်ပါသည်။', 1, '2026-08-12 17:09:13');

-- --------------------------------------------------------

--
-- Table structure for table `authors`
--

CREATE TABLE `authors` (
  `author_id` int(11) NOT NULL,
  `author_name` varchar(150) NOT NULL,
  `bio` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `bookmarks`
--

CREATE TABLE `bookmarks` (
  `bookmark_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `book_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `bookmarks`
--

INSERT INTO `bookmarks` (`bookmark_id`, `user_id`, `book_id`, `created_at`) VALUES
(2, 2, 2, '2026-08-09 19:08:11'),
(4, 7, 1, '2026-08-12 16:53:18'),
(5, 7, 3, '2026-08-12 16:53:31'),
(6, 9, 2, '2026-08-12 16:54:27'),
(7, 10, 3, '2026-08-12 16:55:49'),
(8, 11, 4, '2026-08-12 16:56:51'),
(9, 12, 1, '2026-08-12 16:57:20');

-- --------------------------------------------------------

--
-- Table structure for table `books`
--

CREATE TABLE `books` (
  `book_id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `isbn` varchar(20) DEFAULT NULL,
  `author_name` varchar(255) DEFAULT NULL,
  `author_id` int(11) DEFAULT NULL,
  `category_id` int(11) DEFAULT NULL,
  `faculty_id` int(11) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `resource_type` enum('book','ebook','thesis','journal','research_paper','reference_book','teachers_guide') NOT NULL DEFAULT 'book',
  `pdf_file` varchar(255) NOT NULL,
  `cover_image` varchar(255) DEFAULT NULL,
  `qr_code` varchar(255) DEFAULT NULL,
  `total_copies` int(11) NOT NULL DEFAULT 0,
  `available_copies` int(11) NOT NULL DEFAULT 0,
  `publish_date` date DEFAULT NULL,
  `view_count` int(11) NOT NULL DEFAULT 0,
  `download_count` int(11) NOT NULL DEFAULT 0,
  `upload_date` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `books`
--

INSERT INTO `books` (`book_id`, `title`, `isbn`, `author_name`, `author_id`, `category_id`, `faculty_id`, `description`, `resource_type`, `pdf_file`, `cover_image`, `qr_code`, `total_copies`, `available_copies`, `publish_date`, `view_count`, `download_count`, `upload_date`, `updated_at`) VALUES
(1, 'The Essentials of Java', '978-93-81068-63-2', 'Arunesh Goyal', NULL, 1, 1, 'For improve Java Programming Language Skills.', 'ebook', '1d3b7a3d7fef43f6a2abc0b47e10c8c2.pdf', 'e341c06dc3de4324becd661c46ddc434.jpg', 'qr_book_1.png', 18, 13, '2026-08-10', 31, 0, '2026-08-09 18:12:53', '2026-08-14 08:31:03'),
(2, 'Database System Concepts (7th Edition)', '978-0078022159', 'Abraham Silberschatz, Henry F. Korth, S. Sudarshan', NULL, 3, 7, 'For database', 'ebook', 'bb707760568e4779ad6da74d244f4155.pdf', '077c9426249248d4a5ebeb1113bdfbaa.jpg', 'qr_book_2.png', 10, 9, '2026-08-10', 18, 0, '2026-08-09 18:19:25', '2026-08-14 08:16:33'),
(3, 'Cambridge English Prepare! Level 4 Workbook (Second Edition).', '978-1-009-02296-5', 'Gareth Jones', NULL, 5, 9, 'for improve you english skill.', 'ebook', '1fd3d96e66c043b787bbf58749e4cafa.pdf', 'e533067f67f345b3aae02c772cf8b922.jpg', 'qr_book_3.png', 12, 9, '2026-08-10', 18, 1, '2026-08-09 18:23:48', '2026-08-14 08:27:40'),
(4, 'Artificial Intelligence Programming with Python: From Zero to Hero.', '978-1119820864', 'Perry Xiao', NULL, 1, 1, 'Zero to Hero Python developer', 'ebook', '4abec6af3f7947849e379c09d435d6a6.pdf', 'a346ae55327d47b5a8a49b4ba9a24e92.jpg', 'qr_book_4.png', 10, 8, '2026-08-10', 16, 2, '2026-08-09 18:28:20', '2026-08-13 04:06:39'),
(5, 'Information security and IT Risk Management', '978-1119820864', 'Manish Agrawal', NULL, 3, 8, 'Data information and It Risk', 'ebook', '332c8ac09b6c43c69f6c7e21e79d6911.pdf', '975370c4e20a4a5584402d18251c3a59.jpg', 'qr_book_5.png', 11, 7, '2026-08-10', 20, 3, '2026-08-09 18:34:22', '2026-08-13 04:06:49');

-- --------------------------------------------------------

--
-- Table structure for table `borrow_requests`
--

CREATE TABLE `borrow_requests` (
  `borrow_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `book_id` int(11) NOT NULL,
  `request_date` timestamp NOT NULL DEFAULT current_timestamp(),
  `approve_date` timestamp NULL DEFAULT NULL,
  `due_date` date DEFAULT NULL,
  `return_date` timestamp NULL DEFAULT NULL,
  `status` enum('pending','approved','borrowed','overdue','returned','rejected') NOT NULL DEFAULT 'pending',
  `borrow_id_code` varchar(20) DEFAULT NULL,
  `borrow_qr` varchar(255) DEFAULT NULL,
  `borrowed_date` timestamp NULL DEFAULT NULL,
  `issued_date` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `borrow_requests`
--

INSERT INTO `borrow_requests` (`borrow_id`, `user_id`, `book_id`, `request_date`, `approve_date`, `due_date`, `return_date`, `status`, `borrow_id_code`, `borrow_qr`, `borrowed_date`, `issued_date`) VALUES
(4, 2, 2, '2026-08-09 19:08:27', '2026-08-09 19:09:06', '2026-08-19', NULL, 'borrowed', 'BR-2026-0005', 'qr_borrow_BR-2026-0005.png', '2026-08-09 17:30:00', '2026-08-09 19:09:28'),
(6, 2, 1, '2026-08-11 14:31:03', '2026-08-11 14:31:31', '2026-08-12', NULL, 'overdue', 'BR-2026-0007', 'qr_borrow_BR-2026-0007.png', '2026-08-10 17:30:00', '2026-08-11 16:04:34'),
(7, 2, 5, '2026-08-11 16:02:20', '2026-08-11 16:03:18', '2026-08-12', NULL, 'overdue', 'BR-2026-0004', 'qr_borrow_BR-2026-0004.png', '2026-08-10 17:30:00', '2026-08-11 16:04:47'),
(8, 6, 1, '2026-08-12 11:27:06', '2026-08-12 16:20:35', '2026-08-13', NULL, 'overdue', 'BR-2026-184467440742', 'qr_borrow_BR-2026-184467440742.png', '2026-08-11 17:30:00', '2026-08-12 16:49:55'),
(9, 6, 5, '2026-08-12 11:28:33', '2026-08-12 16:20:25', '2026-08-13', NULL, 'overdue', 'BR-2026-184467440741', 'qr_borrow_BR-2026-184467440741.png', '2026-08-11 17:30:00', '2026-08-12 16:50:26'),
(10, 7, 1, '2026-08-12 11:29:25', '2026-08-12 16:20:13', '2026-08-13', NULL, 'overdue', 'BR-2026-184467440740', 'qr_borrow_BR-2026-184467440740.png', '2026-08-11 17:30:00', '2026-08-12 16:50:17'),
(11, 7, 3, '2026-08-12 11:29:37', '2026-08-12 16:20:03', '2026-08-13', NULL, 'overdue', 'BR-2026-184467440739', 'qr_borrow_BR-2026-184467440739.png', '2026-08-11 17:30:00', '2026-08-12 16:50:09'),
(12, 8, 4, '2026-08-12 11:30:05', '2026-08-12 16:19:58', '2026-08-13', NULL, 'overdue', 'BR-2026-184467440738', 'qr_borrow_BR-2026-184467440738.png', '2026-08-11 17:30:00', '2026-08-12 16:50:02'),
(13, 8, 5, '2026-08-12 11:30:14', '2026-08-12 14:46:24', '2026-08-13', NULL, 'overdue', 'BR-2026-184467440737', 'qr_borrow_BR-2026-18446744073709551613.png', '2026-08-11 17:30:00', '2026-08-12 16:47:51'),
(14, 9, 1, '2026-08-12 11:30:39', '2026-08-12 11:31:02', '2026-08-13', NULL, 'overdue', 'BR-2026-0011', 'qr_borrow_BR-2026-0011.png', '2026-08-11 17:30:00', '2026-08-12 16:47:38'),
(15, 10, 3, '2026-08-12 16:55:54', '2026-08-12 16:58:22', '2026-08-26', '2026-08-13 04:05:52', 'returned', 'BR-2026-184467440743', 'qr_borrow_BR-2026-184467440743.png', '2026-08-11 17:30:00', '2026-08-12 16:58:31'),
(16, 12, 1, '2026-08-12 16:59:10', '2026-08-12 16:59:30', '2026-08-14', '2026-08-13 04:02:22', 'returned', 'BR-2026-184467440744', 'qr_borrow_BR-2026-184467440744.png', '2026-08-11 17:30:00', '2026-08-12 16:59:41'),
(17, 13, 3, '2026-08-14 08:23:03', '2026-08-14 08:23:35', '2026-08-17', NULL, 'borrowed', 'BR-2026-184467440745', 'qr_borrow_BR-2026-184467440745.png', '2026-08-13 17:30:00', '2026-08-14 08:27:40'),
(18, 13, 1, '2026-08-14 08:28:09', '2026-08-14 08:28:49', '2026-08-19', NULL, 'borrowed', 'BR-2026-184467440746', 'qr_borrow_BR-2026-184467440746.png', '2026-08-13 17:30:00', '2026-08-14 08:31:03');

-- --------------------------------------------------------

--
-- Table structure for table `categories`
--

CREATE TABLE `categories` (
  `category_id` int(11) NOT NULL,
  `category_name` varchar(100) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `categories`
--

INSERT INTO `categories` (`category_id`, `category_name`, `description`, `created_at`) VALUES
(1, 'Programming', 'Programming languages and software development', '2026-08-09 17:54:27'),
(2, 'Networking', 'Computer networks and protocols', '2026-08-09 17:54:27'),
(3, 'Database', 'Database systems and management', '2026-08-09 17:54:27'),
(4, 'Mathematics', 'Mathematics and applied math', '2026-08-09 17:54:27'),
(5, 'English', 'English language and literature', '2026-08-09 17:54:27');

-- --------------------------------------------------------

--
-- Table structure for table `downloads`
--

CREATE TABLE `downloads` (
  `download_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `book_id` int(11) NOT NULL,
  `download_date` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `downloads`
--

INSERT INTO `downloads` (`download_id`, `user_id`, `book_id`, `download_date`) VALUES
(3, 2, 5, '2026-08-11 16:02:12'),
(4, 6, 5, '2026-08-12 11:28:35'),
(5, 7, 3, '2026-08-12 16:53:37'),
(6, 8, 5, '2026-08-12 16:55:12');

-- --------------------------------------------------------

--
-- Table structure for table `faculties`
--

CREATE TABLE `faculties` (
  `faculty_id` int(11) NOT NULL,
  `faculty_name` varchar(150) NOT NULL,
  `department` varchar(150) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `faculties`
--

INSERT INTO `faculties` (`faculty_id`, `faculty_name`, `department`, `created_at`) VALUES
(1, 'Faculty of Computing', 'Computer Science (CS)', '2026-08-09 17:54:27'),
(2, 'Faculty of Computing', 'Computer Technology (CT)', '2026-08-09 17:54:27'),
(3, 'Faculty of Engineering', 'Civil', '2026-08-09 17:54:27'),
(4, 'Faculty of Engineering', 'EP', '2026-08-09 17:54:27'),
(5, 'Faculty of Engineering', 'EC', '2026-08-09 17:54:27'),
(6, 'Faculty of Engineering', 'Mechanical', '2026-08-09 17:54:27'),
(7, 'Faculty of Computing', 'Information Science (IS)', '2026-08-09 18:16:06'),
(8, 'Faculty of Computing', 'Information Technology Supporting and Maintenance', '2026-08-09 18:16:24'),
(9, 'Supporting Subjects', 'English', '2026-08-09 18:16:32'),
(10, 'Faculty of Computing', 'Physics', '2026-08-09 18:16:42');

-- --------------------------------------------------------

--
-- Table structure for table `fines`
--

CREATE TABLE `fines` (
  `fine_id` int(11) NOT NULL,
  `borrow_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `amount` decimal(10,2) NOT NULL DEFAULT 0.00,
  `reason` varchar(255) DEFAULT 'Late Return',
  `is_paid` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `paid_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `notifications`
--

CREATE TABLE `notifications` (
  `notification_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `type` enum('new_book','announcement','due_reminder','system') NOT NULL DEFAULT 'system',
  `is_read` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `notifications`
--

INSERT INTO `notifications` (`notification_id`, `user_id`, `title`, `message`, `type`, `is_read`, `created_at`) VALUES
(1, 2, '???? New Book Added: The Essentials of Java', 'Library ထဲသို့ \"The Essentials of Java\" စာအုပ်အသစ် ထည့်သွင်းပြီးပါပြီ။', 'new_book', 1, '2026-08-09 18:12:53'),
(2, 2, '???? New Book Added: Database System Concepts (7th Edition)', 'Library ထဲသို့ \"Database System Concepts (7th Edition)\" စာအုပ်အသစ် ထည့်သွင်းပြီးပါပြီ။', 'new_book', 1, '2026-08-09 18:19:25'),
(3, 2, '???? New Book Added: Cambridge English Prepare! Level 4 Workbook (Second Edition).', 'Library ထဲသို့ \"Cambridge English Prepare! Level 4 Workbook (Second Edition).\" စာအုပ်အသစ် ထည့်သွင်းပြီးပါပြီ။', 'new_book', 1, '2026-08-09 18:23:48'),
(4, 2, '???? New Book Added: Artificial Intelligence Programming with Python: From Zero to Hero.', 'Library ထဲသို့ \"Artificial Intelligence Programming with Python: From Zero to Hero.\" စာအုပ်အသစ် ထည့်သွင်းပြီးပါပြီ။', 'new_book', 1, '2026-08-09 18:28:20'),
(5, 2, '???? New Book Added: Information security and IT Risk Management', 'Library ထဲသို့ \"Information security and IT Risk Management\" စာအုပ်အသစ် ထည့်သွင်းပြီးပါပြီ။', 'new_book', 1, '2026-08-09 18:34:22'),
(12, 2, '✅ Borrow Request Approved — BR-2026-0005', 'မင်္ဂလာပါ Test Student!\n\n\"Database System Concepts (7th Edition)\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-0005\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-09 19:09:06'),
(13, 2, '???? Book Issued — Database System Concepts (7th Edition)', 'မင်္ဂလာပါ Test Student!\n\n\"Database System Concepts (7th Edition)\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-0005\n???? Borrow Date: 2026-08-10\n⏰ Due Date   : 2026-08-19\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-09 19:09:28'),
(17, 2, '???? Announcement: Library rules', 'For student\r\nFor teacher', 'announcement', 1, '2026-08-10 03:16:19'),
(19, 2, '✅ Borrow Request Approved — BR-2026-0007', 'မင်္ဂလာပါ Test Student!\n\n\"The Essentials of Java\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-0007\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-11 14:31:31'),
(20, 2, '✅ Borrow Request Approved — BR-2026-0004', 'မင်္ဂလာပါ Test Student!\n\n\"Information security and IT Risk Management\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-0004\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-11 16:03:18'),
(21, 2, '???? Book Issued — The Essentials of Java', 'မင်္ဂလာပါ Test Student!\n\n\"The Essentials of Java\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-0007\n???? Borrow Date: 2026-08-11\n⏰ Due Date   : 2026-08-12\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-11 16:04:34'),
(22, 2, '???? Book Issued — Information security and IT Risk Management', 'မင်္ဂလာပါ Test Student!\n\n\"Information security and IT Risk Management\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-0004\n???? Borrow Date: 2026-08-11\n⏰ Due Date   : 2026-08-12\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-11 16:04:47'),
(23, 9, '✅ Borrow Request Approved — BR-2026-0011', 'မင်္ဂလာပါ Mg Htet Myat Naing!\n\n\"The Essentials of Java\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-0011\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-12 11:31:02'),
(24, 8, '✅ Borrow Request Approved — BR-2026-18446744073709551613', 'မင်္ဂလာပါ Mg Shein Wai Khant!\n\n\"Information security and IT Risk Management\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-18446744073709551613\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 0, '2026-08-12 14:46:24'),
(25, 8, '✅ Borrow Request Approved — BR-2026-184467440738', 'မင်္ဂလာပါ Mg Shein Wai Khant!\n\n\"Artificial Intelligence Programming with Python: From Zero to Hero.\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440738\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 0, '2026-08-12 16:19:58'),
(26, 7, '✅ Borrow Request Approved — BR-2026-184467440739', 'မင်္ဂလာပါ Ma Su Myat Noe!\n\n\"Cambridge English Prepare! Level 4 Workbook (Second Edition).\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440739\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-12 16:20:03'),
(27, 7, '✅ Borrow Request Approved — BR-2026-184467440740', 'မင်္ဂလာပါ Ma Su Myat Noe!\n\n\"The Essentials of Java\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440740\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-12 16:20:13'),
(28, 6, '✅ Borrow Request Approved — BR-2026-184467440741', 'မင်္ဂလာပါ Ma Aye Myat Khaing!\n\n\"Information security and IT Risk Management\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440741\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-12 16:20:25'),
(29, 6, '✅ Borrow Request Approved — BR-2026-184467440742', 'မင်္ဂလာပါ Ma Aye Myat Khaing!\n\n\"The Essentials of Java\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440742\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-12 16:20:35'),
(30, 9, '???? Book Issued — The Essentials of Java', 'မင်္ဂလာပါ Mg Htet Myat Naing!\n\n\"The Essentials of Java\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-0011\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-13\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-12 16:47:38'),
(31, 8, '???? Book Issued — Information security and IT Risk Management', 'မင်္ဂလာပါ Mg Shein Wai Khant!\n\n\"Information security and IT Risk Management\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440737\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-13\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 0, '2026-08-12 16:47:51'),
(32, 6, '???? Book Issued — The Essentials of Java', 'မင်္ဂလာပါ Ma Aye Myat Khaing!\n\n\"The Essentials of Java\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440742\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-13\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-12 16:49:55'),
(33, 8, '???? Book Issued — Artificial Intelligence Programming with Python: From Zero to Hero.', 'မင်္ဂလာပါ Mg Shein Wai Khant!\n\n\"Artificial Intelligence Programming with Python: From Zero to Hero.\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440738\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-13\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 0, '2026-08-12 16:50:02'),
(34, 7, '???? Book Issued — Cambridge English Prepare! Level 4 Workbook (Second Edition).', 'မင်္ဂလာပါ Ma Su Myat Noe!\n\n\"Cambridge English Prepare! Level 4 Workbook (Second Edition).\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440739\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-13\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-12 16:50:09'),
(35, 7, '???? Book Issued — The Essentials of Java', 'မင်္ဂလာပါ Ma Su Myat Noe!\n\n\"The Essentials of Java\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440740\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-13\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-12 16:50:17'),
(36, 6, '???? Book Issued — Information security and IT Risk Management', 'မင်္ဂလာပါ Ma Aye Myat Khaing!\n\n\"Information security and IT Risk Management\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440741\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-13\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-12 16:50:26'),
(37, 10, '✅ Borrow Request Approved — BR-2026-184467440743', 'မင်္ဂလာပါ Ma Zin Thawdar Phyo!\n\n\"Cambridge English Prepare! Level 4 Workbook (Second Edition).\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440743\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 0, '2026-08-12 16:58:22'),
(38, 10, '???? Book Issued — Cambridge English Prepare! Level 4 Workbook (Second Edition).', 'မင်္ဂလာပါ Ma Zin Thawdar Phyo!\n\n\"Cambridge English Prepare! Level 4 Workbook (Second Edition).\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440743\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-26\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 0, '2026-08-12 16:58:31'),
(39, 12, '✅ Borrow Request Approved — BR-2026-184467440744', 'မင်္ဂလာပါ Tr. Hsu Mon Kyi!\n\n\"The Essentials of Java\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440744\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 0, '2026-08-12 16:59:30'),
(40, 12, '???? Book Issued — The Essentials of Java', 'မင်္ဂလာပါ Tr. Hsu Mon Kyi!\n\n\"The Essentials of Java\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440744\n???? Borrow Date: 2026-08-12\n⏰ Due Date   : 2026-08-14\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 0, '2026-08-12 16:59:41'),
(41, 2, '???? Announcement: ???? အထွေထွေစည်းမျဉ်းများ', '-Digital Library ကို စည်းကမ်းတကျနှင့် တာဝန်ယူမှုရှိစွာ အသုံးပြုရမည်။\r\n-မိမိ၏ Account အချက်အလက်များကို အခြားသူများအား မျှဝေခြင်းမပြုရ။\r\n-စာအုပ်များကို ပညာရေးနှင့် လေ့လာရေးအတွက်သာ အသုံးပြုရမည်။\r\n-မူပိုင', 'announcement', 1, '2026-08-12 17:05:25'),
(42, 6, '???? Announcement: ???? အထွေထွေစည်းမျဉ်းများ', '-Digital Library ကို စည်းကမ်းတကျနှင့် တာဝန်ယူမှုရှိစွာ အသုံးပြုရမည်။\r\n-မိမိ၏ Account အချက်အလက်များကို အခြားသူများအား မျှဝေခြင်းမပြုရ။\r\n-စာအုပ်များကို ပညာရေးနှင့် လေ့လာရေးအတွက်သာ အသုံးပြုရမည်။\r\n-မူပိုင', 'announcement', 1, '2026-08-12 17:05:25'),
(43, 7, '???? Announcement: ???? အထွေထွေစည်းမျဉ်းများ', '-Digital Library ကို စည်းကမ်းတကျနှင့် တာဝန်ယူမှုရှိစွာ အသုံးပြုရမည်။\r\n-မိမိ၏ Account အချက်အလက်များကို အခြားသူများအား မျှဝေခြင်းမပြုရ။\r\n-စာအုပ်များကို ပညာရေးနှင့် လေ့လာရေးအတွက်သာ အသုံးပြုရမည်။\r\n-မူပိုင', 'announcement', 0, '2026-08-12 17:05:25'),
(44, 8, '???? Announcement: ???? အထွေထွေစည်းမျဉ်းများ', '-Digital Library ကို စည်းကမ်းတကျနှင့် တာဝန်ယူမှုရှိစွာ အသုံးပြုရမည်။\r\n-မိမိ၏ Account အချက်အလက်များကို အခြားသူများအား မျှဝေခြင်းမပြုရ။\r\n-စာအုပ်များကို ပညာရေးနှင့် လေ့လာရေးအတွက်သာ အသုံးပြုရမည်။\r\n-မူပိုင', 'announcement', 0, '2026-08-12 17:05:25'),
(45, 9, '???? Announcement: ???? အထွေထွေစည်းမျဉ်းများ', '-Digital Library ကို စည်းကမ်းတကျနှင့် တာဝန်ယူမှုရှိစွာ အသုံးပြုရမည်။\r\n-မိမိ၏ Account အချက်အလက်များကို အခြားသူများအား မျှဝေခြင်းမပြုရ။\r\n-စာအုပ်များကို ပညာရေးနှင့် လေ့လာရေးအတွက်သာ အသုံးပြုရမည်။\r\n-မူပိုင', 'announcement', 1, '2026-08-12 17:05:25'),
(46, 10, '???? Announcement: ???? အထွေထွေစည်းမျဉ်းများ', '-Digital Library ကို စည်းကမ်းတကျနှင့် တာဝန်ယူမှုရှိစွာ အသုံးပြုရမည်။\r\n-မိမိ၏ Account အချက်အလက်များကို အခြားသူများအား မျှဝေခြင်းမပြုရ။\r\n-စာအုပ်များကို ပညာရေးနှင့် လေ့လာရေးအတွက်သာ အသုံးပြုရမည်။\r\n-မူပိုင', 'announcement', 0, '2026-08-12 17:05:25'),
(47, 2, '???? Announcement: ???? စာအုပ်ငှားရမ်းခြင်း', '-Physical Book များကို Digital Library မှတစ်ဆင့် Borrow Request ပြုလုပ်ရမည်။\r\n-Admin မှ ခွင့်ပြုပြီးမှသာ စာအုပ်ကို ငှားရမ်းနိုင်မည်။\r\n-သတ်မှတ်ထားသော Due Date မတိုင်မီ စာအုပ်ကို ပြန်အပ်ရမည်။\r\n-သတ်မှတ်ရ', 'announcement', 1, '2026-08-12 17:06:42'),
(48, 6, '???? Announcement: ???? စာအုပ်ငှားရမ်းခြင်း', '-Physical Book များကို Digital Library မှတစ်ဆင့် Borrow Request ပြုလုပ်ရမည်။\r\n-Admin မှ ခွင့်ပြုပြီးမှသာ စာအုပ်ကို ငှားရမ်းနိုင်မည်။\r\n-သတ်မှတ်ထားသော Due Date မတိုင်မီ စာအုပ်ကို ပြန်အပ်ရမည်။\r\n-သတ်မှတ်ရ', 'announcement', 1, '2026-08-12 17:06:42'),
(49, 7, '???? Announcement: ???? စာအုပ်ငှားရမ်းခြင်း', '-Physical Book များကို Digital Library မှတစ်ဆင့် Borrow Request ပြုလုပ်ရမည်။\r\n-Admin မှ ခွင့်ပြုပြီးမှသာ စာအုပ်ကို ငှားရမ်းနိုင်မည်။\r\n-သတ်မှတ်ထားသော Due Date မတိုင်မီ စာအုပ်ကို ပြန်အပ်ရမည်။\r\n-သတ်မှတ်ရ', 'announcement', 0, '2026-08-12 17:06:42'),
(50, 8, '???? Announcement: ???? စာအုပ်ငှားရမ်းခြင်း', '-Physical Book များကို Digital Library မှတစ်ဆင့် Borrow Request ပြုလုပ်ရမည်။\r\n-Admin မှ ခွင့်ပြုပြီးမှသာ စာအုပ်ကို ငှားရမ်းနိုင်မည်။\r\n-သတ်မှတ်ထားသော Due Date မတိုင်မီ စာအုပ်ကို ပြန်အပ်ရမည်။\r\n-သတ်မှတ်ရ', 'announcement', 0, '2026-08-12 17:06:42'),
(51, 9, '???? Announcement: ???? စာအုပ်ငှားရမ်းခြင်း', '-Physical Book များကို Digital Library မှတစ်ဆင့် Borrow Request ပြုလုပ်ရမည်။\r\n-Admin မှ ခွင့်ပြုပြီးမှသာ စာအုပ်ကို ငှားရမ်းနိုင်မည်။\r\n-သတ်မှတ်ထားသော Due Date မတိုင်မီ စာအုပ်ကို ပြန်အပ်ရမည်။\r\n-သတ်မှတ်ရ', 'announcement', 1, '2026-08-12 17:06:42'),
(52, 10, '???? Announcement: ???? စာအုပ်ငှားရမ်းခြင်း', '-Physical Book များကို Digital Library မှတစ်ဆင့် Borrow Request ပြုလုပ်ရမည်။\r\n-Admin မှ ခွင့်ပြုပြီးမှသာ စာအုပ်ကို ငှားရမ်းနိုင်မည်။\r\n-သတ်မှတ်ထားသော Due Date မတိုင်မီ စာအုပ်ကို ပြန်အပ်ရမည်။\r\n-သတ်မှတ်ရ', 'announcement', 0, '2026-08-12 17:06:42'),
(53, 2, '???? Announcement: ????‍???? ကျောင်းသားများအတွက်(Student Rules)', '-မိမိ၏ ကိုယ်ပိုင် Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-စာအုပ်မငှားမီ သတ်မှတ်ထားသော ပြန်အပ်ရမည့်ရက်ကို စစ်', 'announcement', 1, '2026-08-12 17:07:41'),
(54, 6, '???? Announcement: ????‍???? ကျောင်းသားများအတွက်(Student Rules)', '-မိမိ၏ ကိုယ်ပိုင် Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-စာအုပ်မငှားမီ သတ်မှတ်ထားသော ပြန်အပ်ရမည့်ရက်ကို စစ်', 'announcement', 1, '2026-08-12 17:07:41'),
(55, 7, '???? Announcement: ????‍???? ကျောင်းသားများအတွက်(Student Rules)', '-မိမိ၏ ကိုယ်ပိုင် Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-စာအုပ်မငှားမီ သတ်မှတ်ထားသော ပြန်အပ်ရမည့်ရက်ကို စစ်', 'announcement', 0, '2026-08-12 17:07:41'),
(56, 8, '???? Announcement: ????‍???? ကျောင်းသားများအတွက်(Student Rules)', '-မိမိ၏ ကိုယ်ပိုင် Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-စာအုပ်မငှားမီ သတ်မှတ်ထားသော ပြန်အပ်ရမည့်ရက်ကို စစ်', 'announcement', 0, '2026-08-12 17:07:41'),
(57, 9, '???? Announcement: ????‍???? ကျောင်းသားများအတွက်(Student Rules)', '-မိမိ၏ ကိုယ်ပိုင် Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-စာအုပ်မငှားမီ သတ်မှတ်ထားသော ပြန်အပ်ရမည့်ရက်ကို စစ်', 'announcement', 1, '2026-08-12 17:07:41'),
(58, 10, '???? Announcement: ????‍???? ကျောင်းသားများအတွက်(Student Rules)', '-မိမိ၏ ကိုယ်ပိုင် Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-စာအုပ်မငှားမီ သတ်မှတ်ထားသော ပြန်အပ်ရမည့်ရက်ကို စစ်', 'announcement', 0, '2026-08-12 17:07:41'),
(59, 2, '???? Announcement: ????‍???? ဆရာ/ဆရာမများအတွက်(Teacher Rules)', '-မိမိ၏ Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-သတ်မှတ်ထားသော ငှားရမ်းကာလအတွင်း စာအုပ်များကို ပြန်လည်အပ်နှံရမ', 'announcement', 1, '2026-08-12 17:08:39'),
(60, 6, '???? Announcement: ????‍???? ဆရာ/ဆရာမများအတွက်(Teacher Rules)', '-မိမိ၏ Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-သတ်မှတ်ထားသော ငှားရမ်းကာလအတွင်း စာအုပ်များကို ပြန်လည်အပ်နှံရမ', 'announcement', 1, '2026-08-12 17:08:39'),
(61, 7, '???? Announcement: ????‍???? ဆရာ/ဆရာမများအတွက်(Teacher Rules)', '-မိမိ၏ Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-သတ်မှတ်ထားသော ငှားရမ်းကာလအတွင်း စာအုပ်များကို ပြန်လည်အပ်နှံရမ', 'announcement', 0, '2026-08-12 17:08:39'),
(62, 8, '???? Announcement: ????‍???? ဆရာ/ဆရာမများအတွက်(Teacher Rules)', '-မိမိ၏ Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-သတ်မှတ်ထားသော ငှားရမ်းကာလအတွင်း စာအုပ်များကို ပြန်လည်အပ်နှံရမ', 'announcement', 0, '2026-08-12 17:08:39'),
(63, 9, '???? Announcement: ????‍???? ဆရာ/ဆရာမများအတွက်(Teacher Rules)', '-မိမိ၏ Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-သတ်မှတ်ထားသော ငှားရမ်းကာလအတွင်း စာအုပ်များကို ပြန်လည်အပ်နှံရမ', 'announcement', 1, '2026-08-12 17:08:39'),
(64, 10, '???? Announcement: ????‍???? ဆရာ/ဆရာမများအတွက်(Teacher Rules)', '-မိမိ၏ Registered Account ဖြင့်သာ Library Service များကို အသုံးပြုရမည်။\r\n-မိမိ Account ဖြင့် ငှားရမ်းထားသော စာအုပ်များအတွက် တာဝန်ယူရမည်။\r\n-သတ်မှတ်ထားသော ငှားရမ်းကာလအတွင်း စာအုပ်များကို ပြန်လည်အပ်နှံရမ', 'announcement', 0, '2026-08-12 17:08:39'),
(65, 2, '???? Announcement: အရေးကြီးချက်', '⚠️ အရေးကြီးချက် စာကြည့်တိုက် စည်းမျဉ်းများကို မလိုက်နာပါက Library Service များ အသုံးပြုခွင့်ကို ကန့်သတ်ခြင်း သိုမဟုတ် Admin မှ သတ်မှတ်ထားသော အခြားအရေးယူမှုများ ပြုလုပ်နိုင်ပါသည်။', 'announcement', 1, '2026-08-12 17:09:13'),
(66, 6, '???? Announcement: အရေးကြီးချက်', '⚠️ အရေးကြီးချက် စာကြည့်တိုက် စည်းမျဉ်းများကို မလိုက်နာပါက Library Service များ အသုံးပြုခွင့်ကို ကန့်သတ်ခြင်း သိုမဟုတ် Admin မှ သတ်မှတ်ထားသော အခြားအရေးယူမှုများ ပြုလုပ်နိုင်ပါသည်။', 'announcement', 1, '2026-08-12 17:09:13'),
(67, 7, '???? Announcement: အရေးကြီးချက်', '⚠️ အရေးကြီးချက် စာကြည့်တိုက် စည်းမျဉ်းများကို မလိုက်နာပါက Library Service များ အသုံးပြုခွင့်ကို ကန့်သတ်ခြင်း သိုမဟုတ် Admin မှ သတ်မှတ်ထားသော အခြားအရေးယူမှုများ ပြုလုပ်နိုင်ပါသည်။', 'announcement', 0, '2026-08-12 17:09:13'),
(68, 8, '???? Announcement: အရေးကြီးချက်', '⚠️ အရေးကြီးချက် စာကြည့်တိုက် စည်းမျဉ်းများကို မလိုက်နာပါက Library Service များ အသုံးပြုခွင့်ကို ကန့်သတ်ခြင်း သိုမဟုတ် Admin မှ သတ်မှတ်ထားသော အခြားအရေးယူမှုများ ပြုလုပ်နိုင်ပါသည်။', 'announcement', 0, '2026-08-12 17:09:13'),
(69, 9, '???? Announcement: အရေးကြီးချက်', '⚠️ အရေးကြီးချက် စာကြည့်တိုက် စည်းမျဉ်းများကို မလိုက်နာပါက Library Service များ အသုံးပြုခွင့်ကို ကန့်သတ်ခြင်း သိုမဟုတ် Admin မှ သတ်မှတ်ထားသော အခြားအရေးယူမှုများ ပြုလုပ်နိုင်ပါသည်။', 'announcement', 1, '2026-08-12 17:09:13'),
(70, 10, '???? Announcement: အရေးကြီးချက်', '⚠️ အရေးကြီးချက် စာကြည့်တိုက် စည်းမျဉ်းများကို မလိုက်နာပါက Library Service များ အသုံးပြုခွင့်ကို ကန့်သတ်ခြင်း သိုမဟုတ် Admin မှ သတ်မှတ်ထားသော အခြားအရေးယူမှုများ ပြုလုပ်နိုင်ပါသည်။', 'announcement', 0, '2026-08-12 17:09:13'),
(71, 12, '✅ Book Returned — The Essentials of Java', 'မင်္ဂလာပါ Tr. Hsu Mon Kyi!\n\n\"The Essentials of Java\" (BR-2026-184467440744) ကို ပြန်အပ်ပြီးကြောင်း မှတ်တမ်းတင်ပြီးပါပြီ။\nငှားယူသောကြောင့် ကျေးဇူးတင်ပါသည်။', '', 0, '2026-08-13 04:02:22'),
(72, 10, '✅ Book Returned — Cambridge English Prepare! Level 4 Workbook (Second Edition).', 'မင်္ဂလာပါ Ma Zin Thawdar Phyo!\n\n\"Cambridge English Prepare! Level 4 Workbook (Second Edition).\" (BR-2026-184467440743) ကို ပြန်အပ်ပြီးကြောင်း မှတ်တမ်းတင်ပြီးပါပြီ။\nငှားယူသောကြောင့် ကျေးဇူးတင်ပါသည်။', '', 0, '2026-08-13 04:05:52'),
(73, 13, '✅ Borrow Request Approved — BR-2026-184467440745', 'မင်္ဂလာပါ Ye Kaung Chit!\n\n\"Cambridge English Prepare! Level 4 Workbook (Second Edition).\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440745\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-14 08:23:35'),
(74, 13, '???? Book Issued — Cambridge English Prepare! Level 4 Workbook (Second Edition).', 'မင်္ဂလာပါ Ye Kaung Chit!\n\n\"Cambridge English Prepare! Level 4 Workbook (Second Edition).\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440745\n???? Borrow Date: 2026-08-14\n⏰ Due Date   : 2026-08-17\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 1, '2026-08-14 08:27:40'),
(75, 13, '✅ Borrow Request Approved — BR-2026-184467440746', 'မင်္ဂလာပါ Ye Kaung Chit!\n\n\"The Essentials of Java\" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n???? သင်၏ Borrow ID: BR-2026-184467440746\n\nLibrary သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\nAdmin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။', '', 1, '2026-08-14 08:28:49'),
(76, 13, '???? Book Issued — The Essentials of Java', 'မင်္ဂလာပါ Ye Kaung Chit!\n\n\"The Essentials of Java\" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n???? Borrow ID  : BR-2026-184467440746\n???? Borrow Date: 2026-08-14\n⏰ Due Date   : 2026-08-19\n\nကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\nနောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။', '', 0, '2026-08-14 08:31:03');

-- --------------------------------------------------------

--
-- Table structure for table `read_history`
--

CREATE TABLE `read_history` (
  `history_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `book_id` int(11) NOT NULL,
  `read_date` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `read_history`
--

INSERT INTO `read_history` (`history_id`, `user_id`, `book_id`, `read_date`) VALUES
(4, 2, 1, '2026-08-11 14:30:52'),
(5, 2, 1, '2026-08-11 15:28:28'),
(6, 2, 5, '2026-08-11 16:02:07'),
(7, 6, 1, '2026-08-12 11:27:11'),
(8, 6, 2, '2026-08-12 11:27:29'),
(9, 6, 1, '2026-08-12 11:27:53'),
(10, 6, 4, '2026-08-12 11:28:08'),
(11, 6, 5, '2026-08-12 11:28:36'),
(12, 7, 1, '2026-08-12 11:29:17'),
(13, 7, 1, '2026-08-12 16:53:20'),
(14, 7, 3, '2026-08-12 16:53:33'),
(15, 9, 2, '2026-08-12 16:54:29'),
(16, 8, 5, '2026-08-12 16:55:08'),
(17, 10, 3, '2026-08-12 16:55:56'),
(18, 11, 4, '2026-08-12 16:56:46'),
(19, 12, 1, '2026-08-12 16:57:22'),
(20, 2, 1, '2026-08-13 04:10:12'),
(21, 2, 2, '2026-08-14 08:16:29'),
(22, 13, 3, '2026-08-14 08:22:52');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` int(11) NOT NULL,
  `student_id` varchar(50) DEFAULT NULL,
  `name` varchar(150) NOT NULL,
  `email` varchar(150) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` enum('admin','student','teacher') NOT NULL DEFAULT 'student',
  `faculty_id` int(11) DEFAULT NULL,
  `profile_image` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `last_login` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_id`, `student_id`, `name`, `email`, `username`, `password`, `role`, `faculty_id`, `profile_image`, `is_active`, `last_login`, `created_at`, `updated_at`) VALUES
(1, NULL, 'System Administrator', 'admin@library.edu.mm', 'admin', 'scrypt:32768:8:1$LKmUFyYURpc6utQs$a516cd1866ed7d7c5518b91fa3db1b30f2ad1fc904e743db681da228f8e8227ae8376a9ed6102aebff320d4f46da2bc7fd81abf808263e53534b1d57a4f5939f', 'admin', NULL, NULL, 1, '2026-08-14 09:28:39', '2026-08-09 17:54:27', '2026-08-14 09:28:39'),
(2, 'CS-2024-001', 'Test Student', 'student@library.edu.mm', 'student01', 'scrypt:32768:8:1$xzaxxAk51Ii4XRif$33acc0e5e3347fab8de6eb29ba77d6e4f22142874133958550c4fa080d0b24fdacb64bdc27492f69bc514fb32d88b831e78daaa2411cd56b17540d0d70e4015b', 'student', 1, NULL, 1, '2026-08-14 08:18:01', '2026-08-09 17:54:27', '2026-08-14 08:18:01'),
(6, 'MUB-1350', 'Ma Aye Myat Khaing', 'ayemyatkhaing.22-23@pumub.edu.mm', 'ayemyatkhaing', 'scrypt:32768:8:1$GYHMcKqZ0AR7U0Ck$10e955018c57ada012cd771f7a3feb862c5af15314e9d8c8bf232343dd9bf374d02162fd5cd52688439e9e628e5841f2d4969e933d124690b979ef51a856be93', 'student', NULL, '0611f0d77ca54edabdda279544e604a4.jpg', 1, '2026-08-14 13:31:24', '2026-08-12 11:14:05', '2026-08-14 13:31:24'),
(7, 'MUB-1353', 'Ma Su Myat Noe', 'sumyatnoe.22-23@pumub.edu.mm', 'Su Myat Noe', 'scrypt:32768:8:1$lVusGbOsvmTxOsoL$7b05a8fa76a89cb136bdee3e2e9b3c7bfb3e722b138f91f3427321cafd5821112989cb467b90e6ab3f334000c338cbe2a86c706fa73d32d36481f496abe48b8e', 'student', NULL, NULL, 1, '2026-08-12 16:52:30', '2026-08-12 11:14:46', '2026-08-12 16:52:30'),
(8, 'MUB-1331', 'Mg Shein Wai Khant', 'sheinwaikhant.22-23@pumub.edu.mm', 'Shein Wai Khant', 'scrypt:32768:8:1$eJwHhWpCvbVlangn$a7347a22cdcc2254afdc561b73581215d1462d404cffbd8cd122c2da39e3145e21fd2470e212e0775ad828baa4012caee2a88d3b639a00473ad0ad966980eadc', 'student', NULL, NULL, 1, '2026-08-12 16:54:56', '2026-08-12 11:19:11', '2026-08-12 16:54:56'),
(9, 'MUB-1345', 'Mg Htet Myat Naing', 'htetmyatnaing.22-23@pumub.edu.mm', 'Htet Myat Naing', 'scrypt:32768:8:1$HVtFOCOViQCBpG3n$f91568e9c2fdf08289a6d8b10c25887cede5214f5bc02ca39054baafb9285f29e7bdeb572b7cfa5ccd831090bc69a436375880f1716df36c77e06050c52c9562', 'student', NULL, NULL, 1, '2026-08-12 17:11:32', '2026-08-12 11:20:31', '2026-08-12 17:11:32'),
(10, 'MUB-1338', 'Ma Zin Thawdar Phyo', 'zinthawdarphyo.22-23@pumub.edu.mm', 'Zin Thawdar Phyo', 'scrypt:32768:8:1$cBtqJChq8jRYqe9u$765327a9766eea8481f6bb1934c63d8ec0587013caefd483b16845010821697dea01897f5f05d631de82e465febbe2b8df691bb053bff199b78623bcb413bbac', 'student', NULL, NULL, 1, '2026-08-12 16:55:41', '2026-08-12 11:22:11', '2026-08-12 16:55:41'),
(11, 'T-001', 'Tr. Lwin May Thant', 'lwinmaythant12@pumub.edu.mm', 'Daw Lwin May Thant', 'scrypt:32768:8:1$suZE6HUJhVNM646n$90b2980996410f9b2df031858c5cb060607a064fa6ef78e89d88004a5da7236be793a957d134f3798a997e8578a6e02acff065f541351db346b72254077b8a2d', 'teacher', NULL, NULL, 1, '2026-08-12 16:56:36', '2026-08-12 11:23:43', '2026-08-12 16:56:36'),
(12, 'T-002', 'Tr. Hsu Mon Kyi', 'sumonkyi67@pumub.edu.mm', 'Daw Hsu Mon Kyi', 'scrypt:32768:8:1$Rjm064G9Lm1ULzAh$a6228c0c815a203db71620e48e8de21ee41cf97500aa86c3dc9e1dab5a0e749ee88a9e5ed0269510ec82ee1e9ca6191dd66514daba601b1928e53b7caab2f13d', 'teacher', NULL, NULL, 1, '2026-08-12 16:58:54', '2026-08-12 11:25:20', '2026-08-12 16:58:54'),
(13, 'MUB-1360', 'Ye Kaung Chit', 'yekaungchit.22-23@pumub.edu.mm', 'yekaung', 'scrypt:32768:8:1$RwSkp9pADcS7kAcV$b030a3f55ed70a79336ef37281d0d033e74a11f5f6a61c0caacac604c180af8be3143eace746ce973bf7290e551c96e9dcf30ed5922dd2890c48432f6975eeb8', 'student', NULL, NULL, 1, '2026-08-14 08:34:36', '2026-08-14 08:22:02', '2026-08-14 08:34:36');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `announcements`
--
ALTER TABLE `announcements`
  ADD PRIMARY KEY (`announcement_id`),
  ADD KEY `fk_announcements_admin` (`created_by`);

--
-- Indexes for table `authors`
--
ALTER TABLE `authors`
  ADD PRIMARY KEY (`author_id`);

--
-- Indexes for table `bookmarks`
--
ALTER TABLE `bookmarks`
  ADD PRIMARY KEY (`bookmark_id`),
  ADD UNIQUE KEY `uq_user_book` (`user_id`,`book_id`),
  ADD KEY `fk_bookmarks_book` (`book_id`);

--
-- Indexes for table `books`
--
ALTER TABLE `books`
  ADD PRIMARY KEY (`book_id`),
  ADD KEY `fk_books_author` (`author_id`),
  ADD KEY `fk_books_category` (`category_id`),
  ADD KEY `fk_books_faculty` (`faculty_id`),
  ADD KEY `idx_books_title` (`title`);

--
-- Indexes for table `borrow_requests`
--
ALTER TABLE `borrow_requests`
  ADD PRIMARY KEY (`borrow_id`),
  ADD UNIQUE KEY `borrow_id_code` (`borrow_id_code`),
  ADD KEY `fk_borrow_user` (`user_id`),
  ADD KEY `fk_borrow_book` (`book_id`);

--
-- Indexes for table `categories`
--
ALTER TABLE `categories`
  ADD PRIMARY KEY (`category_id`),
  ADD UNIQUE KEY `category_name` (`category_name`);

--
-- Indexes for table `downloads`
--
ALTER TABLE `downloads`
  ADD PRIMARY KEY (`download_id`),
  ADD KEY `fk_downloads_user` (`user_id`),
  ADD KEY `fk_downloads_book` (`book_id`);

--
-- Indexes for table `faculties`
--
ALTER TABLE `faculties`
  ADD PRIMARY KEY (`faculty_id`);

--
-- Indexes for table `fines`
--
ALTER TABLE `fines`
  ADD PRIMARY KEY (`fine_id`),
  ADD KEY `fk_fines_borrow` (`borrow_id`),
  ADD KEY `fk_fines_user` (`user_id`);

--
-- Indexes for table `notifications`
--
ALTER TABLE `notifications`
  ADD PRIMARY KEY (`notification_id`),
  ADD KEY `fk_notifications_user` (`user_id`);

--
-- Indexes for table `read_history`
--
ALTER TABLE `read_history`
  ADD PRIMARY KEY (`history_id`),
  ADD KEY `fk_readhistory_user` (`user_id`),
  ADD KEY `fk_readhistory_book` (`book_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `student_id` (`student_id`),
  ADD KEY `fk_users_faculty` (`faculty_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `announcements`
--
ALTER TABLE `announcements`
  MODIFY `announcement_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `authors`
--
ALTER TABLE `authors`
  MODIFY `author_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `bookmarks`
--
ALTER TABLE `bookmarks`
  MODIFY `bookmark_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `books`
--
ALTER TABLE `books`
  MODIFY `book_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `borrow_requests`
--
ALTER TABLE `borrow_requests`
  MODIFY `borrow_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT for table `categories`
--
ALTER TABLE `categories`
  MODIFY `category_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `downloads`
--
ALTER TABLE `downloads`
  MODIFY `download_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `faculties`
--
ALTER TABLE `faculties`
  MODIFY `faculty_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT for table `fines`
--
ALTER TABLE `fines`
  MODIFY `fine_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `notifications`
--
ALTER TABLE `notifications`
  MODIFY `notification_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=77;

--
-- AUTO_INCREMENT for table `read_history`
--
ALTER TABLE `read_history`
  MODIFY `history_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=23;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `announcements`
--
ALTER TABLE `announcements`
  ADD CONSTRAINT `fk_announcements_admin` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `bookmarks`
--
ALTER TABLE `bookmarks`
  ADD CONSTRAINT `fk_bookmarks_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`book_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_bookmarks_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `books`
--
ALTER TABLE `books`
  ADD CONSTRAINT `fk_books_author` FOREIGN KEY (`author_id`) REFERENCES `authors` (`author_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_books_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_books_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculties` (`faculty_id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `borrow_requests`
--
ALTER TABLE `borrow_requests`
  ADD CONSTRAINT `fk_borrow_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`book_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_borrow_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `downloads`
--
ALTER TABLE `downloads`
  ADD CONSTRAINT `fk_downloads_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`book_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_downloads_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `fines`
--
ALTER TABLE `fines`
  ADD CONSTRAINT `fk_fines_borrow` FOREIGN KEY (`borrow_id`) REFERENCES `borrow_requests` (`borrow_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_fines_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `notifications`
--
ALTER TABLE `notifications`
  ADD CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `read_history`
--
ALTER TABLE `read_history`
  ADD CONSTRAINT `fk_readhistory_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`book_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_readhistory_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `users`
--
ALTER TABLE `users`
  ADD CONSTRAINT `fk_users_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculties` (`faculty_id`) ON DELETE SET NULL ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
