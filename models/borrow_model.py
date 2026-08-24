"""
models/borrow_model.py
-----------------------
New 5-step borrow workflow:
  pending → approved (+ QR) → borrowed (copies -1) → overdue/returned (copies +1)

Status values: pending, approved, borrowed, overdue, returned, rejected
"""

from models.db import mysql
from datetime import datetime, date

FINE_RATE_MMK_PER_DAY = 200


def _coerce_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


# ─── HELPERS ─────────────────────────────────────────────────

def _generate_borrow_code():
    """Generate the next code from the highest existing suffix, not row count."""
    cur = mysql.connection.cursor()
    year = datetime.now().year
    cur.execute("""
        SELECT COALESCE(MAX(CAST(SUBSTRING_INDEX(borrow_id_code, '-', -1) AS UNSIGNED)), 0) AS last_no
        FROM borrow_requests
        WHERE borrow_id_code LIKE %s
    """, (f"BR-{year}-%",))
    row = cur.fetchone()
    cur.close()
    next_no = int(row["last_no"] if row else 0) + 1
    return f"BR-{year}-{next_no:04d}"


# ─── STEP 1: Student Request ──────────────────────────────────

def create_borrow_request(user_id, book_id):
    """User submits borrow request. Status = pending."""
    cur = mysql.connection.cursor()
    
    # Get user role
    cur.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    role = user["role"] if user else "student"
    
    # Check active borrow count
    cur.execute("""
        SELECT COUNT(*) AS active_count FROM borrow_requests
        WHERE user_id = %s AND status IN ('pending', 'approved', 'borrowed', 'overdue')
    """, (user_id,))
    active_count = cur.fetchone()["active_count"]
    
    # Existing Borrow Management policy: Student = 3, Teacher = 10.
    limit = 10 if role == "teacher" else 3
    if active_count >= limit:
        cur.close()
        return "limit_reached"

    # Check duplicate active request for the same book
    cur.execute("""
        SELECT borrow_id FROM borrow_requests
        WHERE user_id=%s AND book_id=%s
          AND status IN ('pending','approved','borrowed', 'overdue')
    """, (user_id, book_id))
    existing = cur.fetchone()
    if existing:
        cur.close()
        return "duplicate"

    cur.execute("""
        INSERT INTO borrow_requests (user_id, book_id, status)
        VALUES (%s, %s, 'pending')
    """, (user_id, book_id))
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id


# ─── STEP 2: Admin Approve ────────────────────────────────────

def approve_borrow(borrow_id, qr_folder, base_url="http://127.0.0.1:5000"):
    """Approve a pending request once and return its stable ticket code."""
    from utils.qrcode_gen import generate_borrow_qr

    cur = mysql.connection.cursor()
    cur.execute("SELECT status, borrow_id_code FROM borrow_requests WHERE borrow_id=%s", (borrow_id,))
    current = cur.fetchone()
    if not current:
        cur.close()
        raise ValueError("Borrow request not found")
    if current["status"] == "approved" and current["borrow_id_code"]:
        cur.close()
        return current["borrow_id_code"]
    if current["status"] != "pending":
        cur.close()
        raise ValueError("Only pending requests can be approved")

    borrow_id_code = _generate_borrow_code()
    qr_filename = generate_borrow_qr(borrow_id_code, qr_folder, base_url)
    cur.execute("""
        UPDATE borrow_requests
        SET status='approved', approve_date=%s, borrow_id_code=%s, borrow_qr=%s
        WHERE borrow_id=%s AND status='pending' AND borrow_id_code IS NULL
    """, (datetime.now(), borrow_id_code, qr_filename, borrow_id))
    if cur.rowcount != 1:
        mysql.connection.rollback()
        cur.close()
        raise ValueError("This request was already processed")
    mysql.connection.commit()
    cur.close()
    return borrow_id_code


# ─── STEP 3: Lookup by borrow_id_code (QR scan / manual entry) ───

def get_borrow_by_code(borrow_id_code):
    """Find borrow record by BR code (used after QR scan)."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT br.*, u.name AS student_name, u.student_id,
               b.title AS book_title, b.available_copies, b.cover_image
        FROM borrow_requests br
        JOIN users u ON br.user_id = u.user_id
        JOIN books b ON br.book_id = b.book_id
        WHERE br.borrow_id_code = %s
    """, (borrow_id_code,))
    row = cur.fetchone()
    cur.close()
    return row


