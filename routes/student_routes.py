"""
routes/student_routes.py
--------------------------
Student Module — full implementation.

Features:
- Dashboard (recent + popular books)
- Search Books (Title / Author / Category / Faculty)
- View Book Details (+ view_count increment)
- Read Online (PDF inline viewer) (+ read_history log)
- Bookmark / Favorite (add, remove, list)
- View History (Read History)
- Profile Management (Update Profile, Change Password)
"""

import os
import re
from io import BytesIO
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, send_file, send_from_directory, current_app, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

from utils.decorators import login_required, student_required, library_user_required
from utils.file_utils import save_uploaded_file
from utils.recommender import get_recommendations
from services.ai_recommender import get_smart_recommendations
from utils.password_policy import check_password_policy
from utils.i18n import SUPPORTED_LANGUAGES, current_language, translate
from models.db import mysql

from models.book_model import (
    search_books, get_all_books, get_book_by_id, get_popular_books,
    get_collection_page,
    increment_view_count, 
    get_all_categories, get_all_authors,
)
from models.bookmark_model import add_bookmark, remove_bookmark, is_bookmarked, get_user_bookmarks
from models.history_model import (
    log_read_history, get_read_history,
)
from models.user_model import (
    get_user_by_id, update_password, update_profile, update_username,
    update_profile_image, get_all_faculties,
)
from models.report_model import (
    get_all_announcements,
    get_announcement_by_id,
    get_books_by_category_for_shelf,
    get_active_users,
    get_most_borrowed_books,
)
from models.borrow_model import (
    create_borrow_request,
    get_student_borrow_history,
    get_student_borrow_stats,
    get_student_fines,
    mark_overdue_records,
)
from models.notification_model import (
    get_user_notifications, get_unread_count, mark_all_read, mark_one_read,
    notify_borrow_request_submitted,
)
from utils.r2_storage import R2StorageError, download_bytes, is_enabled as r2_is_enabled
from services.text_summary import summarize_pasted_text

student_bp = Blueprint("student", __name__, url_prefix="/student")


# ============================================================
# DASHBOARD
# ============================================================
@student_bp.route("/dashboard")
@login_required
@library_user_required
def dashboard():
    from flask import request as _req
    faculty_scroll = _req.args.get("faculty") or ""
    try:
        faculty_scroll = str(int(faculty_scroll))
    except (ValueError, TypeError):
        faculty_scroll = ""
    user_id = session["user_id"]
    recent_books    = get_all_books(limit=8)
    popular_books   = get_popular_books(limit=10)
    recommended     = get_smart_recommendations(user_id, top_n=8)
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

    # Enrich faculties with books (full collection count + shelf preview)
    for faculty in faculties:
        fid = faculty.get('faculty_id')
        all_books_for_faculty = search_books(faculty_id=fid, primary_only=True)
        faculty['book_count'] = len(all_books_for_faculty)
        faculty['books'] = all_books_for_faculty[:6]

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
        overdue_count=stats.get("overdue", 0),
        faculty_scroll=faculty_scroll
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
    author_id = request.args.get("author") or request.args.get("author_id") or None
    resource_type = request.args.get("resource_type") or None
    availability = request.args.get("availability") or None
    sort_by = request.args.get("sort") or "newest"

    has_filters = any((keyword, category_id, faculty_id, author_id, resource_type, availability))
    if sort_by == "borrowed" and not has_filters:
        books = get_most_borrowed_books(limit=100)
    elif has_filters:
        books = search_books(
            keyword=keyword or None,
            category_id=category_id,
            faculty_id=faculty_id,
            author_id=author_id,
            resource_type=resource_type,
            primary_only=False,
        )
    else:
        books = get_all_books()

    if availability == "available":
        books = [book for book in books if int(book.get("available_copies") or 0) > 0]
    elif availability == "digital":
        books = [book for book in books if book.get("pdf_file")]

    if sort_by == "title":
        books = sorted(books, key=lambda row: (row.get("title") or "").lower())

    return render_template(
        "user/search.html",
        books=books,
        keyword=keyword,
        selected_category=category_id,
        selected_faculty=faculty_id,
        selected_author=author_id,
        selected_resource_type=resource_type,
        selected_availability=availability,
        selected_sort=sort_by,
        categories=get_all_categories(),
        authors=get_all_authors(),
        faculties=get_all_faculties(),
    )


