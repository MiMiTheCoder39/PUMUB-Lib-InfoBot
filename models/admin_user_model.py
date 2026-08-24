"""
models/admin_user_model.py
---------------------------
Admin Module — User Management DB functions
(Add / Edit / Delete / Activate / Deactivate Student accounts)
"""

from models.db import mysql


def get_all_users():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.*, f.faculty_name, f.department
        FROM users u
        LEFT JOIN faculties f ON u.faculty_id = f.faculty_id
        ORDER BY u.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def get_user_by_id_admin(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    return row


def create_user_admin(student_id, name, email, username, hashed_password, role, faculty_id):
    # Phase 6: application-layer gate — manual admin creation is
    # never permitted; the system keeps exactly one admin account.
    if (role or "student").lower() == "admin":
        return False
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO users (student_id,name,email,username,password,role,faculty_id,is_active)
           VALUES (%s,%s,%s,%s,%s,%s,%s,1)""",
        (student_id, name, email, username, hashed_password, role, faculty_id)
    )
    mysql.connection.commit()
    cur.close()


def update_user_admin(user_id, name, email, faculty_id):
    """Phase 6: the role is controlled by the official university
    record; the application layer guarantees exactly one admin
    account, so role changes are not permitted through this
    helper. """
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE users SET name=%s, email=%s, faculty_id=%s WHERE user_id=%s",
        (name, email, faculty_id, user_id)
    )
    mysql.connection.commit()
    cur.close()


def reset_user_password_admin(user_id, hashed_password):
    """Set a temporary password for a non-admin member from Admin Users."""
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE users SET password = %s WHERE user_id = %s AND role != 'admin'",
        (hashed_password, user_id),
    )
    changed = cur.rowcount == 1
    mysql.connection.commit()
    cur.close()
    return changed


def delete_user_admin(user_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()


def toggle_user_status(user_id, status):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_active=%s WHERE user_id=%s", (status, user_id))
    mysql.connection.commit()
    cur.close()

def get_inactive_users(months=6):
    """Fetch users who haven't logged in for X months."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.*, f.faculty_name, f.department
        FROM users u
        LEFT JOIN faculties f ON u.faculty_id = f.faculty_id
        WHERE u.role != 'admin'
          AND (u.last_login < DATE_SUB(NOW(), INTERVAL %s MONTH) OR (u.last_login IS NULL AND u.created_at < DATE_SUB(NOW(), INTERVAL %s MONTH)))
        ORDER BY u.last_login ASC
    """, (months, months))
    rows = cur.fetchall()
    cur.close()
    return rows

def bulk_delete_users(user_ids):
    """Delete multiple users at once."""
    if not user_ids:
        return
    cur = mysql.connection.cursor()
    format_strings = ','.join(['%s'] * len(user_ids))
    cur.execute(f"DELETE FROM users WHERE user_id IN ({format_strings}) AND role != 'admin'", tuple(user_ids))
    mysql.connection.commit()
    cur.close()


def get_admin_users(role=None, status=None, faculty_id=None, search=None, page=1, per_page=25):
    """Return real Admin user records with optional read-only filters and bounded pagination."""
    page = max(1, int(page or 1))
    per_page = min(100, max(1, int(per_page or 25)))
    where = ["1=1"]
    params = []
    if role in ("student", "teacher", "admin"):
        where.append("u.role = %s")
        params.append(role)
    if status == "active":
        where.append("u.is_active = 1")
    elif status == "inactive":
        where.append("u.is_active = 0")
    if faculty_id:
        where.append("u.faculty_id = %s")
        params.append(int(faculty_id))
    if search:
        like = f"%{search}%"
        where.append("(u.name LIKE %s OR u.username LIKE %s OR u.email LIKE %s OR u.student_id LIKE %s)")
        params.extend([like, like, like, like])

    base = f"""
        SELECT u.*, f.faculty_name, f.department,
               (SELECT COUNT(*) FROM borrow_requests br
                WHERE br.user_id = u.user_id AND br.status IN ('borrowed','overdue')) AS active_borrow_count,
               (SELECT COALESCE(SUM(fn.amount), 0) FROM fines fn
                JOIN borrow_requests br2 ON br2.borrow_id = fn.borrow_id
                WHERE br2.user_id = u.user_id AND fn.is_paid = 0) AS outstanding_fines
        FROM users u
        LEFT JOIN faculties f ON u.faculty_id = f.faculty_id
        WHERE {' AND '.join(where)}
        ORDER BY u.created_at DESC, u.user_id DESC
    """
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT COUNT(*) AS total FROM ({base}) AS matched_users", tuple(params))
    total = int(cur.fetchone()["total"] or 0)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    offset = (page - 1) * per_page
    cur.execute(base + " LIMIT %s OFFSET %s", tuple(params) + (per_page, offset))
    rows = cur.fetchall()
    cur.close()
    return {"records": rows, "total": total, "page": page, "pages": pages, "per_page": per_page}


def get_admin_user_summary():
    """Real role/status summary for Admin user cards."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
          COUNT(*) AS total,
          SUM(role = 'student') AS students,
          SUM(role = 'teacher') AS teachers,
          SUM(role = 'admin') AS admins,
          SUM(is_active = 1) AS active,
          SUM(is_active = 0) AS inactive
        FROM users
    """)
    row = cur.fetchone()
    cur.close()
    return row


def get_user_dependency_counts(user_id):
    """Return existing relationships before allowing a destructive user delete."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
          (SELECT COUNT(*) FROM borrow_requests WHERE user_id = %s) AS borrows,
          (SELECT COUNT(*) FROM fines WHERE user_id = %s) AS fines,
          (SELECT COUNT(*) FROM notifications WHERE user_id = %s) AS notifications
    """, (user_id, user_id, user_id))
    row = cur.fetchone()
    cur.close()
    return row


def get_user_safety(user_id, session_user_id=None):
    """Shared pre-delete safety validation used by both individual and
    bulk deletion (Phase 2). Never performs a deletion itself.

    Returns a dict:
      exists         - whether the user row exists
      is_admin       - whether the account holds the admin role
      is_self        - whether the account is the current session user
      is_active      - whether the account is active (active accounts
                       must be deactivated before deletion)
      dependencies   - dict of existing protected-data counts
                       (borrows, fines, notifications, bookmarks,
                        read_history, downloads)
      deletable      - True only when every rule passes
      reason         - machine-readable reason key ('none' when safe)
    """
    result = {
        "exists": False, "is_admin": False, "is_self": False,
        "is_active": False,
        "dependencies": {"borrows": 0, "fines": 0, "notifications": 0,
                         "bookmarks": 0, "read_history": 0, "downloads": 0},
        "deletable": False, "reason": "none",
    }
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        if user is None:
            result["reason"] = "user_not_found"
            return result
        result["exists"] = True
        result["is_admin"] = (user.get("role") or "").lower() == "admin"
        result["is_self"] = session_user_id is not None and user["user_id"] == session_user_id
        result["is_active"] = bool(user.get("is_active"))

        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM borrow_requests WHERE user_id = %s) AS borrows,
              (SELECT COUNT(*) FROM fines WHERE user_id = %s) AS fines,
              (SELECT COUNT(*) FROM notifications WHERE user_id = %s) AS notifications,
              (SELECT COUNT(*) FROM bookmarks WHERE user_id = %s) AS bookmarks,
              (SELECT COUNT(*) FROM read_history WHERE user_id = %s) AS read_history,
              (SELECT COUNT(*) FROM downloads WHERE user_id = %s) AS downloads
        """, (user_id, user_id, user_id, user_id, user_id, user_id))
        result["dependencies"] = dict(cur.fetchone())

        if result["is_admin"]:
            result["reason"] = "admin_delete_blocked"
        elif result["is_self"]:
            result["reason"] = "self_delete_blocked"
        elif result["is_active"]:
            result["reason"] = "active_user_delete_blocked"
        else:
            for name, count in result["dependencies"].items():
                if count:
                    result["reason"] = "dependencies_present"
                    break
            else:
                result["deletable"] = True
    finally:
        cur.close()
    return result

def delete_user_admin_safe(user_id, session_user_id=None):
    """Validate then delete a single user through the shared safety
    rules. Returns the same dict produced by get_user_safety, so the
    caller can inspect why a deletion was refused."""
    safety = get_user_safety(user_id, session_user_id)
    if safety["deletable"]:
        delete_user_admin(user_id)
    return safety

def bulk_delete_users_safe(user_ids, session_user_id=None):
    """Validate every selected id individually through the shared
    safety rules, delete only those that pass, and leave everything
    else untouched. Never deletes admin accounts, the current admin
    self-account, active users, or users with protected data, and an
    invalid id can never cause unrelated safe users to be deleted.

    Returns a dict {"removed": n, "skipped": n} with per-user identical
    safety validation (admin accounts, the self-account, active accounts
    and accounts with protected data are never deleted)."""
    deleted = 0
    skipped = 0
    for raw_id in user_ids:
        try:
            uid = int(raw_id)
        except (TypeError, ValueError):
            skipped += 1
            continue
        safety = get_user_safety(uid, session_user_id=session_user_id)
        if safety["deletable"]:
            delete_user_admin(uid)
            deleted += 1
        else:
            skipped += 1
    return {"removed": deleted, "skipped": skipped}
