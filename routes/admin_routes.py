"""
routes/admin_routes.py
------------------------
Admin Module — full implementation.

Features:
- Dashboard (stats + charts data)
- User Management (Add/Edit/Delete/Activate/Deactivate)
- Book Management (Add/Edit/Delete + PDF/Cover upload + QR Code)
- Category / Author / Faculty Management
- Borrow Management (Approve/Reject/Return)
- Fine Management (Add/Mark Paid)
- Reports (Most Viewed, Most Downloaded, Active Users, Monthly)
- Announcements (Add/Edit/Delete)
"""

import os
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app
)
from werkzeug.security import generate_password_hash

from utils.decorators import login_required, admin_required
from utils.file_utils import save_uploaded_file
from utils.qrcode_gen import generate_book_qr

from models.book_model import get_all_books, get_book_by_id, get_all_categories, get_all_authors
from models.user_model import get_all_faculties
from models.admin_user_model import (
    get_all_users, get_user_by_id_admin,
    create_user_admin, update_user_admin,
    delete_user_admin, toggle_user_status,
    get_inactive_users, bulk_delete_users,
)
from models.admin_book_model import (
    add_book, update_book, delete_book, update_book_qr,
    add_category, update_category, delete_category,
    add_author, update_author, delete_author, get_author_by_id,
    add_faculty, update_faculty, delete_faculty, get_all_faculties_admin,
)
from models.db import mysql
from models.borrow_model import (
    get_all_borrow_requests, get_borrow_by_id, get_borrow_by_code,
    approve_borrow, reject_borrow, return_book, issue_book,
    mark_overdue_records, calculate_fine,
    get_all_fines, add_fine, mark_fine_paid, get_fine_total,
    get_borrow_stats,
)
from models.notification_model import (
    notify_all_students,
    notify_borrow_approved, notify_borrow_issued,
    notify_borrow_returned, notify_borrow_overdue, notify_fine_added,
)
from models.report_model import (
    get_dashboard_stats, get_most_viewed_books,
    get_most_downloaded_books, get_monthly_downloads,
    get_active_users, get_most_borrowed_books,
    get_user_role_stats, get_borrow_status_stats,
    get_category_book_counts, get_all_announcements,
    add_announcement, update_announcement,
    delete_announcement, get_announcement_by_id,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ============================================================
# DASHBOARD
# ============================================================
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    mark_overdue_records()
    stats = get_dashboard_stats()
    borrow_stats = get_borrow_stats()
    most_borrowed = get_most_borrowed_books(10)
    category_counts = get_category_book_counts()
    role_stats = get_user_role_stats()
    status_stats = get_borrow_status_stats()
    monthly = get_monthly_downloads(12)
    return render_template(
        "admin/dashboard.html",
        stats=stats, borrow_stats=borrow_stats,
        most_borrowed=most_borrowed,
        category_counts=category_counts,
        role_stats=role_stats,
        status_stats=status_stats,
        months=[r["month"] for r in monthly],
        dl_data=[r["total"] for r in monthly],
        name=session.get("name"),
    )


# ============================================================
# USER MANAGEMENT
# ============================================================
@admin_bp.route("/users")
@login_required
@admin_required
def users():
    inactive_only = request.args.get("inactive") == "1"
    if inactive_only:
        all_users = get_inactive_users(months=6)
    else:
        all_users = get_all_users()
    return render_template("admin/users.html", users=all_users, inactive_only=inactive_only)


@admin_bp.route("/users/bulk-delete", methods=["POST"])
@login_required
@admin_required
def users_bulk_delete():
    user_ids = request.form.getlist("user_ids")
    if user_ids:
        bulk_delete_users(user_ids)
        flash(f"{len(user_ids)} accounts have been deleted.", "success")
    else:
        flash("No accounts selected.", "warning")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/add", methods=["GET","POST"])
@login_required
@admin_required
def user_add():
    faculties = get_all_faculties()
    if request.method == "POST":
        student_id   = request.form.get("student_id","").strip() or None
        name         = request.form.get("name","").strip()
        email        = request.form.get("email","").strip()
        username     = request.form.get("username","").strip()
        password     = request.form.get("password","")
        role         = request.form.get("role","student")
        faculty_id   = request.form.get("faculty_id") or None
        if not all([name, email, username, password]):
            flash("Field အားလုံး ဖြည့်ပါ။","danger")
            return redirect(url_for("admin.user_add"))
        create_user_admin(student_id, name, email, username,
                          generate_password_hash(password), role, faculty_id)
        flash("User အသစ် ထည့်ပြီးပါပြီ။","success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=None, faculties=faculties)


@admin_bp.route("/users/edit/<int:user_id>", methods=["GET","POST"])
@login_required
@admin_required
def user_edit(user_id):
    user = get_user_by_id_admin(user_id)
    faculties = get_all_faculties()
    if request.method == "POST":
        name       = request.form.get("name","").strip()
        email      = request.form.get("email","").strip()
        faculty_id = request.form.get("faculty_id") or None
        role       = request.form.get("role","student")
        update_user_admin(user_id, name, email, faculty_id, role)
        flash("User ကို Update လုပ်ပြီးပါပြီ။","success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=user, faculties=faculties)


@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def user_delete(user_id):
    if user_id == session["user_id"]:
        flash("မိမိ Account ကိုယ်တိုင် မဖျက်နိုင်ပါ။","danger")
        return redirect(url_for("admin.users"))
    delete_user_admin(user_id)
    flash("User ကို ဖျက်ပြီးပါပြီ။","info")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/toggle/<int:user_id>/<int:status>", methods=["POST"])
@login_required
@admin_required
def user_toggle(user_id, status):
    toggle_user_status(user_id, status)
    msg = "Activate" if status == 1 else "Deactivate"
    flash(f"User ကို {msg} လုပ်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.users"))


# ============================================================
# BOOK MANAGEMENT
# ============================================================
@admin_bp.route("/books")
@login_required
@admin_required
def books():
    all_books = get_all_books()
    return render_template("admin/books.html", books=all_books)


@admin_bp.route("/books/add", methods=["GET","POST"])
@login_required
@admin_required
def book_add():
    categories = get_all_categories()
    authors    = get_all_authors()
    faculties  = get_all_faculties()
    if request.method == "POST":
        title         = request.form.get("title","").strip()
        isbn          = request.form.get("isbn","").strip() or None
        author_name   = request.form.get("author_name","").strip() or None
        author_id     = request.form.get("author_id") or None
        category_id   = request.form.get("category_id") or None
        faculty_id    = request.form.get("faculty_id") or None
        description   = request.form.get("description","").strip()
        resource_type = request.form.get("resource_type","book")
        publish_date  = request.form.get("publish_date") or None
        total_copies  = int(request.form.get("total_copies",0))

        pdf_file = save_uploaded_file(
            request.files.get("pdf_file"),
            current_app.config["UPLOAD_FOLDER_BOOKS"],
            current_app.config["ALLOWED_PDF_EXTENSIONS"],
        )
        cover_image = save_uploaded_file(
            request.files.get("cover_image"),
            current_app.config["UPLOAD_FOLDER_COVERS"],
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
        )

        if not pdf_file:
            flash("PDF File လိုအပ်ပါသည်။","danger")
            return redirect(url_for("admin.book_add"))

        book_id = add_book(title, isbn, author_name, author_id, category_id, faculty_id,
                           description, resource_type, pdf_file, cover_image,
                           publish_date, total_copies)

        # Auto QR Code generate
        qr_file = generate_book_qr(
            book_id, title,
            current_app.config["UPLOAD_FOLDER_QRCODES"]
        )
        update_book_qr(book_id, qr_file)

        # 🔔 Student အားလုံးကို New Book notification ပို့သည်
        notify_all_students(
            title=f"📚 New Book Added: {title}",
            message=f'Library ထဲသို့ "{title}" စာအုပ်အသစ် ထည့်သွင်းပြီးပါပြီ။',
            ntype="new_book"
        )

        flash("Book အသစ် ထည့်ပြီးပါပြီ (QR Code auto-generated)။","success")
        return redirect(url_for("admin.books"))
    return render_template("admin/book_form.html",
                           book=None, categories=categories,
                           authors=authors, faculties=faculties)


@admin_bp.route("/books/edit/<int:book_id>", methods=["GET","POST"])
@login_required
@admin_required
def book_edit(book_id):
    book       = get_book_by_id(book_id)
    categories = get_all_categories()
    authors    = get_all_authors()
    faculties  = get_all_faculties()
    if request.method == "POST":
        title         = request.form.get("title","").strip()
        isbn          = request.form.get("isbn","").strip() or None
        author_name   = request.form.get("author_name","").strip() or None
        author_id     = request.form.get("author_id") or None
        category_id   = request.form.get("category_id") or None
        faculty_id    = request.form.get("faculty_id") or None
        description   = request.form.get("description","").strip()
        resource_type = request.form.get("resource_type","book")
        publish_date  = request.form.get("publish_date") or None
        total_copies  = int(request.form.get("total_copies",0))

        pdf_file = save_uploaded_file(
            request.files.get("pdf_file"),
            current_app.config["UPLOAD_FOLDER_BOOKS"],
            current_app.config["ALLOWED_PDF_EXTENSIONS"],
        )
        cover_image = save_uploaded_file(
            request.files.get("cover_image"),
            current_app.config["UPLOAD_FOLDER_COVERS"],
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
        )
        update_book(book_id, title, isbn, author_name, author_id, category_id, faculty_id,
                    description, resource_type, publish_date, total_copies,
                    pdf_file, cover_image)
        flash("Book ကို Update လုပ်ပြီးပါပြီ။","success")
        return redirect(url_for("admin.books"))
    return render_template("admin/book_form.html",
                           book=book, categories=categories,
                           authors=authors, faculties=faculties)


@admin_bp.route("/books/delete/<int:book_id>", methods=["POST"])
@login_required
@admin_required
def book_delete(book_id):
    delete_book(book_id)
    flash("Book ကို ဖျက်ပြီးပါပြီ။","info")
    return redirect(url_for("admin.books"))


# ============================================================
# CATEGORY MANAGEMENT
# ============================================================
@admin_bp.route("/categories")
@login_required
@admin_required
def categories():
    cats = get_all_categories()
    return render_template("admin/categories.html", categories=cats)


@admin_bp.route("/categories/add", methods=["POST"])
@login_required
@admin_required
def category_add():
    name = request.form.get("name","").strip()
    desc = request.form.get("description","").strip()
    if name:
        add_category(name, desc)
        flash("Category ထည့်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/edit/<int:cat_id>", methods=["POST"])
@login_required
@admin_required
def category_edit(cat_id):
    name = request.form.get("name","").strip()
    desc = request.form.get("description","").strip()
    update_category(cat_id, name, desc)
    flash("Category ကို Update လုပ်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/delete/<int:cat_id>", methods=["POST"])
@login_required
@admin_required
def category_delete(cat_id):
    delete_category(cat_id)
    flash("Category ကို ဖျက်ပြီးပါပြီ။","info")
    return redirect(url_for("admin.categories"))
# ============================================================


# ============================================================
# FACULTY MANAGEMENT
# ============================================================
@admin_bp.route("/faculties")
@login_required
@admin_required
def faculties():
    all_faculties = get_all_faculties_admin()
    return render_template("admin/faculties.html", faculties=all_faculties)


@admin_bp.route("/faculties/add", methods=["POST"])
@login_required
@admin_required
def faculty_add():
    faculty_name = request.form.get("faculty_name","").strip()
    department   = request.form.get("department","").strip()
    if faculty_name:
        add_faculty(faculty_name, department)
        flash("Faculty ထည့်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.faculties"))


@admin_bp.route("/faculties/edit/<int:faculty_id>", methods=["POST"])
@login_required
@admin_required
def faculty_edit(faculty_id):
    faculty_name = request.form.get("faculty_name","").strip()
    department   = request.form.get("department","").strip()
    update_faculty(faculty_id, faculty_name, department)
    flash("Faculty ကို Update လုပ်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.faculties"))


