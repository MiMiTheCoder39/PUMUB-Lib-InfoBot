"""
routes/auth_routes.py
------------------------
Register / Login / Logout — full implementation.

- Password hashing: werkzeug.security (generate_password_hash / check_password_hash)
- Session-based auth: Flask session stores user_id, username, name, role
- Role-based redirect: admin -> admin.dashboard | student -> student.dashboard

VERIFIED REGISTRATION (Phase 2):
Step 1  — official university email (+ university ID) verified
          against the `university_records` master table. No identity
          field is ever user-selected: the official record's name,
          role and faculty are LOCKED server-side (session-bound).
Step 2  — username + strong password only (live policy checklist).
          Duplicate protection is enforced at both steps against the
          official record AND existing accounts.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

import MySQLdb

from werkzeug.security import generate_password_hash, check_password_hash
from utils.i18n import SUPPORTED_LANGUAGES
from utils.identity_check import verify_identity
from utils.i18n import translate
from utils.password_policy import check_password_policy
from models.db import mysql
from models.user_model import (
    get_user_by_username,
    get_user_by_email,
    get_user_by_student_id,
    create_library_user,
    get_all_faculties,
    update_last_login,
    update_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ============================================================
# STEP 1 — OFFICIAL IDENTITY VERIFICATION (email + university ID)
# ============================================================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("auth.dashboard_redirect"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        university_id = request.form.get("university_id", "").strip() or None

        # ---- Basic presence checks (generic messages — never reveal
        #      whether the problem is the email or the ID) ------------
        if not email:
            flash(translate("verify_email_required"), "danger")
            return redirect(url_for("auth.register"))

        # ---- Official record lookup + duplicate + status gates ------
        result = verify_identity(email)

        if not result["valid"]:
            for err in result["errors"]:
                flash(err, "danger")
            return redirect(url_for("auth.register"))

        # ---- University ID matching (Phase 2): a student record
        #      (which always carries an ID) must also match on the
        #      submitted university ID; teacher records carry no ID. --
        if result["university_id"] and university_id is not None:
            if str(result["university_id"]).lower() != str(university_id).lower():
                flash(translate("verify_id_mismatch"), "danger")
                return redirect(url_for("auth.register"))
        elif result["university_id"] and university_id is None:
            flash(translate("verify_id_required"), "danger")
            return redirect(url_for("auth.register"))

        # ---- Account-status verification (Phase 2, approved Q3a):
        #      graduated/suspended records are never eligible to
        #      register, even if is_active is still 1. ----------------
        status = (str(result.get("status") or "active")).lower()
        if status != "active":
            # Map record status to a translated denial message.
            if status == "graduated":
                flash(translate("verify_record_graduated"), "danger")
            elif status == "suspended":
                flash(translate("verify_record_suspended"), "danger")
            else:
                flash(translate("verify_record_inactive"), "danger")
            return redirect(url_for("auth.register"))

        # ---- Duplicate account gate (identity-lock): one registered
        #      users account per official record email, ever. ---------
        from models.university_records import count_users_registered_from_email
        if count_users_registered_from_email(email):
            flash(translate("verify_duplicate_email"), "danger")
            return redirect(url_for("auth.register"))

        # ---- Verified: lock the official identity into the session ---
        session["register_verified"] = True
        session["register_email"] = email
        session["register_name"] = result["official_name"]
        session["register_role"] = result["role"]           # auto-assigned
        session["register_faculty_id"] = result["faculty_id"]
        session["register_university_id"] = result["university_id"]
        session["register_department"] = result["department"]  # for step 2 card
        session["register_year"] = result["year"]              # for step 2 card

        return redirect(url_for("auth.register_password"))

    return render_template("auth/register.html")


# ============================================================
# STEP 2 — USERNAME + STRONG PASSWORD (identity is locked)
# ============================================================
@auth_bp.route("/register/password", methods=["GET", "POST"])
def register_password():
    if "user_id" in session:
        return redirect(url_for("auth.dashboard_redirect"))

    # Step 1 verification must have completed first.
    if not session.get("register_verified"):
        flash(translate("verify_step_required"), "danger")
        return redirect(url_for("auth.register"))

    email = session["register_email"]

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # ---- Presence ------------------------------------------------
        if not all([username, password, confirm_password]):
            flash(translate("reg_missing_fields"), "danger")
            return render_step2(email)

        # ---- Username validation -------------------------------------
        if not (3 <= len(username) <= 50) or not all(ch.isalnum() or ch == "_" for ch in username):
            flash(translate("reg_username_invalid"), "danger")
            return render_step2(email)

        if get_user_by_username(username):
            flash(translate("reg_username_taken"), "danger")
            return render_step2(email)

        # ---- Password policy (server-authoritative) ------------------
        policy = check_password_policy(password)
        if not policy["all_ok"]:
            flash(translate("reg_password_weak"), "danger")
            return render_step2(email)

        if password != confirm_password:
            flash(translate("reg_password_mismatch"), "danger")
            return render_step2(email)

        # ---- Duplicate account gate (re-check at commit time) --------
        if get_user_by_email(email):
            flash(translate("verify_duplicate_email"), "danger")
            session.pop("register_verified", None)
            return redirect(url_for("auth.register"))

        # ---- Create the account ---------------------------------------
        role = session["register_role"]
        if role not in ("student", "teacher"):
            role = "student"

        university_id = session.get("register_university_id")
        name = session["register_name"]
        faculty_id = session.get("register_faculty_id")
        hashed_password = generate_password_hash(password)

        try:
            create_library_user(university_id, name, email, username,
                                hashed_password, role, faculty_id)
        except MySQLdb.IntegrityError as exc:
            # Narrow scope: only the duplicate account constraints
            # (student_id / email / username unique keys) turn into a
            # friendly message. Every other IntegrityError is NOT caught
            # here and behaves exactly as before.
            code = exc.args[0] if exc.args else None
            if code == 1062:
                flash(translate("reg_duplicate_account"), "danger")
                return render_step2(email)
            raise

        # ---- Clear verification session, all done ---------------------
        for key in ("register_verified", "register_email", "register_name",
                    "register_role", "register_faculty_id",
                    "register_university_id"):
            session.pop(key, None)

        # Phase 4: present the Step 4 completion state (presentation only;
        # reg_success flash is still set so login gets the success banner
        # if the user navigates there directly).
        flash(translate("reg_success"), "success")
        return render_template(
            "auth/register_complete.html",
            lang=session.get("language", "my"),
        )

    return render_step2(email)


def render_step2(email):
    faculty_name = None
    faculty_id = session.get("register_faculty_id")
    if faculty_id:
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "SELECT faculty_name FROM faculties "
                "WHERE faculty_id = %s LIMIT 1",
                (int(faculty_id),),
            )
            row = cur.fetchone()
            if row:
                faculty_name = row["faculty_name"]
        finally:
            cur.close()
    return render_template(
        "auth/register_password.html",
        name=session["register_name"],
        university_id=session.get("register_university_id"),
        email=email,
        role=session["register_role"],
        faculty_name=faculty_name,
        department=session.get("register_department"),
        year=session.get("register_year"),
        lang=session.get("language", "my"),
    )


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
            flash(translate("login_missing_fields"), "danger")
            return redirect(url_for("auth.login"))

        user = get_user_by_username(username)

        if not user:
            flash(translate("login_bad_username"), "danger")
            return redirect(url_for("auth.login"))

        if not check_password_hash(user["password"], password):
            flash(translate("login_bad_password"), "danger")
            return redirect(url_for("auth.login"))

        if not user["is_active"]:
            flash(translate("login_account_deactivated"), "danger")
            return redirect(url_for("auth.login"))

        # ---------------- Phase 5: live record status re-check ---------
        # The official university record's four-state status is
        # re-verified at login time (not only at registration). A
        # graduated / suspended / inactive record is denied even for
        # previously working accounts. Admin accounts carry no official
        # record and are never blocked here.
        if user["role"] in ("student", "teacher") and user.get("email"):
            from models.university_records import get_record_by_email as _gre
            _rec = _gre(user["email"])
            _rec_status = (str(_rec["status"]) if _rec else "").strip().lower()
            if _rec_status in ("inactive", "graduated", "suspended"):
                flash(translate("login_record_status_denied"), "danger")
                return redirect(url_for("auth.login"))

        # ---------------- Session ထဲ Save ----------------
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["name"] = user["name"]
        session["role"] = user["role"]
        session["faculty_id"] = user["faculty_id"]
        session["profile_image"] = user.get("profile_image")

        # Update last login timestamp
        update_last_login(user["user_id"])

        flash(translate("login_success"), "success")

        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)

        return redirect(url_for("auth.dashboard_redirect"))

    return render_template(
        "auth/login.html",
        lang=session.get("language", "my"),
    )


# ============================================================
# LOGOUT
# ============================================================
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash(translate("logout_success"), "info")
    return redirect(url_for("auth.login"))


# ============================================================
# FORGOT PASSWORD — 3-STEP IN-APP TOKEN FLOW (Phase 4)
#
# Step 1  /auth/forgot-password   verify identity (email + student_id /
#                                 username), issue hashed single-use
#                                 token, show raw token once in-app
# Step 2  /auth/reset/token       confirm the raw token (constant-time)
# Step 3  /auth/reset/password    set a new policy-compliant password
# ============================================================
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Show the Admin-mediated recovery instructions."""
    for key in ("reset_token_raw", "reset_user_id", "reset_verified_user_id"):
        session.pop(key, None)
    if request.method == "GET":
        return render_template("auth/forgot_password_admin.html")
    flash(translate("forgot_admin_notice"), "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset/token", methods=["GET", "POST"])
def reset_token_page():
    """Legacy token endpoint retained only to redirect to the Admin flow."""
    for key in ("reset_token_raw", "reset_user_id", "reset_verified_user_id"):
        session.pop(key, None)
    flash(translate("forgot_admin_notice"), "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset/password", methods=["GET", "POST"])
def reset_password_page():
    """Legacy password endpoint retained only to redirect to the Admin flow."""
    for key in ("reset_token_raw", "reset_user_id", "reset_verified_user_id"):
        session.pop(key, None)
    flash(translate("forgot_admin_notice"), "info")
    return redirect(url_for("auth.login"))


# ============================================================
# LANGUAGE SWITCH (shared by auth pages)
# ============================================================
@auth_bp.route("/language/<language>")
def set_language(language):
    """Language switch used by both auth pages (via ?redirect= param)
    and the rest of the app (via Referer)."""
    if language not in SUPPORTED_LANGUAGES:
        flash(translate("language_unsupported"), "warning")
        target = request.args.get("redirect") or (request.referrer or url_for("auth.register"))
        return redirect(target)
    session["language"] = language
    target = request.args.get("redirect") or (request.referrer or url_for("auth.register"))
    return redirect(target)


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