# ─── STEP 4: Issue Book (Admin enters dates) ──────────────────

def issue_book(borrow_id, borrowed_date, due_date):
    """Move an approved request to borrowed and decrement one available copy."""
    borrowed = _coerce_date(borrowed_date)
    due = _coerce_date(due_date)
    if not borrowed or not due:
        raise ValueError("Borrowed date and due date are required")
    if due < borrowed:
        raise ValueError("Due date cannot be earlier than borrowed date")

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT br.book_id, br.status, b.available_copies
            FROM borrow_requests br JOIN books b ON b.book_id=br.book_id
            WHERE br.borrow_id=%s FOR UPDATE
        """, (borrow_id,))
        row = cur.fetchone()
        if not row or row["status"] != "approved":
            raise ValueError("Only approved requests can be issued")
        if int(row["available_copies"] or 0) < 1:
            raise ValueError("No available copies remain")
        cur.execute("""
            UPDATE borrow_requests
            SET status='borrowed', borrowed_date=%s, due_date=%s, issued_date=%s
            WHERE borrow_id=%s AND status='approved'
        """, (borrowed, due, datetime.now(), borrow_id))
        cur.execute("UPDATE books SET available_copies=available_copies-1 WHERE book_id=%s AND available_copies>0", (row["book_id"],))
        if cur.rowcount != 1:
            raise ValueError("Unable to reserve a copy")
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()


# ─── STEP 5: Return Book ─────────────────────────────────────

def return_book(borrow_id):
    """Return a book, restore stock, create one final fine, and notify atomically."""
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT br.*, u.name AS student_name, u.role, b.title AS book_title
            FROM borrow_requests br
            JOIN users u ON u.user_id = br.user_id
            JOIN books b ON b.book_id = br.book_id
            WHERE br.borrow_id=%s FOR UPDATE
        """, (borrow_id,))
        row = cur.fetchone()
        if not row or row["status"] not in ("borrowed", "overdue"):
            raise ValueError("Only borrowed or overdue books can be returned")

        returned_at = datetime.now()
        due = _coerce_date(row.get("due_date"))
        late_days = max(0, (returned_at.date() - due).days) if due else 0
        fine_amount = 0 if row.get("role") == "teacher" else late_days * FINE_RATE_MMK_PER_DAY

        cur.execute("""
            UPDATE borrow_requests
            SET status='returned', return_date=%s
            WHERE borrow_id=%s AND status IN ('borrowed','overdue')
        """, (returned_at, borrow_id))
        if cur.rowcount != 1:
            raise ValueError("This borrow was already returned")

        cur.execute("""
            UPDATE books SET available_copies=available_copies+1
            WHERE book_id=%s AND available_copies < total_copies
        """, (row["book_id"],))
        if cur.rowcount != 1:
            raise ValueError("Unable to restore book stock safely")

        fine_id = None
        if fine_amount > 0:
            cur.execute("SELECT fine_id FROM fines WHERE borrow_id=%s FOR UPDATE", (borrow_id,))
            existing = cur.fetchone()
            if existing:
                fine_id = existing["fine_id"]
            else:
                cur.execute("""
                    INSERT INTO fines (borrow_id, user_id, amount, reason, is_paid, paid_at)
                    VALUES (%s, %s, %s, %s, 0, NULL)
                """, (borrow_id, row["user_id"], fine_amount, f"Late Return ({late_days} days)"))
                fine_id = cur.lastrowid

        if fine_amount > 0:
            title = f"Fine Created — {row['borrow_id_code'] or borrow_id}"
            message = (f"{row['book_title']} ကို ပြန်အပ်ပြီးပါပြီ။ "
                       f"Late {late_days} days အတွက် {fine_amount:,.0f} MMK final fine ရှိပါသည်။")
            ntype = "fine_added"
        else:
            title = f"Book Returned — {row['book_title']}"
            message = f"{row['book_title']} ({row['borrow_id_code'] or borrow_id}) ကို ပြန်အပ်ပြီးကြောင်း မှတ်တမ်းတင်ပြီးပါပြီ။"
            ntype = "borrow_returned"
        cur.execute("""
            INSERT INTO notifications (user_id, borrow_id, title, message, type)
            VALUES (%s, %s, %s, %s, %s)
        """, (row["user_id"], borrow_id, title, message, ntype))
        mysql.connection.commit()
        return {
            "borrow_id": borrow_id,
            "user_id": row["user_id"],
            "student_name": row["student_name"],
            "book_title": row["book_title"],
            "borrow_id_code": row["borrow_id_code"],
            "late_days": late_days,
            "fine_amount": fine_amount,
            "fine_id": fine_id,
            "return_date": returned_at,
        }
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()