@admin_bp.route("/faculties/delete/<int:faculty_id>", methods=["POST"])
@login_required
@admin_required
def faculty_delete(faculty_id):
    delete_faculty(faculty_id)
    flash("Faculty ကို ဖျက်ပြီးပါပြီ။","info")
    return redirect(url_for("admin.faculties"))


# ============================================================
# BORROW MANAGEMENT
# ============================================================
@admin_bp.route("/borrows")
@login_required
@admin_required
def borrows():
    from datetime import date
    # Mark overdue records automatically on page load
    mark_overdue_records()
    
    status_filter = request.args.get("status")
    search_query = request.args.get("search")
    
    requests = get_all_borrow_requests(status=status_filter, search=search_query)
    stats = get_borrow_stats()
    fine_total = get_fine_total()
    
    today = date.today().strftime("%Y-%m-%d")
    today_date = date.today()
    
    return render_template("admin/borrows.html",
                           requests=requests,
                           stats=stats,
                           fine_total=fine_total,
                           status_filter=status_filter,
                           search=search_query,
                           today=today,
                           today_date=today_date)


@admin_bp.route("/borrows/approve/<int:borrow_id>", methods=["POST"])
@login_required
@admin_required
def borrow_approve(borrow_id):
    try:
        qr_folder = current_app.config["UPLOAD_FOLDER_QRCODES"]
        borrow_id_code = approve_borrow(borrow_id, qr_folder, request.host_url.rstrip('/'))
        br = get_borrow_by_id(borrow_id)
        if br:
            notify_borrow_approved(br["user_id"], br["student_name"], br["book_title"], borrow_id_code)
        flash(f"Borrow Request ကို Approve လုပ်ပြီးပါပြီ။ ID: {borrow_id_code}", "success")
    except Exception as exc:
        mysql.connection.rollback()
        flash(f"Approve မအောင်မြင်ပါ: {exc}", "danger")
    return redirect(url_for("admin.borrows"))


