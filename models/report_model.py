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
    cur.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'student'")
    total_students = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'teacher'")
    total_teachers = cur.fetchone()["total"]
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
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_downloads": total_downloads,
        "total_categories": total_categories,
        "active_borrows": active_borrows,
        "pending_requests": pending_requests,
    }


def get_monthly_borrow_activity(months=12):
    """Return issued-borrow activity by month using real issued_date values."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT DATE_FORMAT(issued_date, '%%Y-%%m') AS month,
               COUNT(*) AS total
        FROM borrow_requests
        WHERE issued_date IS NOT NULL
          AND status IN ('borrowed', 'overdue', 'returned')
          AND issued_date >= DATE_SUB(DATE_FORMAT(CURDATE(), '%%Y-%%m-01'), INTERVAL %s MONTH)
        GROUP BY DATE_FORMAT(issued_date, '%%Y-%%m')
        ORDER BY month ASC
    """, (months - 1,))
    existing = {row["month"]: int(row["total"] or 0) for row in cur.fetchall()}
    cur.close()
    current = date.today().replace(day=1)
    result = []
    for offset in range(months - 1, -1, -1):
        month_index = current.year * 12 + current.month - 1 - offset
        month_date = date(month_index // 12, month_index % 12 + 1, 1)
        key = month_date.strftime("%Y-%m")
        result.append({"month": key, "total": existing.get(key, 0)})
    return result


def get_recent_borrow_requests(limit=8):
    """Return recent real borrow requests for the Admin dashboard."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT br.borrow_id, br.borrow_id_code, br.status, br.request_date,
               br.due_date, u.name AS student_name, b.title AS book_title
        FROM borrow_requests br
        JOIN users u ON u.user_id = br.user_id
        JOIN books b ON b.book_id = br.book_id
        ORDER BY br.request_date DESC
        LIMIT %s
    """, (int(limit),))
    rows = cur.fetchall()
    cur.close()
    return rows


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
        WHERE br.status IN ('borrowed', 'overdue', 'returned') AND COALESCE(b.is_archived, 0) = 0
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
        WHERE b.category_id = %s AND COALESCE(b.is_archived, 0) = 0
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


def _month_start(value):
    return value.replace(day=1)


def _iter_periods(start_date, end_date, granularity):
    if granularity == "day":
        current = start_date
        while current <= end_date:
            yield current.strftime("%Y-%m-%d"), current
            current = current.fromordinal(current.toordinal() + 1)
        return
    current = _month_start(start_date)
    stop = _month_start(end_date)
    while current <= stop:
        yield current.strftime("%Y-%m"), current
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)


def get_borrowing_trend(start_date, end_date, granularity="month"):
    """Return a continuous real-data borrowing series from issued_date."""
    if granularity == "day":
        expression = "DATE(br.issued_date)"
    else:
        expression = "DATE_FORMAT(br.issued_date, '%%Y-%%m')"
    cur = mysql.connection.cursor()
    cur.execute(f"""
        SELECT {expression} AS period, COUNT(*) AS total
        FROM borrow_requests br
        WHERE br.issued_date IS NOT NULL
          AND DATE(br.issued_date) BETWEEN %s AND %s
          AND br.status IN ('borrowed', 'overdue', 'returned')
        GROUP BY {expression}
        ORDER BY period ASC
    """, (start_date, end_date))
    existing = {str(row["period"]): int(row["total"] or 0) for row in cur.fetchall()}
    cur.close()
    return [{"period": key, "total": existing.get(key, 0)} for key, _ in _iter_periods(start_date, end_date, granularity)]


