"""
models/book_model.py
----------------------
books table အတွက် DB query functions များ။
Student Module (Search, View Details, Download) နှင့်
Admin Module (Book Management, Phase 5) နှစ်ခုလုံးက သုံးပါမယ်။
"""

from models.db import mysql


# ============================================================
# SEARCH / LISTING
# ============================================================
def search_books(keyword=None, category_id=None, faculty_id=None, author_id=None, resource_type=None, limit=None, primary_only=False):
    """
    Title / Author Name / Category ဖြင့် primary search လုပ်နိုင်ပြီး၊
    legacy callers အတွက် ISBN နှင့် optional filters ကို ဆက်လက်ထောက်ပံ့သည်။
    """
    query = """
        SELECT b.*, COALESCE(b.author_name, a.author_name) AS author_name, 
               c.category_name, f.faculty_name
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN categories c ON b.category_id = c.category_id
        LEFT JOIN faculties f ON b.faculty_id = f.faculty_id
        WHERE 1=1
    """
    params = []

    if keyword:
        like = f"%{keyword}%"
        if primary_only:
            query += """ AND (b.title LIKE %s
                              OR b.author_name LIKE %s
                              OR a.author_name LIKE %s
                              OR c.category_name LIKE %s)"""
            params.extend([like, like, like, like])
        else:
            clean_keyword = keyword.replace("-", "")
            query += """ AND (b.title LIKE %s
                              OR b.author_name LIKE %s
                              OR a.author_name LIKE %s
                              OR REPLACE(b.isbn, '-', '') LIKE %s
                              OR b.isbn LIKE %s
                              OR c.category_name LIKE %s)"""
            clean_like = f"%{clean_keyword}%"
            params.extend([like, like, like, clean_like, like, like])

    if category_id:
        query += " AND b.category_id = %s"
        params.append(category_id)

    if faculty_id:
        query += " AND b.faculty_id = %s"
        params.append(faculty_id)

    if author_id:
        query += " AND b.author_id = %s"
        params.append(author_id)

    if resource_type:
        query += " AND b.resource_type = %s"
        params.append(resource_type)

    # Phase 3: archived books are invisible in catalog / search / listing.
    query += " AND COALESCE(b.is_archived, 0) = 0 ORDER BY b.upload_date DESC"

    if limit:
        query += " LIMIT %s"
        params.append(int(limit))

    cur = mysql.connection.cursor()
    cur.execute(query, tuple(params))
    books = cur.fetchall()
    cur.close()
    return books


def get_collection_page(category_id=None, faculty_id=None, page=1, per_page=12):
    """Return one page of active books for a faculty/category collection."""
    import math

    page = max(1, int(page or 1))
    per_page = max(1, min(int(per_page or 12), 100))
    filters = ["COALESCE(b.is_archived, 0) = 0"]
    params = []
    if category_id:
        filters.append("b.category_id = %s")
        params.append(category_id)
    if faculty_id:
        filters.append("b.faculty_id = %s")
        params.append(faculty_id)
    where_sql = " AND ".join(filters)

    cur = mysql.connection.cursor()
    cur.execute(f"SELECT COUNT(*) AS total FROM books b WHERE {where_sql}", tuple(params))
    total = int((cur.fetchone() or {}).get("total") or 0)
    pages = max(1, math.ceil(total / per_page))
    page = min(page, pages)
    offset = (page - 1) * per_page

    cur.execute(
        f"""SELECT b.*, COALESCE(b.author_name, a.author_name) AS author_name,
                   c.category_name, f.faculty_name
            FROM books b
            LEFT JOIN authors a ON b.author_id = a.author_id
            LEFT JOIN categories c ON b.category_id = c.category_id
            LEFT JOIN faculties f ON b.faculty_id = f.faculty_id
            WHERE {where_sql}
            ORDER BY b.upload_date DESC, b.book_id DESC
            LIMIT %s OFFSET %s""",
        tuple(params + [per_page, offset]),
    )
    records = cur.fetchall()
    cur.close()

    return {
        "records": records,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "start": offset + 1 if total else 0,
        "end": min(offset + len(records), total),
    }


def get_all_books(limit=None):
    """Search filter မပါဘဲ Book အားလုံးကို ပြသည် (Browse page)."""
    query = """
        SELECT b.*, COALESCE(b.author_name, a.author_name) AS author_name, c.category_name, f.faculty_name
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN categories c ON b.category_id = c.category_id
        LEFT JOIN faculties f ON b.faculty_id = f.faculty_id
        WHERE COALESCE(b.is_archived, 0) = 0
        ORDER BY b.upload_date DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    cur = mysql.connection.cursor()
    cur.execute(query)
    books = cur.fetchall()
    cur.close()
    return books


def get_book_by_id(book_id):
    """Book Details Page အတွက် single book fetch."""
    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT b.*, COALESCE(b.author_name, a.author_name) AS author_name, 
                  c.category_name, f.faculty_name
           FROM books b
           LEFT JOIN authors a ON b.author_id = a.author_id
           LEFT JOIN categories c ON b.category_id = c.category_id
           LEFT JOIN faculties f ON b.faculty_id = f.faculty_id
           WHERE b.book_id = %s""",
        (book_id,),
    )
    book = cur.fetchone()
    cur.close()
    return book


def get_popular_books(limit=8):
    """Most Downloaded Books (Popular Books widget)."""
    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT b.*, COALESCE(b.author_name, a.author_name) AS author_name, c.category_name
           FROM books b
           LEFT JOIN authors a ON b.author_id = a.author_id
           LEFT JOIN categories c ON b.category_id = c.category_id
           WHERE COALESCE(b.is_archived, 0) = 0
           ORDER BY b.download_count DESC
           LIMIT %s""",
        (limit,),
    )
    books = cur.fetchall()
    cur.close()
    return books


def get_books_by_category(category_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM books WHERE category_id = %s AND COALESCE(is_archived, 0) = 0 "
        "ORDER BY upload_date DESC",
        (category_id,),
    )
    books = cur.fetchall()
    cur.close()
    return books


# ============================================================
# COUNTERS (view_count / download_count)
# ============================================================
def increment_view_count(book_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE books SET view_count = view_count + 1 WHERE book_id = %s", (book_id,))
    mysql.connection.commit()
    cur.close()


def increment_download_count(book_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE books SET download_count = download_count + 1 WHERE book_id = %s", (book_id,))
    mysql.connection.commit()
    cur.close()


# ============================================================
# LOOKUP DATA (for search filter dropdowns)
# ============================================================
def get_all_categories():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories ORDER BY category_name")
    rows = cur.fetchall()
    cur.close()
    return rows


def get_all_authors():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM authors ORDER BY author_name")
    rows = cur.fetchall()
    cur.close()
    return rows