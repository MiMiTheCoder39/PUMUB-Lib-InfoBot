"""
Admin reporting and announcement database helpers.

All chart data is sourced from the existing digital_library_db schema.
"""

from datetime import date
from models.db import mysql


def get_dashboard_stats():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM books")
    total_books = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM downloads")
    total_downloads = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM categories")
    total_categories = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM borrow_requests WHERE status IN ('borrowed','overdue')")
    active_borrows = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM borrow_requests WHERE status = 'pending'")
    pending_requests = cur.fetchone()["total"]
    cur.close()
    return {
        "total_books": total_books,
        "total_users": total_users,
        "total_downloads": total_downloads,
        "total_categories": total_categories,
        "active_borrows": active_borrows,
        "pending_requests": pending_requests,
    }


def get_most_viewed_books(limit=10):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.title, COALESCE(b.view_count, 0) AS view_count,
               a.author_name, c.category_name
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN categories c ON b.category_id = c.category_id
        ORDER BY b.view_count DESC, b.title ASC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_most_downloaded_books(limit=10):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.title, COALESCE(b.download_count, 0) AS download_count,
               a.author_name, c.category_name
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN categories c ON b.category_id = c.category_id
        ORDER BY b.download_count DESC, b.title ASC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_most_borrowed_books(limit=10):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.book_id, b.title, b.cover_image, b.author_name,
               c.category_name, COUNT(br.borrow_id) AS borrow_count
        FROM borrow_requests br
        JOIN books b ON br.book_id = b.book_id
        LEFT JOIN categories c ON b.category_id = c.category_id
        GROUP BY b.book_id, b.title, b.cover_image, b.author_name, c.category_name
        ORDER BY borrow_count DESC, b.title ASC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_books_by_category_for_shelf(category_id, limit=4):
    """Return recent books for a homepage/student category shelf."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.*, COALESCE(b.author_name, '') AS author_name
        FROM books b
        WHERE b.category_id = %s
        ORDER BY b.upload_date DESC
        LIMIT %s
    """, (category_id, int(limit)))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_user_role_stats():
    cur = mysql.connection.cursor()
    cur.execute("SELECT role, COUNT(*) AS cnt FROM users GROUP BY role ORDER BY role")
    rows = cur.fetchall()
    cur.close()
    return rows


def get_borrow_status_stats():
    cur = mysql.connection.cursor()
    cur.execute("SELECT status, COUNT(*) AS cnt FROM borrow_requests GROUP BY status ORDER BY status")
    rows = cur.fetchall()
    cur.close()
    return rows


def get_category_book_counts():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.category_name, COUNT(b.book_id) AS book_count
        FROM categories c
        LEFT JOIN books b ON c.category_id = b.category_id
        GROUP BY c.category_id, c.category_name
        ORDER BY book_count DESC, c.category_name ASC
        LIMIT 12
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def get_monthly_downloads(months=12):
    """Return a continuous recent month series, including zero-download months."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT DATE_FORMAT(download_date, '%%Y-%%m') AS month, COUNT(*) AS total
        FROM downloads
        WHERE download_date >= DATE_SUB(DATE_FORMAT(CURDATE(), '%%Y-%%m-01'), INTERVAL %s MONTH)
        GROUP BY DATE_FORMAT(download_date, '%%Y-%%m')
        ORDER BY month ASC
    """, (months - 1,))
    existing = {row["month"]: int(row["total"]) for row in cur.fetchall()}
    cur.close()

    current = date.today().replace(day=1)
    result = []
    for offset in range(months - 1, -1, -1):
        month_index = current.year * 12 + current.month - 1 - offset
        month_date = date(month_index // 12, month_index % 12 + 1, 1)
        key = month_date.strftime("%Y-%m")
        result.append({"month": key, "total": existing.get(key, 0)})
    return result


def get_active_users(limit=10):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.name, u.student_id, COUNT(d.download_id) AS activity_count
        FROM users u
        JOIN downloads d ON u.user_id = d.user_id
        GROUP BY u.user_id, u.name, u.student_id
        ORDER BY activity_count DESC, u.name ASC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_all_announcements():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT ann.*, u.name AS created_by_name
        FROM announcements ann
        LEFT JOIN users u ON ann.created_by = u.user_id
        ORDER BY ann.date DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def add_announcement(title, content, created_by):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO announcements (title,content,created_by) VALUES (%s,%s,%s)", (title, content, created_by))
    mysql.connection.commit()
    cur.close()


def update_announcement(ann_id, title, content):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE announcements SET title=%s,content=%s WHERE announcement_id=%s", (title, content, ann_id))
    mysql.connection.commit()
    cur.close()


def delete_announcement(ann_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM announcements WHERE announcement_id=%s", (ann_id,))
    mysql.connection.commit()
    cur.close()


def get_announcement_by_id(ann_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM announcements WHERE announcement_id=%s", (ann_id,))
    row = cur.fetchone()
    cur.close()
    return row