@admin_bp.route("/borrows/lookup", methods=["POST"])
@login_required
@admin_required
def borrow_lookup():
    code = request.form.get("borrow_id_code", "").strip()
    if not code:
        flash("Borrow ID ထည့်ပါ။", "danger")
        return redirect(url_for("admin.borrows"))
    return redirect(url_for("admin.borrow_scan", borrow_id_code=code))


@admin_bp.route("/borrows/scan/<borrow_id_code>")
@login_required
@admin_required
def borrow_scan(borrow_id_code):
    br = get_borrow_by_code(borrow_id_code)
    if not br:
        flash("Borrow record မတွေ့ပါ။", "danger")
        return redirect(url_for("admin.borrows"))
    
    if br["status"] != "approved":
        flash(f"ဒီ record က {br['status']} ဖြစ်နေပါသည်။ Approved status သာ Issue လုပ်နိုင်ပါသည်။", "warning")
        return redirect(url_for("admin.borrows"))
        
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    return render_template("admin/borrow_issue_form.html", br=br, today=today)


@admin_bp.route("/borrows/issue/<int:borrow_id>", methods=["POST"])
@login_required
@admin_required
def borrow_issue(borrow_id):
    borrowed_date = request.form.get("borrowed_date")
    due_date = request.form.get("due_date")
    
    if not borrowed_date or not due_date:
        flash("ရက်စွဲများ အားလုံး ဖြည့်ပါ။", "danger")
        br = get_borrow_by_id(borrow_id)
        return redirect(url_for("admin.borrow_scan", borrow_id_code=br["borrow_id_code"]))
        
    try:
        issue_book(borrow_id, borrowed_date, due_date)
        br = get_borrow_by_id(borrow_id)
        notify_borrow_issued(br["user_id"], br["student_name"], br["book_title"], br["borrow_id_code"], borrowed_date, due_date)
        flash("စာအုပ် ထုတ်ပေးမှု (Issue) အောင်မြင်ပါသည်။", "success")
    except Exception as exc:
        mysql.connection.rollback()
        flash(f"Issue မအောင်မြင်ပါ: {exc}", "danger")
    return redirect(url_for("admin.borrows"))


