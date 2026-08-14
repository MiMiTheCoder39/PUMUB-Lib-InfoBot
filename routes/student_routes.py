"""
routes/student_routes.py
--------------------------
Student Module — full implementation.

Features:
- Dashboard (recent + popular books)
- Search Books (Title / Author / Category / Faculty)
- View Book Details (+ view_count increment)
- Read Online (PDF inline viewer) (+ read_history log)
- Download Book (PDF download) (+ download_count increment + download_history log)
- Bookmark / Favorite (add, remove, list)
- View History (Read History + Download History)
- Profile Management (Update Profile, Change Password)
"""

import os
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, send_from_directory, current_app, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from utils.decorators import login_required, student_required, library_user_required
from utils.file_utils import save_uploaded_file
from utils.recommender import get_recommendations

from models.book_model import (
    search_books, get_all_books, get_book_by_id, get_popular_books,
    increment_view_count, increment_download_count,
    get_all_categories, get_all_authors,
)
from models.bookmark_model import add_bookmark, remove_bookmark, is_bookmarked, get_user_bookmarks
from models.history_model import (
    log_read_history, get_read_history, log_download, get_download_history,
)
from models.user_model import get_user_by_id, update_password, update_profile, get_all_faculties
from models.report_model import (
    get_all_announcements,
    get_books_by_category_for_shelf,
    get_active_users,
    get_most_borrowed_books,
)
from models.borrow_model import (
    create_borrow_request,
    get_student_borrow_history,
    get_student_borrow_stats,
)
from models.notification_model import (
    get_user_notifications, get_unread_count, mark_all_read, mark_one_read,
)

student_bp = Blueprint("student", __name__, url_prefix="/student")


# ============================================================
# DASHBOARD
# ============================================================
@student_bp.route("/dashboard")
@login_required
@library_user_required
def dashboard():
    user_id = session["user_id"]
    recent_books    = get_all_books(limit=8)
    popular_books   = get_popular_books(limit=10)
    recommended     = get_recommendations(user_id, top_n=8)
    unread_count    = get_unread_count(user_id)
    faculties       = get_all_faculties()
    categories      = get_all_categories()
    # Borrow stats for dashboard stat cards
    try:
        stats = get_student_borrow_stats(user_id)
    except Exception:
        stats = {"borrowed": 0, "overdue": 0, "pending": 0, "approved": 0}
    if stats is None:
        stats = {"borrowed": 0, "overdue": 0, "pending": 0, "approved": 0}
    announcements   = []
    categories_with_books = []
    top_score_users = []
    most_borrowed_books = []
    try:
        announcements = get_all_announcements()[:5]
        top_score_users = get_active_users(limit=10)
        most_borrowed_books = get_most_borrowed_books(limit=10)
    except Exception:
        pass

    # Enrich faculties with books
    for faculty in faculties:
        faculty['books'] = search_books(faculty_id=faculty.get('faculty_id'), limit=4)

    # Enrich categories with book covers (photo5-style shelves)
    for cat in categories:
        cat['books'] = get_books_by_category_for_shelf(cat.get('category_id'), limit=4)
        try:
            cat['book_count'] = get_books_by_category_for_shelf(cat.get('category_id'), limit=100)
            cat['book_count'] = len(cat['book_count'])
        except Exception:
            cat['book_count'] = 0
    
    return render_template(
        "user/dashboard.html",
        name=session.get("name"),
        recent_books=recent_books,
        popular_books=popular_books,
        recommended=recommended,
        faculties=faculties,
        categories=categories,
        categories_with_books=categories_with_books or categories,
        announcements=announcements,
        top_score_users=top_score_users,
        most_borrowed_books=most_borrowed_books or popular_books,
        unread_count=unread_count,
        active_borrows_count=stats.get("borrowed", 0) + stats.get("overdue", 0),
        pending_requests_count=stats.get("pending", 0) + stats.get("approved", 0),
        overdue_count=stats.get("overdue", 0)
    )


# ============================================================
# SEARCH BOOKS
# ============================================================
@student_bp.route("/search")
@login_required
@library_user_required
def search():
    keyword = (request.args.get("q") or request.args.get("keyword", "")).strip()
    category_id = request.args.get("category") or request.args.get("category_id") or None
    faculty_id = request.args.get("faculty") or request.args.get("faculty_id") or None
    author_id = request.args.get("author_id") or None
    resource_type = request.args.get("resource_type") or None
    sort_by = request.args.get("sort") or None

    # Filter တစ်ခုမှ မပါရင် Book အားလုံးကို ပြသည်
    if not any([keyword, category_id, faculty_id, author_id, resource_type]):
        if sort_by == 'borrowed':
            books = get_popular_books(limit=50)
        else:
            books = get_all_books()
    else:
        books = search_books(
            keyword=keyword or None,
            category_id=category_id,
            faculty_id=faculty_id,
            author_id=author_id,
            resource_type=resource_type,
        )

    categories = get_all_categories()
    faculties = get_all_faculties()
    authors = get_all_authors()

    return render_template(
        "user/search.html",
        books=books,
        categories=categories,
        faculties=faculties,
        authors=authors,
        keyword=keyword,
        selected_category=category_id,
        selected_faculty=faculty_id,
        selected_author=author_id,
        selected_type=resource_type,
    )