# ─── OVERDUE: Mark overdue records ───────────────────────────

def mark_overdue_records():
    """
    Find all borrowed books past due_date and mark as overdue.
    Call this from a scheduled job or dashboard load.
    """
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE borrow_requests
        SET status = 'overdue'
        WHERE status = 'borrowed'
          AND due_date < CURDATE()
    """)
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected


# ─── REJECT ──────────────────────────────────────────────────

def reject_borrow(borrow_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE borrow_requests SET status='rejected' WHERE borrow_id=%s",
        (borrow_id,)
    )
    mysql.connection.commit()
    cur.close()


# ─── QUERIES ─────────────────────────────────────────────────

def _paginate_rows(cur, query, params, page, per_page):
    """Execute a bounded query and return rows plus pagination metadata."""
    per_page = max(1, min(int(per_page or 25), 100))
    page = max(1, int(page or 1))
    cur.execute(f"SELECT COUNT(*) AS total FROM ({query}) AS matched_rows", tuple(params))
    total = int((cur.fetchone() or {}).get("total", 0))
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    offset = (page - 1) * per_page
    cur.execute(query + " LIMIT %s OFFSET %s", tuple(params) + (per_page, offset))
    return {"records": cur.fetchall(), "total": total, "page": page, "per_page": per_page, "pages": pages}


def get_all_borrow_requests(status=None, search=None, start_date=None, end_date=None, faculty_id=None, category_id=None, page=None, per_page=25):
    """Get borrow requests; preserve list return by default and paginate when requested."""
    query = """
        SELECT br.*, u.name AS student_name, u.student_id,
               u.email AS student_email, u.role,
               b.title AS book_title, b.author_name, b.available_copies,
               c.category_name, fac.faculty_name, fac.department,
               fn.fine_id, fn.amount AS fine_amount, fn.reason AS fine_reason,
               fn.is_paid AS fine_paid, fn.created_at AS fine_created_at,
               fn.paid_at AS fine_paid_at,
               (SELECT COUNT(*) FROM borrow_requests br2
                WHERE br2.user_id = br.user_id
                  AND br2.status IN ('pending','approved','borrowed','overdue')) AS active_borrow_count
        FROM borrow_requests br
        JOIN users u ON br.user_id = u.user_id
        JOIN books b ON br.book_id = b.book_id
        LEFT JOIN categories c ON b.category_id = c.category_id
        LEFT JOIN faculties fac ON u.faculty_id = fac.faculty_id
        LEFT JOIN fines fn ON br.borrow_id = fn.borrow_id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND br.status = %s"
        params.append(status)
    if start_date:
        query += " AND DATE(br.request_date) >= %s"
        params.append(start_date)
    if end_date:
        query += " AND DATE(br.request_date) <= %s"
        params.append(end_date)
    if faculty_id:
        query += " AND u.faculty_id = %s"
        params.append(int(faculty_id))
    if category_id:
        query += " AND b.category_id = %s"
        params.append(int(category_id))
    if search:
        query += " AND (u.name LIKE %s OR u.student_id LIKE %s OR b.title LIKE %s OR br.borrow_id_code LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like, like])
    query += " ORDER BY br.request_date DESC"
    cur = mysql.connection.cursor()
    result = _paginate_rows(cur, query, tuple(params), page, per_page) if page is not None else None
    if result is None:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        cur.close()
        return _enrich_fine_fields(rows)
    result["records"] = _enrich_fine_fields(result["records"])
    cur.close()
    return result





def _enrich_fine_fields(rows):
    """Attach the same current estimated/final fine fields to every borrow row."""
    today = date.today()
    for row in rows:
        due = _coerce_date(row.get("due_date"))
        returned = _coerce_date(row.get("return_date"))
        end = returned or today
        late_days = max(0, (end - due).days) if due else 0
        if row.get("role") == "teacher":
            late_days = 0
        row["late_days"] = late_days
        row["estimated_fine"] = late_days * FINE_RATE_MMK_PER_DAY
        row["fine_rate"] = FINE_RATE_MMK_PER_DAY
        row["days_remaining"] = (due - today).days if due and row.get("status") in ("borrowed", "approved") else 0
        row["fine_status"] = "paid" if row.get("fine_paid") else ("unpaid" if row.get("fine_amount") else None)
    return rows


