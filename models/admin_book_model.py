"""
models/admin_book_model.py
---------------------------
Admin Module — Book / Category / Author / Faculty CRUD functions

Phase 1 (Book System) changes:
- Books support three valid availability states (Physical Only / Digital
  Only / Hybrid). A book MUST have at least one of is_physical or
  pdf_file; the invalid state (no physical copies, no PDF) is rejected
  server-side by add_book / update_book.
- pdf_file is now optional (Migration 004 makes the column nullable).
- Category/Faculty alignment is validated server-side: a submitted
  category_id must either be unassigned (NULL faculty linkage — valid
  for every department) or belong to the submitted faculty_id.
"""

from models.db import mysql

# ─── BOOKS ───────────────────────────────────────────────────

class BookStateError(ValueError):
    """Raised when a book payload fails the valid-state rule
    (must be physical and/or digital) or the category alignment rule."""


def _validate_book_state(is_physical: bool, pdf_file) -> None:
    """Server-side gate: a book must be physical, digital, or both.
    Physical is True when the row claims stock (is_physical=1).
    Digital is True when a PDF file is stored.
    """
    if not is_physical and not pdf_file:
        raise BookStateError("invalid_book_state")
    if pdf_file and not isinstance(pdf_file, str):
        raise BookStateError("invalid_book_state")