@admin_bp.route("/borrows/reject/<int:borrow_id>", methods=["POST"])
@login_required
@admin_required
def borrow_reject(borrow_id):
    reject_borrow(borrow_id)
    flash("Borrow Request ကို Reject လုပ်ပြီးပါပြီ။","warning")
    return redirect(url_for("admin.borrows"))


@admin_bp.route("/borrows/return/<int:borrow_id>", methods=["POST"])
@login_required
@admin_required
def borrow_return(borrow_id):
    br = get_borrow_by_id(borrow_id)
    try:
        return_book(borrow_id)
    except Exception as exc:
        mysql.connection.rollback()
        flash(f"Return မအောင်မြင်ပါ: {exc}", "danger")
        return redirect(url_for("admin.borrows"))

    # Late return ဆိုရင် fine အလိုအလျောက် ထည့်
    if br and br["due_date"] and br["due_date"] < datetime.now().date():
        days_late, fine_amount = calculate_fine(borrow_id)
        if fine_amount > 0:
            add_fine(borrow_id, br["user_id"], fine_amount,
                     f"Late Return ({days_late} days)")
            notify_fine_added(br["user_id"], br["student_name"], br["book_title"], 
                              br["borrow_id_code"], days_late, fine_amount)
            flash(f"Book ပြန်အပ်ပြီး — Late {days_late} days, Fine: {fine_amount} Ks ထည့်ထားပါသည်။","warning")
        else:
            notify_borrow_returned(br["user_id"], br["student_name"], br["book_title"], br["borrow_id_code"])
            flash("Book ပြန်အပ်မှု မှတ်တမ်းတင်ပြီးပါပြီ။","success")
    else:
        notify_borrow_returned(br["user_id"], br["student_name"], br["book_title"], br["borrow_id_code"])
        flash("Book ပြန်အပ်မှု မှတ်တမ်းတင်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.borrows"))