def get_borrow_by_id(borrow_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT br.*, u.name AS student_name, u.student_id,
               b.title AS book_title, b.available_copies
        FROM borrow_requests br
        JOIN users u ON br.user_id = u.user_id
        JOIN books b ON br.book_id = b.book_id
        WHERE br.borrow_id = %s
    """, (borrow_id,))
    row = cur.fetchone()
    cur.close()
    return _enrich_fine_fields([row])[0] if row else None


def get_student_borrow_history(user_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT br.*, u.role, b.title AS book_title, b.cover_image,
               a.author_name,
               f.amount AS fine_amount, f.is_paid AS fine_paid
        FROM borrow_requests br
        JOIN users u ON u.user_id = br.user_id
        JOIN books b ON br.book_id = b.book_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN fines f ON br.borrow_id = f.borrow_id
        WHERE br.user_id = %s
        ORDER BY br.request_date DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    return _enrich_fine_fields(rows)


def get_student_fines(user_id, status=None):
    cur = mysql.connection.cursor()
    query = """
        SELECT f.*, b.title AS book_title, b.cover_image,
               br.due_date, br.return_date, br.borrow_id_code
        FROM fines f
        JOIN borrow_requests br ON br.borrow_id=f.borrow_id
        JOIN books b ON b.book_id=br.book_id
        WHERE f.user_id=%s
    """
    params = [user_id]
    if status == "unpaid":
        query += " AND f.is_paid=0"
    elif status == "paid":
        query += " AND f.is_paid=1"
    query += " ORDER BY f.created_at DESC"
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    for row in rows:
        due = _coerce_date(row.get("due_date"))
        returned = _coerce_date(row.get("return_date"))
        row["late_days"] = max(0, (returned - due).days) if due and returned else 0
    return rows


# ─── STATS ───────────────────────────────────────────────────

def get_borrow_stats():
    """Count per status for dashboard."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
          SUM(status='pending')  AS pending,
          SUM(status='approved') AS approved,
          SUM(status='borrowed') AS borrowed,
          SUM(status='overdue')  AS overdue,
          SUM(status='returned') AS returned,
          SUM(status='rejected') AS rejected
        FROM borrow_requests
    """)
    row = cur.fetchone()
    cur.close()
    return {
        "pending":  int(row["pending"]  or 0),
        "approved": int(row["approved"] or 0),
        "borrowed": int(row["borrowed"] or 0),
        "overdue":  int(row["overdue"]  or 0),
        "returned": int(row["returned"] or 0),
        "rejected": int(row["rejected"] or 0),
    }


# ─── FINES ───────────────────────────────────────────────────

def calculate_fine(borrow_id, as_of=None):
    """Return current estimated or final fine as (late_days, amount)."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT br.due_date, br.return_date, br.status, u.role
        FROM borrow_requests br
        JOIN users u ON br.user_id = u.user_id
        WHERE br.borrow_id = %s
    """, (borrow_id,))
    br = cur.fetchone()
    cur.close()
    if not br or not br["due_date"] or br["role"] == "teacher":
        return 0, 0
    due = _coerce_date(br["due_date"])
    end = _coerce_date(br["return_date"]) or as_of or date.today()
    if isinstance(end, datetime):
        end = end.date()
    if end <= due:
        return 0, 0
    days = (end - due).days
    return days, days * FINE_RATE_MMK_PER_DAY


def get_all_fines(status=None, search=None, start_date=None, end_date=None, faculty_id=None, page=None, per_page=25):
    """Get fine records with optional real filters and backward-compatible list return."""
    query = """
        SELECT f.*, u.name AS student_name, u.student_id,
               b.title AS book_title, b.author_name,
               c.category_name, fac.faculty_name,
               br.status AS borrow_status, br.due_date, br.return_date,
               br.borrow_id_code, br.borrowed_date, br.issued_date
        FROM fines f
        JOIN users u ON f.user_id = u.user_id
        JOIN borrow_requests br ON f.borrow_id = br.borrow_id
        JOIN books b ON br.book_id = b.book_id
        LEFT JOIN categories c ON b.category_id = c.category_id
        LEFT JOIN faculties fac ON u.faculty_id = fac.faculty_id
        WHERE 1=1
    """
    params = []
    if status == "paid":
        query += " AND f.is_paid=1"
    elif status == "unpaid":
        query += " AND f.is_paid=0"
    elif status == "overdue":
        query += " AND f.is_paid=0 AND br.status='overdue'"
    if start_date:
        query += " AND DATE(f.created_at) >= %s"
        params.append(start_date)
    if end_date:
        query += " AND DATE(f.created_at) <= %s"
        params.append(end_date)
    if faculty_id:
        query += " AND u.faculty_id = %s"
        params.append(int(faculty_id))
    if search:
        query += " AND (u.name LIKE %s OR u.student_id LIKE %s OR b.title LIKE %s OR br.borrow_id_code LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like, like])
    query += " ORDER BY f.created_at DESC"

    cur = mysql.connection.cursor()
    result = _paginate_rows(cur, query, tuple(params), page, per_page) if page is not None else None
    if result is None:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
    else:
        rows = result["records"]
    today = date.today()
    for row in rows:
        due = _coerce_date(row.get("due_date"))
        returned = _coerce_date(row.get("return_date"))
        end = returned or today
        row["late_days"] = max(0, (end - due).days) if due else 0
    cur.close()
    if result is None:
        return rows
    result["records"] = rows
    return result


def add_fine(borrow_id, user_id, amount, reason="Late Return"):
    """Create at most one final fine per borrow; DB migration adds a unique guard."""
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT fine_id FROM fines WHERE borrow_id=%s FOR UPDATE", (borrow_id,))
        existing = cur.fetchone()
        if existing:
            return existing["fine_id"]
        cur.execute("INSERT INTO fines (borrow_id, user_id, amount, reason) VALUES (%s, %s, %s, %s)", (borrow_id, user_id, amount, reason))
        fine_id = cur.lastrowid
        mysql.connection.commit()
        return fine_id
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()


def mark_fine_paid(fine_id, payment_method="Cash"):
    """Mark an unpaid fine paid once and create a student notification."""
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT f.*, br.borrow_id_code, b.title
            FROM fines f
            JOIN borrow_requests br ON br.borrow_id=f.borrow_id
            JOIN books b ON b.book_id=br.book_id
            WHERE f.fine_id=%s FOR UPDATE
        """, (fine_id,))
        fine = cur.fetchone()
        if not fine:
            raise ValueError("Fine not found")
        if fine["is_paid"]:
            return {"already_paid": True, "fine": fine}
        cur.execute("""
            UPDATE fines SET is_paid=1, paid_at=%s, payment_method=%s
            WHERE fine_id=%s AND is_paid=0
        """, (datetime.now(), payment_method or "Cash", fine_id))
        if cur.rowcount != 1:
            raise ValueError("Fine was already paid")
        cur.execute("""
            INSERT INTO notifications (user_id, borrow_id, title, message, type)
            VALUES (%s, %s, %s, %s, %s)
        """, (fine["user_id"], fine["borrow_id"], "Fine Paid", f"{fine['title']} အတွက် {fine['amount']:,.0f} MMK payment မှတ်တမ်းတင်ပြီးပါပြီ။", "fine_paid"))
        mysql.connection.commit()
        return {"already_paid": False, "fine": fine}
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()