@student_bp.route("/collection/<kind>/<int:collection_id>")
@login_required
@library_user_required
def collection(kind, collection_id):
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    if kind == "category":
        books_page = get_collection_page(category_id=collection_id, page=page, per_page=12)
        title = next((row.get("category_name") for row in get_all_categories() if str(row.get("category_id")) == str(collection_id)), "Category Collection")
    elif kind == "faculty":
        books_page = get_collection_page(faculty_id=collection_id, page=page, per_page=12)
        title = next((row.get("faculty_name") for row in get_all_faculties() if str(row.get("faculty_id")) == str(collection_id)), "Faculty Collection")
    else:
        abort(404)

    if page != books_page["page"]:
        return redirect(url_for(
            "student.collection",
            kind=kind,
            collection_id=collection_id,
            page=books_page["page"],
        ))

    return render_template(
        "user/collection.html",
        books=books_page["records"],
        books_page=books_page,
        collection_title=title,
        collection_kind=kind,
        collection_id=collection_id,
    )


@student_bp.route("/most-borrowed")
@login_required
@library_user_required
def most_borrowed():
    return render_template(
        "user/collection.html",
        books=get_most_borrowed_books(limit=100),
        collection_title="Most Borrowed Books",
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
        flash("ဤစာအုပ်ကို ဖတ့်ရှုခွင့်မရှိပါ။ (Teachers Only)", "danger")
        return redirect(url_for("student.book_details", book_id=book_id))

    # Read Online ဂိတ်: PDF ဖိုင်မရှိသောစာအုပ်ကို viewer မဖွင့်ဘဲ details သို့ ပြန်ပို့မည်
    if not book.get("pdf_file"):
        flash("ဤစာအုပ်တွင် PDF ဖိုင် မရှိသည့်အတွက် Online ဖတ့်ရှုမှု မရနိုင်ပါ။", "warning")
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

    if r2_is_enabled():
        try:
            pdf_bytes, content_type = download_bytes("books", book["pdf_file"])
        except R2StorageError:
            abort(404)
        resp = send_file(
            BytesIO(pdf_bytes),
            mimetype=content_type or "application/pdf",
            download_name=book["pdf_file"],
            as_attachment=False,
        )
    else:
        resp = send_from_directory(
            current_app.config["UPLOAD_FOLDER_BOOKS"], book["pdf_file"], as_attachment=False
        )
    # Defense-in-depth: never offer the PDF as a saved attachment (already
    # guaranteed by as_attachment=False), block proxy/content-sniffing
    # reuse, and keep it out of shared caches.
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Cache-Control'] = 'private, no-store'
    return resp


# ============================================================
# SUMMARIZE PASTED TEXT
# ============================================================
@student_bp.route("/book/<int:book_id>/summarize", methods=["GET", "POST"])
@login_required
@library_user_required
def summarize_book_text(book_id):
    """Summarize text copied from an authorized book's online reading session."""
    book = get_book_by_id(book_id)
    if not book:
        abort(404)

    restricted_types = {'thesis', 'research_paper', 'reference_book', 'teachers_guide'}
    if book.get('resource_type') in restricted_types and session.get('role') != 'teacher':
        abort(403)
    if not book.get('pdf_file'):
        flash(translate('read_online_unavailable'), 'warning')
        return redirect(url_for('student.book_details', book_id=book_id))

    result = None
    source_text = ''
    language = current_language()
    length = 'medium'
    if request.method == 'POST':
        source_text = (request.form.get('text') or '').strip()
        language = (request.form.get('language') or 'my').strip().lower()
        length = (request.form.get('length') or 'medium').strip().lower()
        try:
            result = summarize_pasted_text(source_text, language=language, length=length)
        except ValueError as exc:
            error_text = str(exc)
            if error_text == 'Text is required.':
                error_message = translate('summary_text_required')
            elif error_text.startswith('Text exceeds'):
                error_message = translate('summary_text_too_long')
            else:
                error_message = translate('summary_invalid_request')
            flash(error_message, 'danger')

    return render_template(
        'user/summarize_text.html',
        book=book,
        result=result,
        source_text=source_text,
        selected_language=language,
        selected_length=length,
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
# VIEW HISTORY (Read History only — Download feature removed)
# ============================================================
@student_bp.route("/history")
@login_required
@library_user_required
def history():
    read_history = get_read_history(session["user_id"])
    return render_template(
        "user/history.html", read_history=read_history
    )


# ============================================================
# PROFILE MANAGEMENT
# ============================================================
@student_bp.route("/profile", methods=["GET"])
@login_required
@library_user_required
def profile():
    user = get_user_by_id(session["user_id"])
    faculties = get_all_faculties()
    return render_template("user/profile.html", user=user, faculties=faculties)


@student_bp.route("/profile/update", methods=["POST"])
@login_required
@library_user_required
def profile_update():
    """Update only the editable username and/or profile picture.

    Name, email, faculty, role, and university identity are deliberately
    not accepted from this form and remain sourced from the official record.
    """
    user_id = session["user_id"]
    username = request.form.get("username", "").strip()
    profile_file = request.files.get("profile_image")
    changed = False

    if username:
        if len(username) < 3 or len(username) > 50 or not re.fullmatch(r"[A-Za-z0-9_]+", username):
            flash(translate("profile_username_invalid"), "danger")
            return redirect(url_for("student.profile"))
        if username != (session.get("username") or ""):
            if not update_username(user_id, username):
                flash(translate("profile_username_taken"), "danger")
                return redirect(url_for("student.profile"))
            session["username"] = username
            changed = True

    if profile_file and profile_file.filename:
        saved = save_uploaded_file(
            profile_file,
            current_app.config["LIBRARY_STORAGE_PROFILES"],
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
        )
        if not saved:
            flash(translate("profile_image_invalid"), "danger")
            return redirect(url_for("student.profile"))
        update_profile_image(user_id, saved)
        session["profile_image"] = saved
        changed = True

    if not changed:
        flash(translate("profile_required_fields"), "warning")
        return redirect(url_for("student.profile"))

    flash(translate("profile_update_success"), "success")
    return redirect(url_for("student.profile"))


@student_bp.route("/profile/change-password", methods=["POST"])
@login_required
@library_user_required
def change_password():
    user = get_user_by_id(session["user_id"])

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not check_password_hash(user["password"], current_password):
        flash(translate("cp_wrong_current"), "danger")
        return redirect(url_for("student.profile"))

    policy = check_password_policy(new_password)
    if not policy["all_ok"]:
        flash(translate("cp_policy_failed"), "danger")
        return redirect(url_for("student.profile"))

    if new_password != confirm_password:
        flash(translate("cp_mismatch"), "danger")
        return redirect(url_for("student.profile"))

    update_password(session["user_id"], generate_password_hash(new_password))
    flash(translate("cp_success"), "success")
    return redirect(url_for("student.profile"))

# ============================================================
# LANGUAGE AND LIBRARY RULES
# ============================================================
@student_bp.route("/language/<language>")
@login_required
@library_user_required
def set_language(language):
    if language not in SUPPORTED_LANGUAGES:
        flash("Unsupported language.", "warning")
        return redirect(request.referrer or url_for("student.dashboard"))
    session["language"] = language
    return redirect(request.referrer or url_for("student.dashboard"))


@student_bp.route("/rules")
@login_required
@library_user_required
def library_rules():
    return render_template("user/rules.html")


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
    user_id = session["user_id"]
    # The existing TF-IDF + cosine similarity engine is used as-is.
    recommended = get_smart_recommendations(user_id, top_n=8)

    # Honest cold-start detection: the engine already falls back to popular
    # books when the user has no read/download/bookmark activity. We label it
    # so the UI never presents generic books as "Recommended for You".
    cold_start = bool(not _user_has_activity(user_id) or not recommended)

    # "Because You Read..." — only shown when real read_history data exists.
    because_you_read = _books_because_you_read(user_id, limit=8)

    # Recently Added — real books ordered by upload date.
    recently_added = _recently_added_books(limit=8)

    # Popular / Most Borrowed — real borrow activity from the library.
    most_borrowed = get_most_borrowed_books(limit=8)
    return render_template(
        "user/recommendations.html",
        books=recommended,
        cold_start=cold_start,
        because_you_read=because_you_read,
        recently_added=recently_added,
        most_borrowed=most_borrowed,
    )


def _user_has_activity(user_id):
    """Real reading / bookmark activity exists for this user."""
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT user_id FROM ("
        " SELECT user_id FROM read_history WHERE user_id = %s"
        " UNION ALL"
        " SELECT user_id FROM bookmarks WHERE user_id = %s"
        ") t LIMIT 1",
        (user_id, user_id),
    )
    has = bool(cur.fetchone())
    cur.close()
    return has


def _books_because_you_read(user_id, limit=8):
    """Book records for the user's real read_history entries (freshest first)."""
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT rh.book_id FROM read_history rh "
        "WHERE rh.user_id = %s "
        "GROUP BY rh.book_id ORDER BY MAX(rh.read_date) DESC LIMIT %s",
        (user_id, limit),
    )
    ids = [row["book_id"] for row in cur.fetchall()]
    if not ids:
        cur.close()
        return []
    placeholders = ",".join("%s" for _ in ids)
    cur.execute(
        f"SELECT b.book_id, b.title, b.cover_image, b.author_name, "
        f"COALESCE(c.category_name,'') AS category_name, b.resource_type "
        f"FROM books b "
        f"LEFT JOIN categories c ON b.category_id = c.category_id "
        f"WHERE b.book_id IN ({placeholders}) AND COALESCE(b.is_archived, 0) = 0",
        ids,
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def _recently_added_books(limit=8):
    """Most recently uploaded books (real data)."""
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT b.book_id, b.title, b.cover_image, "
        "COALESCE(a.author_name,'') AS author_name, "
        "COALESCE(c.category_name,'') AS category_name, "
        "b.resource_type "
        "FROM books b "
        "LEFT JOIN authors a ON b.author_id = a.author_id "
        "LEFT JOIN categories c ON b.category_id = c.category_id "
        "WHERE COALESCE(b.is_archived, 0) = 0 "
        "ORDER BY b.upload_date DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


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
        book = get_book_by_id(book_id)
        notify_borrow_request_submitted(
            session["user_id"],
            book["title"] if book else str(book_id),
            result,
        )
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
    mark_overdue_records()
    history = get_student_borrow_history(session["user_id"])
    return render_template("user/borrow_history.html", history=history, now=datetime.now())


@student_bp.route("/fines")
@login_required
@library_user_required
def fines():
    status_filter = request.args.get("status")
    mark_overdue_records()
    user_id = session["user_id"]
    all_fine_rows = get_student_fines(user_id)
    fine_rows = get_student_fines(user_id, status_filter)
    history = get_student_borrow_history(user_id)
    summary = {
        "finalized_total": sum(float(row.get("amount") or 0) for row in all_fine_rows),
        "finalized_unpaid": sum(float(row.get("amount") or 0) for row in all_fine_rows if not row.get("is_paid")),
        "finalized_paid": sum(float(row.get("amount") or 0) for row in all_fine_rows if row.get("is_paid")),
        "estimated_overdue": sum(
            float(row.get("estimated_fine") or 0)
            for row in history
            if row.get("status") in ("borrowed", "overdue")
        ),
    }
    return render_template("user/fines.html", fines=fine_rows, summary=summary, status_filter=status_filter)

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
    return render_template(
        "user/history.html", read_history=read_hist
    )


# ============================================================
# ANNOUNCEMENTS — list page + detail view
# Reuses the real announcements table via report_model (no mock data).
# ============================================================
@student_bp.route("/announcements")
@login_required
@library_user_required
def announcements():
    search = request.args.get("search", "").strip() or None
    all_ann = get_all_announcements(search=search)
    return render_template(
        "user/announcements.html", announcements=all_ann, search=search
    )


@student_bp.route("/announcements/<int:ann_id>")
@login_required
@library_user_required
def announcement_detail(ann_id):
    # Reuse the same model helper the admin panel uses for the detail lookup.
    ann = get_announcement_by_id(ann_id)
    if not ann:
        abort(404)
    return render_template("user/announcement_detail.html", ann=ann)


# ============================================================
# MY LIBRARY — user-centric hub (Bookmarks / Continue Reading /
# Borrowed / History). Pure read-only aggregation of real data;
# every row comes from the existing bookmarks, read_history
# and borrow_requests tables (no mock data).
# ============================================================
@student_bp.route("/my-library")
@login_required
@library_user_required
def my_library():
    user_id = session["user_id"]
    tab = (request.args.get("tab") or "").strip().lower() or "bookmarks"
    if tab not in ("bookmarks", "continue", "borrowed", "history"):
        tab = "bookmarks"

    # Bookmarks — real user bookmarks with full book details
    bookmarks = get_user_bookmarks(user_id)

    # Continue Reading — real recent reads only.
    # NOTE: read_history has no page/percentage progress columns,
    # so we show only the last-read timestamp (no invented progress).
    recently_read = get_read_history(user_id, limit=12)

    # Borrowed — real borrow records with real statuses and due dates
    mark_overdue_records()  # refresh statuses against real due dates
    borrows = get_student_borrow_history(user_id)
    active_borrows = [b for b in borrows if b.get("status") in ("pending", "approved", "borrowed", "overdue")]

    # History — real read activity rows
    read_hist = get_read_history(user_id, limit=30)

    return render_template(
        "user/my_library.html",
        tab=tab,
        bookmarks=bookmarks,
        recently_read=recently_read,
        borrows=borrows,
        active_borrows=active_borrows,
        read_history=read_hist,
    )
