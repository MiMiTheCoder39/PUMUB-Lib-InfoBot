"""
models/notification_model.py
------------------------------
Notification system — supports borrow workflow notifications.

Types:
  new_book         - Admin adds new book → all students
  announcement     - Admin posts announcement → all students
  due_reminder     - Book due date reminder
  borrow_approved  - Borrow request approved + Borrow ID
  borrow_issued    - Book physically issued
  borrow_returned  - Book returned confirmation
  borrow_overdue   - Book is overdue
  fine_added       - Fine added to account
  system           - General system notification
"""

from models.db import mysql


def create_notification(user_id, title, message, ntype="system", borrow_id=None):
    """Send a notification and optionally associate it with one borrow record."""
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO notifications (user_id, borrow_id, title, message, type)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, borrow_id, title, message, ntype))
    mysql.connection.commit()
    cur.close()


def notify_all_students(title, message, ntype="system"):
    """Send notification to all active students."""
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT user_id FROM users WHERE role='student' AND is_active=1"
    )
    students = cur.fetchall()
    for s in students:
        cur.execute("""
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (%s, %s, %s, %s)
        """, (s["user_id"], title, message, ntype))
    mysql.connection.commit()
    cur.close()


# ─── BORROW-SPECIFIC NOTIFICATIONS ───────────────────────────

def notify_borrow_request_submitted(user_id, book_title, borrow_id=None):
    create_notification(
        user_id,
        "Borrow Request Submitted",
        f'"{book_title}" အတွက် Borrow Request တင်ပြီးပါပြီ။ Admin approval ကို စောင့်ပါ။',
        "borrow_request",
        borrow_id,
    )


def notify_borrow_approved(user_id, student_name, book_title, borrow_id_code, borrow_id=None):
    """
    Sent when admin approves borrow request.
    Tells student their Borrow ID and to visit library.
    """
    title = f"✅ Borrow Request Approved — {borrow_id_code}"
    message = (
        f"မင်္ဂလာပါ {student_name}!\n\n"
        f'"{book_title}" စာအုပ် Borrow Request ကို Admin က Approve ပြုလုပ်ပြီးပါပြီ။\n\n'
        f"📋 သင်၏ Borrow ID: {borrow_id_code}\n\n"
        f"Library သို့ သွားရောက်ပြီး ဤ Borrow ID ကို Admin ထံ ပြသပါ။\n"
        f"Admin က QR Code Scan ပြုလုပ်ပြီး စာအုပ် ထုတ်ပေးပါမည်။"
    )
    create_notification(user_id, title, message, "borrow_approved", borrow_id)


def notify_borrow_issued(user_id, student_name, book_title,
                         borrow_id_code, borrowed_date, due_date, borrow_id=None):
    """
    Sent when admin physically issues the book (status = borrowed).
    """
    title = f"📚 Book Issued — {book_title}"
    message = (
        f"မင်္ဂလာပါ {student_name}!\n\n"
        f'"{book_title}" စာအုပ်ကို ထုတ်ပေးပြီးပါပြီ။\n\n'
        f"📋 Borrow ID  : {borrow_id_code}\n"
        f"📅 Borrow Date: {borrowed_date}\n"
        f"⏰ Due Date   : {due_date}\n\n"
        f"ကျေးဇူးပြု၍ Due Date မတိုင်မီ ပြန်အပ်ပေးပါ။\n"
        f"နောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။"
    )
    create_notification(user_id, title, message, "borrow_issued", borrow_id)


def notify_borrow_returned(user_id, student_name, book_title, borrow_id_code, borrow_id=None):
    """Sent when book is returned."""
    title = f"✅ Book Returned — {book_title}"
    message = (
        f"မင်္ဂလာပါ {student_name}!\n\n"
        f'"{book_title}" ({borrow_id_code}) ကို ပြန်အပ်ပြီးကြောင်း '
        f"မှတ်တမ်းတင်ပြီးပါပြီ။\n"
        f"ငှားယူသောကြောင့် ကျေးဇူးတင်ပါသည်။"
    )
    create_notification(user_id, title, message, "borrow_returned", borrow_id)


def notify_borrow_overdue(user_id, student_name, book_title,
                          borrow_id_code, due_date, days_late, fine_amount, borrow_id=None):
    """Sent when book becomes overdue."""
    title = f"⚠️ Overdue Book — {book_title}"
    message = (
        f"မင်္ဂလာပါ {student_name}!\n\n"
        f'"{book_title}" ({borrow_id_code}) ကို Due Date ({due_date}) ကျော်လွန်ပြီ\n\n'
        f"⏰ နောက်ကျသောရက်  : {days_late} ရက်\n"
        f"💰 Fine Amount   : {fine_amount:,} MMK\n\n"
        f"ကျေးဇူးပြု၍ ချက်ချင်း Library သို့ ပြန်အပ်ပေးပါ။"
    )
    create_notification(user_id, title, message, "borrow_overdue", borrow_id)


