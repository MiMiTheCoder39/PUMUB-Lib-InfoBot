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


def login_required(f):
    """User session ရှိမရှိ စစ်ဆေးသည်။ Login ဝင်ထားမှသာ page ကို ဝင်ခွင့်ရှိမည်။"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("ကျေးဇူးပြု၍ Login ဝင်ပါ။", "warning")
            return redirect(url_for("auth.login", next=request.path))
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