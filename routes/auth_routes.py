"""
routes/auth_routes.py
------------------------
Register / Login / Logout — full implementation.

- Password hashing: werkzeug.security (generate_password_hash / check_password_hash)
- Session-based auth: Flask session stores user_id, username, name, role
- Role-based redirect: admin -> admin.dashboard | student -> student.dashboard
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models.user_model import (
    get_user_by_username,
    get_user_by_email,
    get_user_by_student_id,
    create_library_user,
    get_all_faculties,
    update_last_login,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ============================================================
# REGISTER  (Student only — Admin accounts are seeded directly in DB)
# ============================================================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("auth.dashboard_redirect"))

    if request.method == "POST":
        user_id_card = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        faculty_id = request.form.get("faculty_id") or None
        role = request.form.get("role", "student")

        if role not in ["student", "teacher"]:
            role = "student"

        # ---------------- Email Domain Validation ----------------
        if not email.endswith("@pumub.edu.mm"):
            flash("ကျေးဇူးပြု၍ ကျောင်း Email (@pumub.edu.mm) ကိုသာ အသုံးပြုပါ။", "danger")
            return redirect(url_for("auth.register"))

        # ---------------- Validation ----------------
        if not all([user_id_card, name, email, username, password, confirm_password]):
            flash("ကျေးဇူးပြု၍ Field အားလုံးကို ဖြည့်ပါ။", "danger")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Password နှင့် Confirm Password မတူညီပါ။", "danger")
            return redirect(url_for("auth.register"))

        if len(password) < 6:
            flash("Password အနည်းဆုံး အက္ခရာ ၆ လုံး ရှိရပါမည်။", "danger")
            return redirect(url_for("auth.register"))

        if get_user_by_email(email):
            flash("ဒီ Email ဖြင့် Account ရှိနှင့်ပြီးပါပြီ။", "danger")
            return redirect(url_for("auth.register"))

        if get_user_by_username(username):
            flash("ဒီ Username ကို အသုံးပြုပြီးသား ဖြစ်နေပါသည်။ တခြား Username ရွေးပါ။", "danger")
            return redirect(url_for("auth.register"))

        if get_user_by_student_id(user_id_card):
            flash(f"ဒီ {'Student' if role == 'student' else 'Teacher'} ID ဖြင့် Account ရှိနှင့်ပြီးပါပြီ။", "danger")
            return redirect(url_for("auth.register"))

        # ---------------- Create Account ----------------
        hashed_password = generate_password_hash(password)
        create_library_user(user_id_card, name, email, username, hashed_password, role, faculty_id)

        flash("Register အောင်မြင်ပါသည်! ကျေးဇူးပြု၍ Login ဝင်ပါ။", "success")
        return redirect(url_for("auth.login"))

    faculties = get_all_faculties()
    return render_template("auth/register.html", faculties=faculties)


# ============================================================
# LOGIN
# ============================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("auth.dashboard_redirect"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username နှင့် Password ကို ဖြည့်ပါ။", "danger")
            return redirect(url_for("auth.login"))

        user = get_user_by_username(username)

        if not user:
            flash("Username မှားယွင်းနေပါသည်။", "danger")
            return redirect(url_for("auth.login"))

        if not check_password_hash(user["password"], password):
            flash("Password မှားယွင်းနေပါသည်။", "danger")
            return redirect(url_for("auth.login"))

        if not user["is_active"]:
            flash("သင့် Account ကို Deactivate လုပ်ထားပါသည်။ Library Admin ကို ဆက်သွယ်ပါ။", "danger")
            return redirect(url_for("auth.login"))

        # ---------------- Session ထဲ Save ----------------
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["name"] = user["name"]
        session["role"] = user["role"]
        session["faculty_id"] = user["faculty_id"]

        # Update last login timestamp
        update_last_login(user["user_id"])

        flash(f"ပြန်လည်ကြိုဆိုပါတယ်, {user['name']}!", "success")

        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)

        return redirect(url_for("auth.dashboard_redirect"))

    return render_template("auth/login.html")


# ============================================================
# LOGOUT
# ============================================================
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logout အောင်မြင်ပါသည်။", "info")
    return redirect(url_for("auth.login"))


# ============================================================
# Role-based redirect helper
# ============================================================
@auth_bp.route("/dashboard-redirect")
def dashboard_redirect():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("student.dashboard"))