# ============================================================
# VIEW BOOK DETAILS
# ============================================================
@student_bp.route("/book/<int:book_id>")
@login_required
@library_user_required
def book_details(book_id):
    book = get_book_by_id(book_id)
    if not book:
        abort(404)

    # Access Control: Restricted types are for Teachers only
    restricted_types = ['thesis', 'research_paper', 'reference_book', 'teachers_guide']
    is_restricted = book['resource_type'] in restricted_types
    can_access = True
    if is_restricted and session.get("role") != "teacher":
        can_access = False

    increment_view_count(book_id)
    bookmarked = is_bookmarked(session["user_id"], book_id)

    return render_template("user/book_details.html", 
                           book=book, 
                           bookmarked=bookmarked,
                           can_access=can_access)


# ============================================================
# READ ONLINE (PDF Viewer)
# ============================================================
@student_bp.route("/book/<int:book_id>/read")
@login_required
@library_user_required
def read_book(book_id):
    book = get_book_by_id(book_id)
    if not book:
        abort(404)

    # Access Control
    restricted_types = ['thesis', 'research_paper', 'reference_book', 'teachers_guide']
    if book['resource_type'] in restricted_types and session.get("role") != "teacher":
        flash("ဤစာအုပ်ကို ဖတ်ရှုခွင့်မရှိပါ။ (Teachers Only)", "danger")
        return redirect(url_for("student.book_details", book_id=book_id))

    log_read_history(session["user_id"], book_id)

    return render_template("user/pdf_viewer.html", book=book)


@student_bp.route("/book/<int:book_id>/file")
@login_required
@library_user_required
def serve_book_file(book_id):
    """PDF Viewer ထဲက <iframe>/<embed> က ခေါ်မယ့် inline-serve route (download header မထည့်)."""
    book = get_book_by_id(book_id)
    if not book:
        abort(404)
    
    # Access Control
    restricted_types = ['thesis', 'research_paper', 'reference_book', 'teachers_guide']
    if book['resource_type'] in restricted_types and session.get("role") != "teacher":
        abort(403)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER_BOOKS"], book["pdf_file"], as_attachment=False
    )


# ============================================================
# DOWNLOAD BOOK
# ============================================================
@student_bp.route("/book/<int:book_id>/download")
@login_required
@library_user_required
def download_book(book_id):
    book = get_book_by_id(book_id)
    if not book:
        abort(404)

    # Access Control
    restricted_types = ['thesis', 'research_paper', 'reference_book', 'teachers_guide']
    if book['resource_type'] in restricted_types and session.get("role") != "teacher":
        flash("ဤစာအုပ်ကို Download ပြုလုပ်ခွင့်မရှိပါ။ (Teachers Only)", "danger")
        return redirect(url_for("student.book_details", book_id=book_id))

    increment_download_count(book_id)
    log_download(session["user_id"], book_id)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER_BOOKS"],
        book["pdf_file"],
        as_attachment=True,
        download_name=f"{book['title']}.pdf",
    )


# ============================================================
# BOOKMARK / FAVORITE
# ============================================================
@student_bp.route("/bookmark/<int:book_id>/add", methods=["POST"])
@login_required
@library_user_required
def bookmark_add(book_id):
    add_bookmark(session["user_id"], book_id)
    flash("Bookmark ထဲ ထည့်ပြီးပါပြီ။", "success")
    return redirect(request.referrer or url_for("student.book_details", book_id=book_id))


@student_bp.route("/bookmark/<int:book_id>/remove", methods=["POST"])
@login_required
@library_user_required
def bookmark_remove(book_id):
    remove_bookmark(session["user_id"], book_id)
    flash("Bookmark ထဲကနေ ဖယ်ရှားပြီးပါပြီ။", "info")
    return redirect(request.referrer or url_for("student.book_details", book_id=book_id))


@student_bp.route("/bookmarks")
@login_required
@library_user_required
def bookmarks():
    books = get_user_bookmarks(session["user_id"])
    return render_template("user/bookmarks.html", books=books)


# ============================================================
# VIEW HISTORY (Read History + Download History)
# ============================================================
@student_bp.route("/history")
@login_required
@library_user_required
def history():
    read_history = get_read_history(session["user_id"])
    download_history = get_download_history(session["user_id"])
    return render_template(
        "user/history.html", read_history=read_history, download_history=download_history
    )