def notify_fine_added(user_id, student_name, book_title,
                      borrow_id_code, days_late, fine_amount, borrow_id=None):
    """Sent when fine is added."""
    title = f"💰 Fine Notice — {borrow_id_code}"
    message = (
        f"မင်္ဂလာပါ {student_name}!\n\n"
        f'"{book_title}" ({borrow_id_code}) အတွက် Fine ကောက်ခံပါသည်။\n\n'
        f"⏰ နောက်ကျသောရက်  : {days_late} ရက်\n"
        f"💰 Fine Amount   : {fine_amount:,} MMK\n"
        f"   (1,000 MMK × {days_late} days)\n\n"
        f"Library တွင် Fine ပေးချေပြီး စာအုပ် ပြန်အပ်ပေးပါ။"
    )
    create_notification(user_id, title, message, "fine_added", borrow_id)


# ─── QUERY FUNCTIONS ─────────────────────────────────────────

def get_user_notifications(user_id, limit=30):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_unread_count(user_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=%s AND is_read=0",
        (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    return row["cnt"] if row else 0


def mark_all_read(user_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE notifications SET is_read=1 WHERE user_id=%s AND is_read=0",
        (user_id,)
    )
    mysql.connection.commit()
    cur.close()


def mark_one_read(notification_id, user_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE notifications SET is_read=1 WHERE notification_id=%s AND user_id=%s",
        (notification_id, user_id)
    )
    mysql.connection.commit()
    cur.close()


def send_due_reminders():
    """Send at most one overdue reminder per borrow per calendar day."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT br.borrow_id, br.user_id, br.due_date,
               br.borrow_id_code, b.title, u.name AS student_name, u.role
        FROM borrow_requests br
        JOIN books b ON br.book_id = b.book_id
        JOIN users u ON br.user_id = u.user_id
        WHERE br.status IN ('borrowed','overdue')
          AND br.due_date < CURDATE()
          AND NOT EXISTS (
              SELECT 1 FROM notifications n
              WHERE n.user_id = br.user_id
                AND n.borrow_id = br.borrow_id
                AND n.type = 'borrow_overdue'
                AND DATE(n.created_at) = CURDATE()
          )
    """)
    records = cur.fetchall()
    from datetime import date
    for r in records:
        days = (date.today() - r["due_date"]).days
        fine = 0 if r.get("role") == "teacher" else days * 1000
        notify_borrow_overdue(
            r["user_id"], r["student_name"], r["title"],
            r["borrow_id_code"] or str(r["borrow_id"]),
            str(r["due_date"]), days, fine, r["borrow_id"]
        )
    cur.close()
    return len(records)


def notify_due_date_approaching(user_id, student_name, book_title,
                                borrow_id_code, due_date, days_remaining, borrow_id=None):
    """
    Sent when book due date is approaching (within 3 days).
    Reminder to return book before due date.
    """
    title = f"📅 Due Date Reminder — {book_title}"
    message = (
        f"မင်္ဂလာပါ {student_name}!\n\n"
        f'"{book_title}" ({borrow_id_code}) စာအုပ်ကို '
        f"ပြန်အပ်ရန် {days_remaining} ရက်သာ ကျန်ပါသည်။\n\n"
        f"📅 Due Date: {due_date}\n\n"
        f"ကျေးဇူးပြု၍ Due Date မတိုင်မီ Library သို့ ပြန်အပ်ပေးပါ။\n"
        f"နောက်ကျပါက 1,000 MMK/day Fine ကောက်ခံပါမည်။"
    )
    create_notification(user_id, title, message, "due_reminder", borrow_id)


def send_due_date_reminders(days_before=3):
    """
    Send reminder notifications for books due within N days.
    Call this daily via scheduled task.
    """
    from models.db import mysql as _mysql
    from datetime import date, timedelta
    
    cur = _mysql.connection.cursor()
    target_date = date.today() + timedelta(days=days_before)
    
    cur.execute("""
        SELECT br.borrow_id, br.user_id, br.due_date,
               br.borrow_id_code, b.title, u.name AS student_name, u.role
        FROM borrow_requests br
        JOIN books b ON br.book_id = b.book_id
        JOIN users u ON br.user_id = u.user_id
        WHERE br.status = 'borrowed'
          AND br.due_date = %s
          AND NOT EXISTS (
            SELECT 1 FROM notifications
            WHERE user_id = br.user_id
              AND borrow_id = br.borrow_id
              AND type = 'due_reminder'
              AND created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
          )
    """, (target_date,))
    
    records = cur.fetchall()
    for r in records:
        days_remaining = (r["due_date"] - date.today()).days
        notify_due_date_approaching(
            r["user_id"], r["student_name"], r["title"],
            r["borrow_id_code"] or str(r["borrow_id"]),
            str(r["due_date"]), days_remaining, r["borrow_id"]
        )
    
    cur.close()
    return len(records)