def get_fine_total():
    """Total unpaid fines amount."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) AS total FROM fines WHERE is_paid=0")
    row = cur.fetchone()
    cur.close()
    return float(row["total"] if row else 0)


def get_fine_summary():
    """Return auditable fine totals for today, month, paid and outstanding states."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
          COALESCE(SUM(amount),0) AS all_time_total,
          COALESCE(SUM(CASE WHEN is_paid=0 THEN amount ELSE 0 END),0) AS unpaid_total,
          COALESCE(SUM(CASE WHEN is_paid=1 THEN amount ELSE 0 END),0) AS paid_total,
          COALESCE(SUM(CASE WHEN DATE(created_at)=CURDATE() THEN amount ELSE 0 END),0) AS today_generated,
          COALESCE(SUM(CASE WHEN YEAR(created_at)=YEAR(CURDATE()) AND MONTH(created_at)=MONTH(CURDATE()) THEN amount ELSE 0 END),0) AS month_generated,
          COALESCE(SUM(CASE WHEN is_paid=1 AND YEAR(paid_at)=YEAR(CURDATE()) AND MONTH(paid_at)=MONTH(CURDATE()) THEN amount ELSE 0 END),0) AS month_paid,
          COALESCE((
              SELECT SUM(f2.amount)
              FROM fines f2
              JOIN borrow_requests br2 ON br2.borrow_id = f2.borrow_id
              WHERE f2.is_paid = 0 AND br2.status = 'overdue'
          ), 0) AS overdue_total
        FROM fines
    """)
    row = cur.fetchone() or {}
    cur.close()
    return {key: float(row.get(key) or 0) for key in (
        "all_time_total", "unpaid_total", "paid_total", "today_generated", "month_generated", "month_paid", "overdue_total"
    )}


def get_fine_report_years():
    """Return calendar years represented by fine creation or payment dates."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT DISTINCT year_value
        FROM (
            SELECT YEAR(created_at) AS year_value FROM fines WHERE created_at IS NOT NULL
            UNION
            SELECT YEAR(paid_at) AS year_value FROM fines WHERE paid_at IS NOT NULL
        ) AS fine_years
        WHERE year_value IS NOT NULL
        ORDER BY year_value DESC
    """)
    years = [int(row["year_value"]) for row in cur.fetchall()]
    cur.close()
    current_year = date.today().year
    return sorted(set(years + [current_year]), reverse=True)


def get_monthly_fine_report(year=None):
    """Return Jan-Dec accounting for one year using the correct date columns.

    Generated is grouped by fines.created_at. Paid is grouped independently by
    fines.paid_at. This prevents a fine created in one month and paid in a later
    month from being counted as paid in its creation month.
    """
    report_year = int(year or date.today().year)
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT MONTH(created_at) AS month_number, COALESCE(SUM(amount), 0) AS `fine_generated`
        FROM fines
        WHERE YEAR(created_at) = %s
        GROUP BY MONTH(created_at)
    """, (report_year,))
    generated = {int(row["month_number"]): float(row["fine_generated"] or 0) for row in cur.fetchall()}
    cur.execute("""
        SELECT MONTH(paid_at) AS month_number, COALESCE(SUM(amount), 0) AS paid
        FROM fines
        WHERE is_paid = 1 AND paid_at IS NOT NULL AND YEAR(paid_at) = %s
        GROUP BY MONTH(paid_at)
    """, (report_year,))
    paid = {int(row["month_number"]): float(row["paid"] or 0) for row in cur.fetchall()}
    cur.close()

    result = []
    for month_number in range(1, 13):
        generated_amount = generated.get(month_number, 0.0)
        paid_amount = paid.get(month_number, 0.0)
        result.append({
            "month": date(report_year, month_number, 1).strftime("%B"),
            "month_number": month_number,
            "year": report_year,
            "generated": generated_amount,
            "paid": paid_amount,
            "outstanding": max(0.0, generated_amount - paid_amount),
        })
    return result