def _validate_category_alignment(category_id, faculty_id) -> None:
    """Server-side gate for Department -> Category assignment.
    A category whose faculty_id is NULL is usable under any department
    (Migration 003 semantics). A linked category must match the
    submitted faculty.
    """
    if not category_id:
        return
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        raise BookStateError("invalid_category")

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT faculty_id FROM categories WHERE category_id = %s",
        (category_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        raise BookStateError("invalid_category")

    linked_faculty = row["faculty_id"]
    if linked_faculty is None:
        return  # unassigned categories are valid for every department

    if faculty_id is None:
        raise BookStateError("category_faculty_mismatch")
    try:
        faculty_id = int(faculty_id)
    except (TypeError, ValueError):
        raise BookStateError("invalid_department")
    if int(linked_faculty) != faculty_id:
        raise BookStateError("category_faculty_mismatch")


def _validate_physical_copies(total_copies, book_id=None) -> int:
    """Copies must be a non-negative integer and must not drop below the
    number of copies currently out on active borrows (prevents a
    silently shrinking stock while books are still issued)."""
    try:
        total_copies = int(total_copies)
    except (TypeError, ValueError):
        total_copies = 0
    total_copies = max(0, total_copies)

    cur = mysql.connection.cursor()
    try:
        cur.execute(
            """SELECT COUNT(*) AS out_count
               FROM borrow_requests
               WHERE book_id = %s AND status IN ('approved', 'borrowed', 'overdue')""",
            (book_id,),
        )
        out_count = int(cur.fetchone()["out_count"])
    finally:
        cur.close()

    if total_copies < out_count:
        raise BookStateError("copies_below_borrowed")
    return total_copies


def add_book(title, isbn, author_name, author_id, category_id, faculty_id, description,
             resource_type, pdf_file, cover_image, publish_date, total_copies,
             is_physical, publisher=None, edition=None, publication_year=None):
    _validate_book_state(bool(is_physical), pdf_file)
    _validate_category_alignment(category_id, faculty_id)
    total_copies = _validate_physical_copies(total_copies)

    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO books
           (title,isbn,author_name,author_id,category_id,faculty_id,description,resource_type,
            publisher,edition,publication_year,
            pdf_file,cover_image,publish_date,total_copies,available_copies,is_physical)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (title, isbn, author_name, author_id, category_id, faculty_id, description, resource_type,
         publisher, edition, publication_year,
         pdf_file, cover_image, publish_date, total_copies, total_copies, 1 if is_physical else 0)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id


def update_book(book_id, title, isbn, author_name, author_id, category_id, faculty_id, description,
                resource_type, publish_date, total_copies,
                pdf_file=None, cover_image=None,
                is_physical=None, remove_pdf=False,
                publisher=None, edition=None, publication_year=None):
    cur = mysql.connection.cursor()

    # --- Resolve the effective PDF value ------------------------
    # Stored PDF ကို အမြဲဆွဲယူရမည့် — pdf ဖြုတ်ခြင်းအတွက်လည်း နှိုင်းယှဉ်ရန် လိုသည်။
    cur.execute("SELECT pdf_file FROM books WHERE book_id = %s", (book_id,))
    row = cur.fetchone()
    stored_pdf = row["pdf_file"] if row else None

    if remove_pdf:
        current_pdf = None  # explicit, intentional removal
    else:
        current_pdf = stored_pdf

    effective_pdf = pdf_file if pdf_file else current_pdf
    pdf_changed = effective_pdf != stored_pdf

    # --- Resolve the effective is_physical value ----------------
    if is_physical is None:
        cur.execute("SELECT is_physical FROM books WHERE book_id = %s", (book_id,))
        row = cur.fetchone()
        is_physical = bool(int(row["is_physical"])) if row else False

    # --- Server-side gates --------------------------------------
    _validate_book_state(bool(is_physical), effective_pdf)
    _validate_category_alignment(category_id, faculty_id)
    total_copies = _validate_physical_copies(total_copies, book_id)

    # --- Build the update ---------------------------------------
    sets = ["title=%s", "isbn=%s", "author_name=%s", "author_id=%s", "category_id=%s",
            "faculty_id=%s", "description=%s", "resource_type=%s", "publish_date=%s",
            "total_copies=%s", "is_physical=%s"]
    values = [title, isbn, author_name, author_id, category_id, faculty_id, description,
              resource_type, publish_date, total_copies, 1 if is_physical else 0]

    for col, val in (("publisher", publisher), ("edition", edition),
                     ("publication_year", publication_year)):
        sets.append(f"{col}=%s")
        values.append(val)

    # Only write pdf_file when it actually changes (preserve otherwise)
    if pdf_changed:
        sets.append("pdf_file=%s")
        values.append(effective_pdf)

    # Only write cover_image when a replacement was provided
    if cover_image:
        sets.append("cover_image=%s")
        values.append(cover_image)

    values.append(book_id)
    cur.execute(f"""UPDATE books SET {','.join(sets)} WHERE book_id=%s""", tuple(values))
    mysql.connection.commit()
    cur.close()


def delete_book(book_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM books WHERE book_id=%s", (book_id,))
    mysql.connection.commit()
    cur.close()


def update_book_qr(book_id, qr_filename):
    """Legacy helper kept for compatibility. Book QR generation is retired
    from the active Admin flow per the approved Phase plan (Borrow QR,
    the physical-borrow workflow, is a separate untouched system)."""
    cur = mysql.connection.cursor()
    cur.execute("UPDATE books SET qr_code=%s WHERE book_id=%s", (qr_filename, book_id))
    mysql.connection.commit()
    cur.close()


# ─── CATEGORIES ──────────────────────────────────────────────
def add_category(name, description=""):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO categories (category_name,description) VALUES (%s,%s)", (name, description))
    mysql.connection.commit()
    cur.close()


def update_category(cat_id, name, description):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE categories SET category_name=%s,description=%s WHERE category_id=%s",
                (name, description, cat_id))
    mysql.connection.commit()
    cur.close()


def delete_category(cat_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM categories WHERE category_id=%s", (cat_id,))
    mysql.connection.commit()
    cur.close()


# ─── AUTHORS ────────────────────────────────────────────────
def get_author_by_id(author_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM authors WHERE author_id=%s", (author_id,))
    row = cur.fetchone()
    cur.close()
    return row


def add_author(name, bio=""):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO authors (author_name,bio) VALUES (%s,%s)", (name, bio))
    mysql.connection.commit()
    cur.close()


def update_author(author_id, name, bio):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE authors SET author_name=%s,bio=%s WHERE author_id=%s",
                (name, bio, author_id))
    mysql.connection.commit()
    cur.close()


def delete_author(author_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM authors WHERE author_id=%s", (author_id,))
    mysql.connection.commit()
    cur.close()


# ─── FACULTIES ──────────────────────────────────────────────
def get_all_faculties_admin():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM faculties ORDER BY faculty_name, department")
    rows = cur.fetchall()
    cur.close()
    return rows


def add_faculty(faculty_name, department):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO faculties (faculty_name,department) VALUES (%s,%s)",
                (faculty_name, department))
    mysql.connection.commit()
    cur.close()


def update_faculty(faculty_id, faculty_name, department):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE faculties SET faculty_name=%s,department=%s WHERE faculty_id=%s",
                (faculty_name, department, faculty_id))
    mysql.connection.commit()
    cur.close()


def delete_faculty(faculty_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM faculties WHERE faculty_id=%s", (faculty_id,))
    mysql.connection.commit()
    cur.close()


# ─── ADMIN LIST HELPERS ─────────────────────────────────────
def get_admin_book_page(search=None, category_id=None, faculty_id=None, availability=None,
                        resource_type=None, page=1, per_page=25, faculty_ids=None):
    where = []
    params = []
    if search:
        like = f"%{search}%"
        where.append("(b.title LIKE %s OR b.author_name LIKE %s OR b.isbn LIKE %s)")
        params.extend([like, like, like])
    if category_id:
        where.append("b.category_id = %s")
        params.append(int(category_id))
    if faculty_ids:
        ids = [int(v) for v in faculty_ids if int(v) > 0]
        if ids:
            where.append("b.faculty_id IN (%s)" % ",".join("%s" for _ in ids))
            params.extend(ids)
    elif faculty_id:
        where.append("b.faculty_id = %s")
        params.append(int(faculty_id))
    if resource_type:
        where.append("b.resource_type = %s")
        params.append(resource_type)
    if availability == "physical":
        where.append("b.is_physical = 1")
    elif availability == "digital":
        where.append("b.pdf_file IS NOT NULL")
    elif availability == "available":
        where.append("COALESCE(b.available_copies, 0) > 0")
    elif availability == "borrowed":
        where.append("COALESCE(b.available_copies, 0) < COALESCE(b.total_copies, 0)")
    elif availability == "unavailable":
        where.append("(COALESCE(b.available_copies, 0) = 0 AND b.pdf_file IS NULL)")

    # Phase 3 archive lifecycle: Active / All views never list archived books.
    where.append("COALESCE(b.is_archived, 0) = 0")

    where_sql = (" AND " + " AND ".join(where)) if where else ""
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT COUNT(*) AS total FROM books b WHERE 1=1{where_sql}", tuple(params))
    total = int(cur.fetchone()["total"])

    pages = max(1, -(-total // per_page))
    page = max(1, min(int(page), pages))
    offset = (page - 1) * per_page

    cur.execute(
        f"""SELECT b.book_id, b.title, b.isbn, b.author_name AS books_author_name,
                   b.author_id, b.category_id, b.faculty_id, b.description,
                   b.resource_type, b.publisher, b.edition, b.publication_year,
                   b.pdf_file, b.cover_image, b.qr_code,
                   b.total_copies, b.available_copies, b.publish_date,
                   b.view_count, b.download_count, b.upload_date, b.updated_at,
                   b.is_physical,
                   COALESCE(a.author_name) AS authors_author_name,
                   c.category_name, f.faculty_name, f.department,
                   (SELECT COUNT(*) FROM borrow_requests br
                      WHERE br.book_id = b.book_id
                        AND br.status IN ('approved','borrowed','overdue')) AS active_borrow_count
            FROM books b
            LEFT JOIN authors a ON b.author_id = a.author_id
            LEFT JOIN categories c ON b.category_id = c.category_id
            LEFT JOIN faculties f ON b.faculty_id = f.faculty_id
            WHERE 1=1{where_sql}
            ORDER BY b.upload_date DESC, b.book_id DESC
            LIMIT %s OFFSET %s""",
        tuple(params) + (per_page, offset),
    )
    records = cur.fetchall()
    cur.close()
    return {"records": records, "total": total, "page": page, "pages": pages, "per_page": per_page}


def get_admin_book_summary():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT COUNT(*) AS total_books,
               SUM(total_copies) AS total_copies,
               SUM(available_copies) AS available_copies,
               SUM(CASE WHEN is_physical = 1 THEN 1 ELSE 0 END) AS physical_books,
               SUM(CASE WHEN pdf_file IS NOT NULL THEN 1 ELSE 0 END) AS digital_books,
               SUM(CASE WHEN resource_type <> 'book' THEN 1 ELSE 0 END) AS other_types,
               (SELECT COUNT(*) FROM borrow_requests WHERE status IN ('borrowed','overdue')) AS borrowed_books,
               SUM(CASE WHEN COALESCE(is_archived, 0) = 1 THEN 1 ELSE 0 END) AS archived_books
        FROM books
    """)
    row = cur.fetchone()
    cur.close()
    return dict(row)


def get_admin_category_rows():
    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT c.*, COUNT(b.book_id) AS book_count, f.faculty_name
           FROM categories c
           LEFT JOIN books b ON b.category_id = c.category_id
           LEFT JOIN faculties f ON c.faculty_id = f.faculty_id
           GROUP BY c.category_id ORDER BY c.category_name"""
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_admin_faculty_rows():
    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT f.*, COUNT(b.book_id) AS book_count,
                  COUNT(DISTINCT c.category_id) AS category_count
           FROM faculties f
           LEFT JOIN books b ON b.faculty_id = f.faculty_id
           LEFT JOIN categories c ON c.faculty_id = f.faculty_id
           GROUP BY f.faculty_id ORDER BY f.faculty_name"""
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_category_dependency_count(category_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM books WHERE category_id = %s", (category_id,))
    cnt = int(cur.fetchone()["cnt"])
    cur.close()
    return cnt


def get_faculty_dependency_counts(faculty_id):
    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT (SELECT COUNT(*) FROM books WHERE faculty_id = %s) AS books,
                  (SELECT COUNT(*) FROM categories WHERE faculty_id = %s) AS categories""",
        (faculty_id, faculty_id),
    )
    row = cur.fetchone()
    cur.close()
    return dict(row)


def get_book_dependency_count(book_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM borrow_requests WHERE book_id = %s", (book_id,))
    cnt = int(cur.fetchone()["cnt"])
    cur.close()
    return cnt


# ============================================================
# ARCHIVE LIFECYCLE (Phase 3)
# Active -> Archive -> Archived -> Restore / dependency-checked
# Permanent Delete. Historical records are NEVER touched.
# ============================================================

def archive_book(book_id):
    """Active book -> Archived. Only books not already archived."""
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE books SET is_archived = 1 WHERE book_id = %s AND COALESCE(is_archived, 0) = 0",
        (book_id,),
    )
    affected = cur.rowcount
    mysql.connection.commit()
    cur.close()
    return affected == 1


def restore_book(book_id):
    """Archived book -> Active."""
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE books SET is_archived = 0 WHERE book_id = %s AND COALESCE(is_archived, 0) = 1",
        (book_id,),
    )
    affected = cur.rowcount
    mysql.connection.commit()
    cur.close()
    return affected == 1


def get_book_dependency_audit(book_id):
    """Full dependency audit for permanent-delete gate.

    Returns dict with per-table row counts of historical records that
    reference the book. Archived book with ALL zeros may be hard-deleted;
    any non-zero count BLOCKS permanent delete (history is never removed).
    """
    cur = mysql.connection.cursor()
    audit = {}
    for table in ("borrow_requests", "bookmarks", "downloads", "read_history"):
        cur.execute(f"SELECT COUNT(*) AS cnt FROM {table} WHERE book_id = %s", (book_id,))
        audit[table] = int(cur.fetchone()["cnt"])
    # Fines reference books via borrow_requests.borrow_id (no book_id column).
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM fines f "
        "INNER JOIN borrow_requests br ON br.borrow_id = f.borrow_id "
        "WHERE br.book_id = %s",
        (book_id,),
    )
    audit["fines"] = int(cur.fetchone()["cnt"])
    cur.close()
    audit["has_dependencies"] = any(v > 0 for k, v in audit.items() if k != "has_dependencies")
    return audit


def get_book_by_id_admin(book_id):
    """Admin-safe single book fetch (includes archived books for restore flow)."""
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM books WHERE book_id = %s",
        (book_id,),
    )
    book = cur.fetchone()
    cur.close()
    return book