# ============================================================
# PROFILE MANAGEMENT
# ============================================================
@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
@library_user_required
def profile():
    user = get_user_by_id(session["user_id"])
    faculties = get_all_faculties()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        faculty_id = request.form.get("faculty_id") or None

        if not name or not email:
            flash("Name နှင့် Email ကို ဖြည့်ပါ။", "danger")
            return redirect(url_for("student.profile"))

        profile_image_filename = None
        if "profile_image" in request.files:
            saved = save_uploaded_file(
                request.files["profile_image"],
                current_app.config["UPLOAD_FOLDER_COVERS"],  # reuse covers folder for simplicity
                current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
            )
            if saved:
                profile_image_filename = saved

        update_profile(session["user_id"], name, email, faculty_id, profile_image_filename)
        session["name"] = name  # navbar ထဲက name ကို update လုပ်ပါ

        flash("Profile ကို အောင်မြင်စွာ Update လုပ်ပြီးပါပြီ။", "success")
        return redirect(url_for("student.profile"))

    return render_template("user/profile.html", user=user, faculties=faculties)


@student_bp.route("/profile/change-password", methods=["POST"])
@login_required
@library_user_required
def change_password():
    user = get_user_by_id(session["user_id"])

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not check_password_hash(user["password"], current_password):
        flash("လက်ရှိ Password မှားယွင်းနေပါသည်။", "danger")
        return redirect(url_for("student.profile"))

    if len(new_password) < 6:
        flash("Password အသစ်သည် အနည်းဆုံး အက္ခရာ ၆ လုံး ရှိရပါမည်။", "danger")
        return redirect(url_for("student.profile"))

    if new_password != confirm_password:
        flash("Password အသစ်နှင့် Confirm Password မတူညီပါ။", "danger")
        return redirect(url_for("student.profile"))

    update_password(session["user_id"], generate_password_hash(new_password))
    flash("Password ကို အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ။", "success")
    return redirect(url_for("student.profile"))

# ============================================================
# NOTIFICATIONS
# ============================================================
@student_bp.route("/notifications")
@login_required
@library_user_required
def notifications():
    notifs = get_user_notifications(session["user_id"])
    mark_all_read(session["user_id"])
    return render_template("user/notifications.html", notifications=notifs)


@student_bp.route("/notifications/read/<int:notif_id>", methods=["POST"])
@login_required
@library_user_required
def notification_read(notif_id):
    mark_one_read(notif_id, session["user_id"])
    return redirect(url_for("student.notifications"))


# ============================================================
# RECOMMENDATIONS page
# ============================================================
@student_bp.route("/recommendations")
@login_required
@library_user_required
def recommendations():
    recommended = get_recommendations(session["user_id"], top_n=12)
    return render_template("user/recommendations.html", books=recommended)


# ============================================================
# BORROW REQUEST (Student submits → status = pending)
# ============================================================
@student_bp.route("/borrow/<int:book_id>/request", methods=["POST"])
@login_required
def borrow_request(book_id):
    # Allowed for both students and teachers
    if session.get("role") not in ["student", "teacher"]:
        flash("ဤ Page ကို ဝင်ခွင့်မရှိပါ။", "danger")
        return redirect(url_for("student.dashboard"))

    result = create_borrow_request(session["user_id"], book_id)
    if result == "limit_reached":
        limit = 10 if session.get("role") == "teacher" else 3
        flash(f"စာအုပ်ငှားယူမှု ကန့်သတ်ချက် ({limit} အုပ်) ပြည့်နေပါသည်။", "danger")
    elif result == "duplicate":
        flash("ဤစာအုပ်ကို ငှားယူရန် တောင်းဆိုထားပြီး (သို့မဟုတ်) လက်ဝယ်ရှိနေပြီး ဖြစ်ပါသည်။", "warning")
    else:
        flash("Borrow Request ပေးပို့ပြီးပါပြီ။ Admin Approve ပြုလုပ်ရန် စောင့်ပါ။", "success")
    return redirect(url_for("student.book_details", book_id=book_id))


# ============================================================
# BORROW HISTORY (Student views own borrow records)
# ============================================================
@student_bp.route("/borrow-history")
@login_required
@library_user_required
def borrow_history():
    from datetime import datetime
    history = get_student_borrow_history(session["user_id"])
    return render_template("user/borrow_history.html", history=history, now=datetime.now())

# ============================================================
# CLEARANCE / NO-DUES
# ============================================================
@student_bp.route("/clearance")
@login_required
@library_user_required
def clearance():
    from models.borrow_model import check_user_clearance
    status = check_user_clearance(session["user_id"])
    return render_template("user/clearance.html", status=status)


# ============================================================
# READING HISTORY (alias for history page)
# ============================================================
@student_bp.route("/reading-history")
@login_required
@library_user_required
def reading_history():
    read_hist = get_read_history(session["user_id"])
    download_hist = get_download_history(session["user_id"])
    return render_template(
        "user/history.html", read_history=read_hist, download_history=download_hist
    )


# ============================================================
# DOWNLOADS (Download History)
# ============================================================
@student_bp.route("/downloads")
@login_required
@library_user_required
def downloads():
    download_hist = get_download_history(session["user_id"])
    return render_template("user/downloads.html", download_history=download_hist)
