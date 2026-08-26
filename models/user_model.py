"""
models/user_model.py
----------------------
users table အတွက် DB query functions များ။
Auth (Register/Login) နှင့် User Management (Phase 5) နှစ်ခုလုံးက ဒီ functions တွေကို သုံးပါမယ်။
"""

from models.db import mysql


def get_user_by_username(username):
    """Username နဲ့ user ရှာသည် (Login အတွက်)."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    return user


def get_user_by_email(email):
    """Email ဖြင့် user ရှာသည် (Register duplicate check)."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    return user


def get_user_by_student_id(student_id):
    """Student ID ဖြင့် user ရှာသည် (Register duplicate check)."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE student_id = %s", (student_id,))
    user = cur.fetchone()
    cur.close()
    return user


def get_user_by_id(user_id):
    """user_id ဖြင့် user ရှာသည် (Profile load, session refresh)."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    return user


def create_library_user(user_id_card, name, email, username, hashed_password, role, faculty_id):
    """Student သို့မဟုတ် Teacher account အသစ် register လုပ်သည်."""
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO users (student_id, name, email, username, password, role, faculty_id, is_active)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 1)""",
        (user_id_card, name, email, username, hashed_password, role, faculty_id),
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id


def get_all_faculties():
    """Register page ထဲက Faculty dropdown အတွက်."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM faculties ORDER BY faculty_name, department")
    faculties = cur.fetchall()
    cur.close()
    return faculties


def update_password(user_id, hashed_password):
    """Change Password (Profile Management) အတွက်."""
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET password = %s WHERE user_id = %s", (hashed_password, user_id))
    mysql.connection.commit()
    cur.close()


def update_profile(user_id, name, email, faculty_id, profile_image=None, username=None):
    """Update editable profile fields and optionally a new profile picture."""
    fields = ["name = %s", "email = %s", "faculty_id = %s"]
    values = [name, email, faculty_id]

    if username is not None:
        fields.append("username = %s")
        values.append(username)
    if profile_image:
        fields.append("profile_image = %s")
        values.append(profile_image)

    values.append(user_id)
    cur = mysql.connection.cursor()
    cur.execute(
        f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s",
        tuple(values),
    )
    mysql.connection.commit()
    cur.close()

def update_last_login(user_id):
    """Login ဝင်ချိန်တိုင်း last_login column ကို update လုပ်သည်."""
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()