def get_admin_archived_page(search=None, page=1, per_page=25):
    """Archived-books workspace list (admin only)."""
    where = []
    params = []
    if search:
        like = f"%{search}%"
        where.append("(b.title LIKE %s OR b.author_name LIKE %s OR b.isbn LIKE %s)")
        params.extend([like, like, like])
    where_sql = (" AND " + " AND ".join(where)) if where else ""
    cur = mysql.connection.cursor()
    cur.execute(
        f"SELECT COUNT(*) AS total FROM books b WHERE COALESCE(b.is_archived, 0) = 1{where_sql}",
        tuple(params),
    )
    total = int(cur.fetchone()["total"])
    pages = max(1, -(-total // per_page))
    page = max(1, min(int(page), pages))
    offset = (page - 1) * per_page
    cur.execute(
        f"""SELECT b.book_id, b.title, b.isbn, b.author_name AS books_author_name,
                   b.resource_type, b.cover_image,
                   b.upload_date, COALESCE(b.is_archived, 0) AS is_archived
            FROM books b
            WHERE COALESCE(b.is_archived, 0) = 1{where_sql}
            ORDER BY b.upload_date DESC, b.book_id DESC
            LIMIT %s OFFSET %s""",
        tuple(params) + (per_page, offset),
    )
    records = cur.fetchall()
    cur.close()
    return {"records": records, "total": total, "page": page, "pages": pages, "per_page": per_page}


def get_author_dependency_count(author_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM books WHERE author_id = %s", (author_id,))
    cnt = int(cur.fetchone()["cnt"])
    cur.close()
    return cnt

def book_state_hints():
    """Book Add/Edit form ရဲ့ real-time state hint dict (i18n)။

    Form template က JSON အဖြစ်ထည့်ပြီး ရွေးချယ်မှုအလိုက်
    ဘာသာစကား ၂ မျိုးလုံးအတွက် hint ပြရန်သုံးသည်။
    """
    from utils.i18n import translate
    return {
        "hybrid": translate("state_hint_hybrid"),
        "physical": translate("state_hint_physical"),
        "digital": translate("state_hint_digital"),
        "invalid": translate("state_hint_invalid"),
    }