def get_borrow_by_faculty(start_date, end_date, limit=12):
    """Count issued borrow records by the borrowing user's faculty."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT COALESCE(CONCAT_WS(' · ', f.faculty_name, f.department), 'Unassigned') AS faculty_name,
               COUNT(br.borrow_id) AS borrow_count
        FROM borrow_requests br
        JOIN users u ON u.user_id = br.user_id
        LEFT JOIN faculties f ON f.faculty_id = u.faculty_id
        WHERE br.issued_date IS NOT NULL
          AND DATE(br.issued_date) BETWEEN %s AND %s
          AND br.status IN ('borrowed', 'overdue', 'returned')
        GROUP BY f.faculty_id, f.faculty_name, f.department
        ORDER BY borrow_count DESC, faculty_name ASC
        LIMIT %s
    """, (start_date, end_date, int(limit)))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_borrow_by_category(start_date, end_date, limit=12):
    """Count issued borrow records by the book's real category."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT COALESCE(c.category_name, 'Uncategorized') AS category_name,
               COUNT(br.borrow_id) AS borrow_count
        FROM borrow_requests br
        JOIN books b ON b.book_id = br.book_id
        LEFT JOIN categories c ON c.category_id = b.category_id
        WHERE br.issued_date IS NOT NULL
          AND DATE(br.issued_date) BETWEEN %s AND %s
          AND br.status IN ('borrowed', 'overdue', 'returned')
        GROUP BY c.category_id, c.category_name
        ORDER BY borrow_count DESC, category_name ASC
        LIMIT %s
    """, (start_date, end_date, int(limit)))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_fine_trend(start_date, end_date, granularity="month"):
    """Return generated and paid fine activity using created_at and paid_at separately."""
    if granularity == "day":
        expression_created = "DATE(created_at)"
        expression_paid = "DATE(paid_at)"
    else:
        expression_created = "DATE_FORMAT(created_at, '%%Y-%%m')"
        expression_paid = "DATE_FORMAT(paid_at, '%%Y-%%m')"
    cur = mysql.connection.cursor()
    cur.execute(f"""
        SELECT {expression_created} AS period, COALESCE(SUM(amount), 0) AS `fine_generated`
        FROM fines
        WHERE DATE(created_at) BETWEEN %s AND %s
        GROUP BY {expression_created}
    """, (start_date, end_date))
    generated = {str(row["period"]): float(row["fine_generated"] or 0) for row in cur.fetchall()}
    cur.execute(f"""
        SELECT {expression_paid} AS period, COALESCE(SUM(amount), 0) AS paid
        FROM fines
        WHERE is_paid = 1 AND paid_at IS NOT NULL
          AND DATE(paid_at) BETWEEN %s AND %s
        GROUP BY {expression_paid}
    """, (start_date, end_date))
    paid = {str(row["period"]): float(row["paid"] or 0) for row in cur.fetchall()}
    cur.close()
    return [{"period": key, "generated": generated.get(key, 0.0), "paid": paid.get(key, 0.0)} for key, _ in _iter_periods(start_date, end_date, granularity)]