# ============================================================
# FINE MANAGEMENT
# ============================================================
@admin_bp.route("/fines")
@login_required
@admin_required
def fines():
    all_fines = get_all_fines()
    return render_template("admin/fines.html", fines=all_fines)


@admin_bp.route("/fines/paid/<int:fine_id>", methods=["POST"])
@login_required
@admin_required
def fine_paid(fine_id):
    mark_fine_paid(fine_id)
    flash("Fine ကို ပေးချေပြီးဟု မှတ်တမ်းတင်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.fines"))


# ============================================================
# REPORTS
# ============================================================
@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    most_viewed = get_most_viewed_books(10)
    most_downloaded = get_most_downloaded_books(10)
    active_users = get_active_users(10)
    monthly = get_monthly_downloads(12)
    return render_template("admin/reports.html",
                           most_viewed=most_viewed,
                           most_downloaded=most_downloaded,
                           active_users=active_users,
                           monthly=monthly)


# ============================================================
# CHARTS
# ============================================================
@admin_bp.route("/charts")
@login_required
@admin_required
def charts():
    mark_overdue_records()
    stats = get_dashboard_stats()
    most_borrowed = get_most_borrowed_books(10)
    category_counts = get_category_book_counts()
    role_stats = get_user_role_stats()
    status_stats = get_borrow_status_stats()
    monthly = get_monthly_downloads(12)
    return render_template("admin/charts.html",
                           stats=stats,
                           most_borrowed=most_borrowed,
                           category_counts=category_counts,
                           role_stats=role_stats,
                           status_stats=status_stats,
                           monthly=monthly)


# ============================================================
# ANNOUNCEMENTS
# ============================================================
@admin_bp.route("/announcements")
@login_required
@admin_required
def announcements():
    all_ann = get_all_announcements()
    return render_template("admin/announcements.html", announcements=all_ann)


@admin_bp.route("/announcements/add", methods=["POST"])
@login_required
@admin_required
def announcement_add():
    title   = request.form.get("title","").strip()
    content = request.form.get("content","").strip()
    if title and content:
        add_announcement(title, content, session["user_id"])
        # 🔔 Student အားလုံးကို Announcement notification ပို့သည်
        notify_all_students(
            title=f"📢 Announcement: {title}",
            message=content[:200],
            ntype="announcement"
        )
        flash("Announcement ထည့်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.announcements"))


@admin_bp.route("/announcements/edit/<int:ann_id>", methods=["POST"])
@login_required
@admin_required
def announcement_edit(ann_id):
    title   = request.form.get("title","").strip()
    content = request.form.get("content","").strip()
    update_announcement(ann_id, title, content)
    flash("Announcement ကို Update လုပ်ပြီးပါပြီ။","success")
    return redirect(url_for("admin.announcements"))


@admin_bp.route("/announcements/delete/<int:ann_id>", methods=["POST"])
@login_required
@admin_required
def announcement_delete(ann_id):
    delete_announcement(ann_id)
    flash("Announcement ကို ဖျက်ပြီးပါပြီ။","info")
    return redirect(url_for("admin.announcements"))