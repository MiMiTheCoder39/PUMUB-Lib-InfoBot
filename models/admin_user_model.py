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
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO users (student_id,name,email,username,password,role,faculty_id,is_active)
           VALUES (%s,%s,%s,%s,%s,%s,%s,1)""",
        (student_id, name, email, username, hashed_password, role, faculty_id)
    )
    mysql.connection.commit()
    cur.close()


def update_user_admin(user_id, name, email, faculty_id, role):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE users SET name=%s, email=%s, faculty_id=%s, role=%s WHERE user_id=%s",
        (name, email, faculty_id, role, user_id)
    )
    mysql.connection.commit()
    cur.close()


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
