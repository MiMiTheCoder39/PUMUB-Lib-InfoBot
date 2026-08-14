"""
models/history_model.py
--------------------------
read_history နှင့် downloads tables အတွက် DB query functions များ။
"""

from models.db import mysql


# ============================================================
# READ HISTORY (View History — PDF Viewer ဖွင့်ကြည့်တိုင်း log)
# ============================================================
def log_read_history(user_id, book_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO read_history (user_id, book_id) VALUES (%s, %s)",
        (user_id, book_id),
    )
    mysql.connection.commit()
    cur.close()


def get_read_history(user_id, limit=50):
    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT rh.history_id, rh.read_date, b.book_id, b.title, b.cover_image, a.author_name
           FROM read_history rh
           JOIN books b ON rh.book_id = b.book_id
           LEFT JOIN authors a ON b.author_id = a.author_id
           WHERE rh.user_id = %s
           ORDER BY rh.read_date DESC
           LIMIT %s""",
        (user_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# ============================================================
# DOWNLOAD HISTORY (download တိုင်း log)
# ============================================================
def log_download(user_id, book_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO downloads (user_id, book_id) VALUES (%s, %s)",
        (user_id, book_id),
    )
    mysql.connection.commit()
    cur.close()


def get_download_history(user_id, limit=50):
    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT d.download_id, d.download_date, b.book_id, b.title, b.cover_image, a.author_name
           FROM downloads d
           JOIN books b ON d.book_id = b.book_id
           LEFT JOIN authors a ON b.author_id = a.author_id
           WHERE d.user_id = %s
           ORDER BY d.download_date DESC
           LIMIT %s""",
        (user_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    return rows