# ─── CLEARANCE ────────────────────────────────────────────────

def check_user_clearance(user_id):
    """
    Check if user has any outstanding obligations:
    - unreturned books (borrowed, overdue)
    - unpaid fines (for students)
    Returns: { 'cleared': bool, 'unreturned_count': int, 'unpaid_fines': float }
    """
    cur = mysql.connection.cursor()
    
    # Check unreturned books
    cur.execute("""
        SELECT COUNT(*) AS count FROM borrow_requests
        WHERE user_id = %s AND status IN ('borrowed', 'overdue')
    """, (user_id,))
    unreturned_count = cur.fetchone()["count"]
    
    # Check unpaid fines
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total FROM fines
        WHERE user_id = %s AND is_paid = 0
    """, (user_id,))
    unpaid_fines = float(cur.fetchone()["total"])
    
    cur.close()
    
    return {
        "cleared": (unreturned_count == 0 and unpaid_fines == 0),
        "unreturned_count": unreturned_count,
        "unpaid_fines": unpaid_fines
    }

def get_student_borrow_stats(user_id):
    """Count per status for a specific student's dashboard."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
          SUM(status='pending')  AS pending,
          SUM(status='approved') AS approved,
          SUM(status='borrowed') AS borrowed,
          SUM(status='overdue')  AS overdue
        FROM borrow_requests
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    return {
        "pending":  int(row["pending"]  or 0),
        "approved": int(row["approved"] or 0),
        "borrowed": int(row["borrowed"] or 0),
        "overdue":  int(row["overdue"]  or 0),
    }