def _report_result(cur, query, params, count_query, count_params, page, per_page):
    cur.execute(count_query, tuple(count_params))
    total = int((cur.fetchone() or {}).get("total", 0))
    offset = max(0, (int(page) - 1) * int(per_page))
    cur.execute(query + " LIMIT %s OFFSET %s", tuple(params) + (int(per_page), offset))
    rows = cur.fetchall()
    return {"rows": rows, "total": total, "page": int(page), "per_page": int(per_page), "pages": max(1, (total + per_page - 1) // per_page)}


def get_admin_report(report_type="borrowing", start_date=None, end_date=None, status=None, search=None, faculty_id=None, category_id=None, page=1, per_page=25):
    """Return bounded, server-filtered report rows using only existing schema fields."""
    report_type = report_type if report_type in {"borrowing", "overdue", "fines", "book_usage"} else "borrowing"
    cur = mysql.connection.cursor()
    params = []
    filters = []
    if report_type in {"borrowing", "overdue"}:
        base = """
            FROM borrow_requests br
            JOIN users u ON u.user_id = br.user_id
            JOIN books b ON b.book_id = br.book_id
            LEFT JOIN faculties fac ON fac.faculty_id = u.faculty_id
            LEFT JOIN categories cat ON cat.category_id = b.category_id
            LEFT JOIN fines fn ON fn.borrow_id = br.borrow_id
        """
        if start_date:
            filters.append("DATE(COALESCE(br.issued_date, br.request_date)) >= %s"); params.append(start_date)
        if end_date:
            filters.append("DATE(COALESCE(br.issued_date, br.request_date)) <= %s"); params.append(end_date)
        if report_type == "overdue":
            filters.append("br.status = 'overdue'")
        elif status:
            filters.append("br.status = %s"); params.append(status)
        if faculty_id:
            filters.append("u.faculty_id = %s"); params.append(int(faculty_id))
        if category_id:
            filters.append("b.category_id = %s"); params.append(int(category_id))
        if search:
            like = f"%{search}%"
            filters.append("(u.name LIKE %s OR u.student_id LIKE %s OR b.title LIKE %s OR br.borrow_id_code LIKE %s)")
            params.extend([like, like, like, like])
        where = " WHERE " + " AND ".join(filters) if filters else ""
        select = """SELECT br.borrow_id, br.borrow_id_code, br.request_date, br.borrowed_date, br.issued_date, br.due_date, br.return_date, br.status, u.name AS student_name, u.student_id, fac.faculty_name, cat.category_name, b.title AS book_title, fn.amount AS fine_amount, fn.is_paid AS fine_paid, fn.paid_at"""
        query = select + base + where + " ORDER BY COALESCE(br.issued_date, br.request_date) DESC"
        count_query = "SELECT COUNT(*) AS total " + base + where
        result = _report_result(cur, query, params, count_query, params, page, per_page)
    elif report_type == "fines":
        base = """
            FROM fines fn
            JOIN users u ON u.user_id = fn.user_id
            JOIN borrow_requests br ON br.borrow_id = fn.borrow_id
            JOIN books b ON b.book_id = br.book_id
            LEFT JOIN faculties fac ON fac.faculty_id = u.faculty_id
            LEFT JOIN categories cat ON cat.category_id = b.category_id
        """
        if start_date:
            filters.append("DATE(fn.created_at) >= %s"); params.append(start_date)
        if end_date:
            filters.append("DATE(fn.created_at) <= %s"); params.append(end_date)
        if status in {"paid", "unpaid"}:
            filters.append("fn.is_paid = %s"); params.append(1 if status == "paid" else 0)
        if faculty_id:
            filters.append("u.faculty_id = %s"); params.append(int(faculty_id))
        if category_id:
            filters.append("b.category_id = %s"); params.append(int(category_id))
        if search:
            like = f"%{search}%"
            filters.append("(u.name LIKE %s OR u.student_id LIKE %s OR b.title LIKE %s OR br.borrow_id_code LIKE %s)")
            params.extend([like, like, like, like])
        where = " WHERE " + " AND ".join(filters) if filters else ""
        select = """SELECT fn.fine_id, fn.amount, fn.reason, fn.is_paid, fn.created_at, fn.paid_at, br.borrow_id, br.borrow_id_code, br.borrowed_date, br.due_date, br.return_date, br.status, u.name AS student_name, u.student_id, fac.faculty_name, cat.category_name, b.title AS book_title"""
        query = select + base + where + " ORDER BY fn.created_at DESC"
        count_query = "SELECT COUNT(*) AS total " + base + where
        result = _report_result(cur, query, params, count_query, params, page, per_page)
    else:
        base = """
            FROM books b
            LEFT JOIN categories cat ON cat.category_id = b.category_id
            LEFT JOIN borrow_requests br ON br.book_id = b.book_id
        """
        if start_date:
            filters.append("(br.issued_date IS NULL OR DATE(br.issued_date) >= %s)"); params.append(start_date)
        if end_date:
            filters.append("(br.issued_date IS NULL OR DATE(br.issued_date) <= %s)"); params.append(end_date)
        if faculty_id:
            filters.append("b.faculty_id = %s"); params.append(int(faculty_id))
        if category_id:
            filters.append("b.category_id = %s"); params.append(int(category_id))
        if search:
            like = f"%{search}%"
            filters.append("b.title LIKE %s"); params.append(like)
        where = " WHERE " + " AND ".join(filters) if filters else ""
        select = """SELECT b.book_id, b.title AS book_title, b.author_name, cat.category_name, b.available_copies, b.total_copies, COUNT(br.borrow_id) AS borrow_count, SUM(CASE WHEN br.status IN ('borrowed','overdue') THEN 1 ELSE 0 END) AS active_count"""
        group = " GROUP BY b.book_id, b.title, b.author_name, cat.category_name, b.available_copies, b.total_copies"
        query = select + base + where + group + " ORDER BY borrow_count DESC, b.title ASC"
        count_query = "SELECT COUNT(*) AS total FROM (SELECT b.book_id " + base + where + group + ") AS usage_rows"
        result = _report_result(cur, query, params, count_query, params, page, per_page)
    if report_type in {"borrowing", "overdue", "fines"}:
        for row in result["rows"]:
            due = row.get("due_date")
            end = row.get("return_date") or date.today()
            if hasattr(end, "date"):
                end = end.date()
            row["late_days"] = max(0, (end - due).days) if due else 0
    cur.close()
    return result


def get_all_announcements(search=None):
    cur = mysql.connection.cursor()
    query = """
        SELECT a.*, u.name AS created_by_name
        FROM announcements a
        LEFT JOIN users u ON a.created_by = u.user_id
        WHERE 1=1
    """
    params = []
    if search:
        like = f"%{search}%"
        query += " AND (a.title LIKE %s OR a.content LIKE %s)"
        params.extend([like, like])
    query += " ORDER BY a.date DESC"
    cur.execute(query, tuple(params))
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
