"""
models/bookmark_model.py
---------------------------
bookmarks table အတွက် DB query functions များ။
"""

from models.db import mysql


def add_bookmark(user_id, book_id):
    """Bookmark ထည့်သည် (UNIQUE key ရှိနှင့်ပြီးသား user+book ကို error မထုတ်ဘဲ ignore လုပ်ပါမယ်)."""
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT IGNORE INTO bookmarks (user_id, book_id) VALUES (%s, %s)",
        (user_id, book_id),
    )
    mysql.connection.commit()
    cur.close()


def remove_bookmark(user_id, book_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM bookmarks WHERE user_id = %s AND book_id = %s", (user_id, book_id))
    mysql.connection.commit()
    cur.close()


def is_bookmarked(user_id, book_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT bookmark_id FROM bookmarks WHERE user_id = %s AND book_id = %s", (user_id, book_id))
    result = cur.fetchone()
    cur.close()
    return result is not None


def get_user_bookmarks(user_id):
    """Student ရဲ့ Favorite/Bookmark list အားလုံး (book details ပါတွဲပြ)."""
    cur = mysql.connection.cursor()
    cur.execute(
        """SELECT bm.bookmark_id, bm.created_at, b.*, a.author_name, c.category_name
           FROM bookmarks bm
           JOIN books b ON bm.book_id = b.book_id
           LEFT JOIN authors a ON b.author_id = a.author_id
           LEFT JOIN categories c ON b.category_id = c.category_id
           WHERE bm.user_id = %s
           ORDER BY bm.created_at DESC""",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows