"""
models/borrow_model.py
-----------------------
New 5-step borrow workflow:
  pending → approved (+ QR) → borrowed (copies -1) → overdue/returned (copies +1)

Status values: pending, approved, borrowed, overdue, returned, rejected
"""

from models.db import mysql
from datetime import datetime, date


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
    
    # Limits: Student = 3, Teacher = 10
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
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT br.book_id, br.status, b.available_copies
        FROM borrow_requests br JOIN books b ON b.book_id=br.book_id
        WHERE br.borrow_id=%s FOR UPDATE
    """, (borrow_id,))
    row = cur.fetchone()
    if not row or row["status"] != "approved":
        cur.close()
        raise ValueError("Only approved requests can be issued")
    if int(row["available_copies"] or 0) < 1:
        cur.close()
        raise ValueError("No available copies remain")
    cur.execute("""
        UPDATE borrow_requests
        SET status='borrowed', borrowed_date=%s, due_date=%s, issued_date=%s
        WHERE borrow_id=%s AND status='approved'
    """, (borrowed_date, due_date, datetime.now(), borrow_id))
    cur.execute("UPDATE books SET available_copies=available_copies-1 WHERE book_id=%s AND available_copies>0", (row["book_id"],))
    if cur.rowcount != 1:
        mysql.connection.rollback()
        cur.close()
        raise ValueError("Unable to reserve a copy")
    mysql.connection.commit()
    cur.close()


# ─── STEP 5: Return Book ─────────────────────────────────────

def return_book(borrow_id):
    """Return a borrowed/overdue book once and restore exactly one copy."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT book_id, status FROM borrow_requests WHERE borrow_id=%s FOR UPDATE", (borrow_id,))
    row = cur.fetchone()
    if not row or row["status"] not in ("borrowed", "overdue"):
        cur.close()
        raise ValueError("Only borrowed or overdue books can be returned")
    cur.execute("UPDATE borrow_requests SET status='returned', return_date=%s WHERE borrow_id=%s", (datetime.now(), borrow_id))
    cur.execute("UPDATE books SET available_copies=available_copies+1 WHERE book_id=%s", (row["book_id"],))
    mysql.connection.commit()
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

def get_all_borrow_requests(status=None, search=None):
    """
    Get all borrow requests with optional status filter and search.
    search: searches student name, student_id, book title, borrow_id_code
    """
    query = """
        SELECT br.*, u.name AS student_name, u.student_id,
               u.email AS student_email,
               b.title AS book_title, b.available_copies,
               f.faculty_name, f.department
        FROM borrow_requests br
        JOIN users u ON br.user_id = u.user_id
        JOIN books b ON br.book_id = b.book_id
        LEFT JOIN faculties f ON u.faculty_id = f.faculty_id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND br.status = %s"
        params.append(status)
    if search:
        query += """ AND (
            u.name LIKE %s OR u.student_id LIKE %s
            OR b.title LIKE %s OR br.borrow_id_code LIKE %s
        )"""
        like = f"%{search}%"
        params.extend([like, like, like, like])
    query += " ORDER BY br.request_date DESC"
    cur = mysql.connection.cursor()
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
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
    return row


def get_student_borrow_history(user_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT br.*, b.title AS book_title, b.cover_image,
               a.author_name,
               f.amount AS fine_amount, f.is_paid AS fine_paid
        FROM borrow_requests br
        JOIN books b ON br.book_id = b.book_id
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN fines f ON br.borrow_id = f.borrow_id
        WHERE br.user_id = %s
        ORDER BY br.request_date DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
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

def calculate_fine(borrow_id):
    """
    Calculate fine for overdue book: 1000 MMK per day.
    Returns (days_late, amount) tuple.
    Teachers have NO fines.
    """
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
        
    end = br["return_date"].date() if br["return_date"] else date.today()
    due = br["due_date"]
    if isinstance(due, str):
        due = date.fromisoformat(due)
    if end <= due:
        return 0, 0
    days = (end - due).days
    return days, days * 1000


def get_all_fines():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.*, u.name AS student_name, u.student_id,
               b.title AS book_title,
               br.due_date, br.return_date, br.borrow_id_code,
               br.borrowed_date
        FROM fines f
        JOIN users u ON f.user_id = u.user_id
        JOIN borrow_requests br ON f.borrow_id = br.borrow_id
        JOIN books b ON br.book_id = b.book_id
        ORDER BY f.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def add_fine(borrow_id, user_id, amount, reason="Late Return"):
    """Create one unpaid fine per borrow record; repeated returns are harmless."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT fine_id FROM fines WHERE borrow_id=%s AND is_paid=0 LIMIT 1", (borrow_id,))
    existing = cur.fetchone()
    if existing:
        cur.close()
        return existing["fine_id"]
    cur.execute("INSERT INTO fines (borrow_id, user_id, amount, reason) VALUES (%s, %s, %s, %s)", (borrow_id, user_id, amount, reason))
    mysql.connection.commit()
    fine_id = cur.lastrowid
    cur.close()
    return fine_id


def mark_fine_paid(fine_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE fines SET is_paid=1, paid_at=%s WHERE fine_id=%s",
        (datetime.now(), fine_id)
    )
    mysql.connection.commit()
    cur.close()


def get_fine_total():
    """Total unpaid fines amount."""
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount),0) AS total FROM fines WHERE is_paid=0"
    )
    row = cur.fetchone()
    cur.close()
    return float(row["total"] if row else 0)

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
