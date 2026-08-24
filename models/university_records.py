"""
models/university_records.py
-----------------------------
Official university enrollment records (Phase H master/reference table).

This is the authoritative source for NEW registration identity
verification. The registration flow looks UP a record by
(university_email, university_id). Record management (listing,
searching, filtering, creating, editing, activating/deactivating)
is an ADMIN responsibility implemented below; no permanent deletion
exists — records are managed through Active/Inactive status so that
historical official identity records are always preserved.

Existing `users` login accounts are NOT stored here and must not be
migrated into this table.
"""

import re

from models.db import mysql

VALID_ROLES = ("student", "teacher")
VALID_STATUSES = ("active", "inactive", "graduated", "suspended")


def get_record_by_email(email: str):
    """Exact case-insensitive match by official email only (Phase J).

    Teachers carry no university ID, so registration verification
    matches the submitted email alone. Returns a single dict row or
    None (None = "no match" -- never raises).
    """
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            """SELECT record_id, university_email, university_id, full_name,
                      faculty_id, department, year, role, is_active,
                      status
               FROM university_records
               WHERE LOWER(university_email) = LOWER(%s)
               LIMIT 1""",
            (email,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
    return row


def get_record_by_email_id(email: str, university_id: str):
    """Exact-match lookup (case-insensitive on both fields).

    Returns a single dict row or None. Used by registration
    verification (utils/identity_check). Raises nothing — query
    errors propagate as normal Flask 500 paths (None = "no match").
    """
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            """SELECT record_id, university_email, university_id, full_name,
                      faculty_id, department, year, role, is_active,
                      status
               FROM university_records
               WHERE LOWER(university_email) = LOWER(%s)
                 AND LOWER(university_id) = LOWER(%s)
               LIMIT 1""",
            (email, university_id),
        )
        row = cur.fetchone()
    finally:
        cur.close()
    return row


# ============================================================
# ADMIN MANAGEMENT (Phase I)
# ============================================================


def get_all_faculties():
    """Faculties for dropdowns (shared with user management)."""
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT faculty_id, faculty_name, department FROM faculties "
            "ORDER BY faculty_name"
        )
        return cur.fetchall()
    finally:
        cur.close()


def get_records(search=None, role=None, faculty_id=None, status=None,
                page=1, per_page=25):
    """List with search + filters + pagination (admin page style).

    Returns a dict: records / total / page / pages.
    search -> LIKE over university_id, university_email, full_name.
    All parameters are sanitized/parameterized.
    """
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = max(1, min(100, int(per_page)))
    except (TypeError, ValueError):
        per_page = 25

    where = []
    params = []
    if search:
        where.append(
            "(ur.university_id LIKE %s OR ur.university_email LIKE %s "
            "OR ur.full_name LIKE %s)"
        )
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if role in VALID_ROLES:
        where.append("ur.role = %s")
        params.append(role)
    try:
        faculty_id = int(faculty_id)
        where.append("ur.faculty_id = %s")
        params.append(faculty_id)
    except (TypeError, ValueError):
        faculty_id = None
    if status in VALID_STATUSES:
        where.append("ur.status = %s")
        params.append(status)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    join_sql = (
        " LEFT JOIN faculties f ON f.faculty_id = ur.faculty_id"
    )
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) AS c FROM university_records ur" + where_sql,
            params,
        )
        total = cur.fetchone()["c"]
        cur.execute(
            """SELECT ur.record_id, ur.university_email, ur.university_id,
                      ur.full_name, ur.faculty_id, ur.department, ur.year,
                      ur.role, ur.status, ur.created_at, ur.updated_at,
                      f.faculty_name
               FROM university_records ur"""
            + join_sql
            + where_sql
            + " ORDER BY ur.record_id DESC LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        records = cur.fetchall()
        # Live Registered / Not-Registered badge (one record -> one account).
        for rec in records:
            rec["registered"] = bool(
                count_users_registered_from_email(rec["university_email"])
            )
    finally:
        cur.close()
    pages = max(1, (total + per_page - 1) // per_page)
    return {"records": records, "total": total, "page": page, "pages": pages}


def get_record_counts():
    """Live counts for the segmented role tabs (admin V2 polish).

    Returns a dict with total / students / teachers counts. Read-only,
    one query — kept cheap for every page load.
    """
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) AS c, "
            "SUM(ur.role = 'student') AS s, "
            "SUM(ur.role = 'teacher') AS t "
            "FROM university_records ur"
        )
        row = cur.fetchone()
        return {
            "record_summary": {
                "total": int(row["c"] or 0),
                "students": int(row["s"] or 0),
                "teachers": int(row["t"] or 0),
            }
        }
    finally:
        cur.close()


