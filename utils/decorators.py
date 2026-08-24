"""
utils/decorators.py
---------------------
Route protection အတွက် decorator များ။

login_required  -> session ထဲမှာ user_id ရှိမရှိ စစ်ပါမယ်။ မရှိရင် login page ပို့ပါမယ်။
admin_required  -> login ဖြစ်ပြီး role == 'admin' ဖြစ်မှသာ ဝင်ခွင့်ပြုပါမယ်။
student_required -> login ဖြစ်ပြီး role == 'student' ဖြစ်မှသာ ဝင်ခွင့်ပြုပါမယ်။
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request
from models.user_model import get_user_by_id
from models.university_records import get_record_by_email
from utils.i18n import translate


def login_required(f):
    """User session ရှိမရှိ စစ်ဆေးသည်။ Login ဝင်ထားမှသာ page ကို ဝင်ခွင့်ရှိမည်။

    Phase 5: the linked official university record's four-state status
    is re-checked on every protected request. A record whose status
    has moved out of 'active' (inactive / graduated / suspended) since
    the last login is signed out and redirected with a generic status
    message. Admin accounts (no official record) are never blocked
    here — their access is controlled by admin_required instead.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("ကျေးဇူးပြု၍ Login ဝင်ပါ။", "warning")
            return redirect(url_for("auth.login", next=request.path))
        # Re-verify the official record status live (Phase 5).
        if session.get("role") in ("student", "teacher"):
            user = get_user_by_id(session["user_id"])
            if user and user.get("email"):
                record = get_record_by_email(user["email"])
                status = (record["status"] if record else "").strip().lower()
                if status in ("inactive", "graduated", "suspended"):
                    session.pop("user_id", None)
                    session.pop("username", None)
                    session.pop("name", None)
                    session.pop("role", None)
                    session.pop("faculty_id", None)
                    flash(translate("login_record_status_denied"), "danger")
                    return redirect(url_for("auth.login"))
                elif not record:
                    # Account was registered but its official record was
                    # removed — keep it signed in (data preserved) but
                    # note the anomaly; no silent lock-out.
                    pass
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Admin role ဖြစ်မှသာ ဝင်ခွင့်ပြုသည်။ login_required ပါ အလိုအလျောက် ပါဝင်ပြီးသား။"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("ကျေးဇူးပြု၍ Login ဝင်ပါ။", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "admin":
            flash("ဒီ Page ကို ဝင်ခွင့်မရှိပါ (Admin Only)။", "danger")
            return redirect(url_for("student.dashboard"))
        return f(*args, **kwargs)

    return decorated_function


def student_required(f):
    """Student role ဖြစ်မှသာ ဝင်ခွင့်ပြုသည်."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("ကျေးဇူးပြု၍ Login ဝင်ပါ။", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "student":
            flash("ဒီ Page ကို ဝင်ခွင့်မရှိပါ (Student Only)။", "danger")
            return redirect(url_for("auth.dashboard_redirect"))
        return f(*args, **kwargs)

    return decorated_function


def library_user_required(f):
    """Student သို့မဟုတ် Teacher role ဖြစ်မှသာ ဝင်ခွင့်ပြုသည်။"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("ကျေးဇူးပြု၍ Login ဝင်ပါ။", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") not in ["student", "teacher"]:
            flash("ဒီ Page ကို ဝင်ခွင့်မရှိပါ။", "danger")
            return redirect(url_for("auth.dashboard_redirect"))
        return f(*args, **kwargs)

    return decorated_function