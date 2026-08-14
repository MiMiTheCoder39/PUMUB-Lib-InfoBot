"""
models/admin_book_model.py
---------------------------
Admin Module — Book / Category / Author / Faculty CRUD functions
"""

from models.db import mysql


# ─── BOOKS ───────────────────────────────────────────────────
def add_book(title, isbn, author_name, author_id, category_id, faculty_id, description,
             resource_type, pdf_file, cover_image, publish_date, total_copies):
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO books
           (title,isbn,author_name,author_id,category_id,faculty_id,description,resource_type,
            pdf_file,cover_image,publish_date,total_copies,available_copies)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (title, isbn, author_name, author_id, category_id, faculty_id, description, resource_type,
         pdf_file, cover_image, publish_date, total_copies, total_copies)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id


def update_book(book_id, title, isbn, author_name, author_id, category_id, faculty_id, description,
                resource_type, publish_date, total_copies,
                pdf_file=None, cover_image=None):
    cur = mysql.connection.cursor()
    if pdf_file and cover_image:
        cur.execute(
            """UPDATE books SET title=%s,isbn=%s,author_name=%s,author_id=%s,category_id=%s,faculty_id=%s,
               description=%s,resource_type=%s,publish_date=%s,
               total_copies=%s,pdf_file=%s,cover_image=%s WHERE book_id=%s""",
            (title,isbn,author_name,author_id,category_id,faculty_id,description,resource_type,
             publish_date,total_copies,pdf_file,cover_image,book_id)
        )
    elif pdf_file:
        cur.execute(
            """UPDATE books SET title=%s,isbn=%s,author_name=%s,author_id=%s,category_id=%s,faculty_id=%s,
               description=%s,resource_type=%s,publish_date=%s,
               total_copies=%s,pdf_file=%s WHERE book_id=%s""",
            (title,isbn,author_name,author_id,category_id,faculty_id,description,resource_type,
             publish_date,total_copies,pdf_file,book_id)
        )
    elif cover_image:
        cur.execute(
            """UPDATE books SET title=%s,isbn=%s,author_name=%s,author_id=%s,category_id=%s,faculty_id=%s,
               description=%s,resource_type=%s,publish_date=%s,
               total_copies=%s,cover_image=%s WHERE book_id=%s""",
            (title,isbn,author_name,author_id,category_id,faculty_id,description,resource_type,
             publish_date,total_copies,cover_image,book_id)
        )
    else:
        cur.execute(
            """UPDATE books SET title=%s,isbn=%s,author_name=%s,author_id=%s,category_id=%s,faculty_id=%s,
               description=%s,resource_type=%s,publish_date=%s,
               total_copies=%s WHERE book_id=%s""",
            (title,isbn,author_name,author_id,category_id,faculty_id,description,resource_type,
             publish_date,total_copies,book_id)
        )
    mysql.connection.commit()
    cur.close()


def delete_book(book_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM books WHERE book_id=%s", (book_id,))
    mysql.connection.commit()
    cur.close()


def update_book_qr(book_id, qr_filename):
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


# ─── AUTHORS ─────────────────────────────────────────────────
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


def get_author_by_id(author_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM authors WHERE author_id=%s", (author_id,))
    row = cur.fetchone()
    cur.close()
    return row


# ─── FACULTIES ───────────────────────────────────────────────
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


def get_all_faculties_admin():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM faculties ORDER BY faculty_name, department")
    rows = cur.fetchall()
    cur.close()
    return rows