def get_record_by_id(record_id):
    """Single record lookup by primary key (admin edit view)."""
    try:
        record_id = int(record_id)
    except (TypeError, ValueError):
        return None
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            """SELECT ur.record_id, ur.university_email, ur.university_id,
                      ur.full_name, ur.faculty_id, ur.department, ur.year,
                      ur.role, ur.status, ur.created_at, ur.updated_at,
                      f.faculty_name
               FROM university_records ur
               LEFT JOIN faculties f ON f.faculty_id = ur.faculty_id
               WHERE ur.record_id = %s LIMIT 1""",
            (record_id,),
        )
        row = cur.fetchone()
        if row is not None:
            row["registered"] = bool(
                count_users_registered_from_email(row["university_email"])
            )
        return row
    finally:
        cur.close()


def count_users_registered_from_email(email):
    """How many users accounts share this record's email (Phase I
    identity-lock + no-delete guard). Case-insensitive match."""
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) AS c FROM users "
            "WHERE LOWER(email) = LOWER(%s)",
            (email,),
        )
        return cur.fetchone()["c"]
    finally:
        cur.close()


def _email_exists(email, exclude_record_id=None):
    cur = mysql.connection.cursor()
    try:
        if exclude_record_id:
            cur.execute(
                "SELECT record_id FROM university_records "
                "WHERE LOWER(university_email) = LOWER(%s) "
                "AND record_id != %s LIMIT 1",
                (email, exclude_record_id),
            )
        else:
            cur.execute(
                "SELECT record_id FROM university_records "
                "WHERE LOWER(university_email) = LOWER(%s) LIMIT 1",
                (email,),
            )
        return cur.fetchone() is not None
    finally:
        cur.close()


def _id_exists(university_id, exclude_record_id=None):
    cur = mysql.connection.cursor()
    try:
        if exclude_record_id:
            cur.execute(
                "SELECT record_id FROM university_records "
                "WHERE LOWER(university_id) = LOWER(%s) "
                "AND record_id != %s LIMIT 1",
                (university_id, exclude_record_id),
            )
        else:
            cur.execute(
                "SELECT record_id FROM university_records "
                "WHERE LOWER(university_id) = LOWER(%s) LIMIT 1",
                (university_id,),
            )
        return cur.fetchone() is not None
    finally:
        cur.close()


def _is_valid_email(email):
    return bool(email and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def create_record(university_email, university_id, full_name, role,
                  faculty_id=None, department=None, year=None,
                  is_active=1, status=None):
    """Create a new official record.

    Returns (record_id, None) on success or (None, error_key) where
    Phase J -- Student records MUST carry a university ID; Teacher
    records may omit it (university_id = NULL). Missing ID for a
    student returns the role-dependent error "missing_student_id".
    Returns (record_id, None) on success or (None, error_key) where
    error_key is one of: missing_fields, missing_student_id,
    invalid_email, invalid_role, invalid_faculty, duplicate_email,
    duplicate_id.
    invalid_faculty, duplicate_email, duplicate_id.
    """
    university_email = (university_email or "").strip()
    # Defensive: an empty-string ID must be treated as NULL — many
    # teachers carry no ID, and a stale "" row must never collide.
    university_id = (university_id or "").strip() or None
    full_name = (full_name or "").strip()
    if not all([university_email, full_name]):
        return None, "missing_fields"
    # Phase J: students must have a university ID; teachers may not.
    if role == "student" and not university_id:
        return None, "missing_student_id"
    if not _is_valid_email(university_email):
        return None, "invalid_email"
    if role not in VALID_ROLES:
        return None, "invalid_role"
    if faculty_id not in (None, ""):
        try:
            faculty_id = int(faculty_id)
        except (TypeError, ValueError):
            return None, "invalid_faculty"
        faculties = get_all_faculties()
        if not any(int(f["faculty_id"]) == faculty_id for f in faculties):
            return None, "invalid_faculty"
    else:
        faculty_id = None
    if _email_exists(university_email):
        return None, "duplicate_email"
    if _id_exists(university_id):
        return None, "duplicate_id"
    try:
        is_active = 1 if int(is_active) else 0
    except (TypeError, ValueError):
        is_active = 1
    if status is None or status not in VALID_STATUSES:
        status = "active"
    department = (department or "").strip() or None
    year = (year or "").strip() or None
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            """INSERT INTO university_records
               (university_email, university_id, full_name, faculty_id,
                department, year, role, is_active, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (university_email, university_id, full_name, faculty_id,
             department, year, role, is_active, status),
        )
        record_id = cur.lastrowid
        mysql.connection.commit()
        return record_id, None
    finally:
        cur.close()


def update_record(record_id, university_email, university_id, full_name,
                  role, faculty_id=None, department=None, year=None,
                  is_active=None, lock_identity=False, status=None):
    """Update an existing record.

    lock_identity=True (record already has a registered users account)
    -> email, university_id, full_name and faculty_id changes are
    IGNORED and restored from the current record (server-side guard);
    the route must still never accept forged identity fields, but the
    model double-enforces the lock.

    Returns (rows_affected, None) or (None, error_key) with the same
    Phase J -- Student records MUST carry a university ID; Teacher
    records may omit it (university_id = NULL). Returns
    (rows_affected, None) or (None, error_key) with the same error
    vocabulary as create_record (plus "not_found"). is_active is only
    changed when explicitly provided (None leaves it untouched).
    explicitly provided (None leaves it untouched).
    """
    record = get_record_by_id(record_id)
    if not record:
        return None, "not_found"
    university_email = (university_email or "").strip()
    university_id = (university_id or "").strip()
    full_name = (full_name or "").strip()
    if not all([university_email, full_name]):
        return None, "missing_fields"
    # Phase J: students must have a university ID; teachers may not.
    if role == "student" and not university_id:
        return None, "missing_student_id"
    if not _is_valid_email(university_email):
        return None, "invalid_email"
    if role not in VALID_ROLES:
        return None, "invalid_role"
    if faculty_id not in (None, ""):
        try:
            faculty_id = int(faculty_id)
        except (TypeError, ValueError):
            return None, "invalid_faculty"
        faculties = get_all_faculties()
        if not any(int(f["faculty_id"]) == faculty_id for f in faculties):
            return None, "invalid_faculty"
    else:
        faculty_id = None
    if not lock_identity:
        if _email_exists(university_email, exclude_record_id=record_id):
            return None, "duplicate_email"
        # NULL/empty IDs never collide (many teachers carry no ID).
        if university_id and _id_exists(
                university_id, exclude_record_id=record_id):
            return None, "duplicate_id"
    else:
        # Identity locked: normalize to the current values regardless
        # of what the client submitted.
        university_email = record["university_email"]
        university_id = record["university_id"]
        full_name = record["full_name"]
        faculty_id = record.get("faculty_id")
        # The official role is part of the verified identity — once an
        # account is registered from this record, the role is locked too.
        role = record["role"]
    department = (department or "").strip() or None
    year = (year or "").strip() or None
    if status is not None and status not in VALID_STATUSES:
        status = record.get("status") or "active"
    if status is None:
        status = record.get("status") or "active"
    cur = mysql.connection.cursor()
    try:
        if is_active is None:
            cur.execute(
                """UPDATE university_records
                   SET university_email = %s, university_id = %s,
                       full_name = %s, faculty_id = %s, department = %s,
                       year = %s, role = %s, status = %s
                   WHERE record_id = %s""",
                (university_email, university_id, full_name, faculty_id,
                 department, year, role, status, record_id),
            )
        else:
            try:
                is_active = 1 if int(is_active) else 0
            except (TypeError, ValueError):
                is_active = record["is_active"]
            cur.execute(
                """UPDATE university_records
                   SET university_email = %s, university_id = %s,
                       full_name = %s, faculty_id = %s, department = %s,
                       year = %s, role = %s, is_active = %s, status = %s
                   WHERE record_id = %s""",
                (university_email, university_id, full_name, faculty_id,
                 department, year, role, is_active, status, record_id),
            )
        rows = cur.rowcount
        mysql.connection.commit()
        return rows, None
    finally:
        cur.close()


def set_record_status(record_id, status):
    """Set the four-state status of a record (Active / Inactive /
    Graduated / Suspended).

    Returns the refreshed record dict on success or None when the
    record does not exist / the status is invalid. No other column is
    touched; updated_at is stamped by the database trigger/path below.
    """
    record = get_record_by_id(record_id)
    if not record:
        return None
    if status not in VALID_STATUSES:
        return None
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "UPDATE university_records SET status = %s, "
            "updated_at = NOW() WHERE record_id = %s",
            (status, record_id),
        )
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        return None
    finally:
        cur.close()
    return get_record_by_id(record_id)


def set_record_active(record_id, is_active):
    """Activate/deactivate a record (toggle semantics). Legacy 2-state
    helper retained for backward compatibility; routes now use the
    four-state set_record_status instead.

    Returns (rows_affected, None) or (None, "not_found").
    No other column is touched.
    """
    record = get_record_by_id(record_id)
    if not record:
        return None, "not_found"
    try:
        is_active = 1 if int(is_active) else 0
    except (TypeError, ValueError):
        return None, "invalid_status"
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "UPDATE university_records SET is_active = %s "
            "WHERE record_id = %s",
            (is_active, record_id),
        )
        rows = cur.rowcount
        mysql.connection.commit()
        return rows, None
    finally:
        cur.close()


def get_record_safety(record_id):
    """Shared pre-delete safety validation for a university record
    (Phase 2). Never performs a deletion itself.

    Returns a dict:
      exists      - whether the record exists
      registered  - whether it is linked to a registered user account
      deletable   - True only when the record exists, is not
                    registered, and is safe to remove
      reason      - machine-readable reason key ('none' when safe)
    """
    result = {"exists": False, "registered": False,
              "deletable": False, "reason": "none"}
    record = get_record_by_id(record_id)
    if record is None:
        result["reason"] = "record_not_found"
        return result
    result["exists"] = True
    result["registered"] = bool(record.get("registered"))
    if result["registered"]:
        # A registered record is permanently protected: it drives the
        # official user account and must never be deleted.
        result["reason"] = "registered_record_blocked"
    else:
        result["deletable"] = True
    return result

def delete_record_safe(record_id):
    """Validate then delete a single university record through the
    shared safety rules. Returns the same dict produced by
    get_record_safety so the caller can inspect refusals."""
    safety = get_record_safety(record_id)
    if safety["deletable"]:
        cur = mysql.connection.cursor()
        try:
            cur.execute("DELETE FROM university_records WHERE record_id = %s", (record_id,))
            mysql.connection.commit()
        finally:
            cur.close()
    return safety
