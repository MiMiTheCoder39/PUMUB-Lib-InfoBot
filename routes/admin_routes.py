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
from datetime import date, datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app
)
from werkzeug.security import generate_password_hash

from utils.decorators import login_required, admin_required
from utils.i18n import SUPPORTED_LANGUAGES, translate
from utils.file_utils import save_uploaded_file
from utils.password_policy import check_password_policy
from utils.r2_storage import R2StorageError, delete_object, is_enabled as r2_is_enabled

from models.book_model import get_all_books, get_book_by_id, get_all_categories, get_all_authors
from models.admin_book_model import (
    archive_book, restore_book, delete_book,
    get_book_by_id_admin, get_book_dependency_audit, get_admin_archived_page,
)
from models.user_model import get_all_faculties
from models.university_records import (
    get_records, get_record_by_id, get_record_counts, create_record,
    update_record, delete_record_safe, VALID_STATUSES,
)
from models.admin_user_model import (
    get_all_users, get_user_by_id_admin,
    create_user_admin, update_user_admin,
    delete_user_admin, toggle_user_status,
    get_inactive_users, bulk_delete_users,
    get_admin_users, get_admin_user_summary, get_user_dependency_counts,
    reset_user_password_admin,
)
from models.admin_book_model import (
    BookStateError,
    add_book, update_book, delete_book,
    add_category, update_category, delete_category,
    add_author, update_author, delete_author, get_author_by_id,
    add_faculty, update_faculty, delete_faculty, get_all_faculties_admin,
    get_admin_book_page, get_admin_book_summary, get_admin_category_rows,
    book_state_hints,
    get_admin_faculty_rows, get_category_dependency_count,
    get_faculty_dependency_counts, get_book_dependency_count,
    get_author_dependency_count,
)
from models.db import mysql
from models.borrow_model import (
    get_all_borrow_requests, get_borrow_by_id, get_borrow_by_code,
    approve_borrow, reject_borrow, return_book, issue_book,
    mark_overdue_records,     calculate_fine,
    get_all_fines, add_fine, mark_fine_paid, get_fine_total,
    get_fine_summary, get_fine_report_years, get_monthly_fine_report,

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
    get_category_book_counts, get_monthly_borrow_activity,
    get_recent_borrow_requests, get_borrowing_trend,
    get_borrow_by_faculty, get_borrow_by_category, get_fine_trend,
    get_admin_report, get_all_announcements,
    add_announcement, update_announcement,
    delete_announcement, get_announcement_by_id,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/language/<language>")
@login_required
@admin_required
def set_language(language):
    if language not in SUPPORTED_LANGUAGES:
        flash("Unsupported language.", "warning")
        return redirect(request.referrer or url_for("admin.dashboard"))
    session["language"] = language
    return redirect(request.referrer or url_for("admin.dashboard"))


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
    fine_summary = get_fine_summary()
    recent_requests = get_recent_borrow_requests(8)
    role_stats = get_user_role_stats()
    status_stats = get_borrow_status_stats()
    status_labels = {'pending': translate('pending'), 'approved': translate('approved'), 'borrowed': translate('borrowed'), 'overdue': translate('overdue'), 'returned': translate('returned'), 'rejected': translate('rejected')}
    monthly_borrows = get_monthly_borrow_activity(12)
    dashboard_stats = dict(stats)
    dashboard_stats.update({
        "total_students": stats.get("total_students", 0),
        "overdue": borrow_stats.get("overdue", 0),
        "unpaid_fines": fine_summary.get("unpaid_total", 0),
    })
    # Phase 4 (display-only): Active · Archived split under Total Books KPI.
    # total_books stays the full library inventory (Phase 3 decision).
    cur = mysql.connection.cursor()
    cur.execute("SELECT COALESCE(SUM(is_archived = 0), 0) AS books_active, COALESCE(SUM(is_archived = 1), 0) AS books_archived FROM books")
    split = cur.fetchone()
    cur.close()
    dashboard_stats["books_active"] = int(split["books_active"] or 0)
    dashboard_stats["books_archived"] = int(split["books_archived"] or 0)
    return render_template(
        "admin/dashboard.html",
        stats=dashboard_stats, borrow_stats=borrow_stats,
        fine_summary=fine_summary,
        recent_requests=recent_requests,
        role_stats=role_stats,
        status_stats=status_stats,
        status_labels=status_labels,
        borrow_months=[r["month"] for r in monthly_borrows],
        borrow_data=[r["total"] for r in monthly_borrows],
        trend_labels=[r["month"] for r in monthly_borrows],
        trend_data=[r["total"] for r in monthly_borrows],
        name=session.get("name"),
    )


# ============================================================
# USER MANAGEMENT
# ============================================================
@admin_bp.route("/users")
@login_required
@admin_required
def users():
    role = request.args.get("role") or None
    status = request.args.get("status") or ("inactive" if request.args.get("inactive") == "1" else None)
    search = request.args.get("search", "").strip()
    try:
        faculty_id = int(request.args["faculty_id"]) if request.args.get("faculty_id") else None
    except ValueError:
        faculty_id = None
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    users_page = get_admin_users(role=role, status=status, faculty_id=faculty_id, search=search or None, page=page, per_page=25)
    query_args = request.args.to_dict(flat=True)
    query_args["page"] = max(1, users_page["page"] - 1)
    pagination_prev_url = url_for("admin.users", **query_args)
    query_args["page"] = min(users_page["pages"], users_page["page"] + 1)
    pagination_next_url = url_for("admin.users", **query_args)
    return render_template(
        "admin/users.html", users=users_page["records"], users_page=users_page,
        user_summary=get_admin_user_summary(), record_counts=get_record_counts(), faculties=get_all_faculties(),
        role_filter=role, status_filter=status, faculty_id=faculty_id, search=search,
        pagination_prev_url=pagination_prev_url, pagination_next_url=pagination_next_url,
    )


@admin_bp.route("/users/reset-password/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def user_reset_password(user_id):
    """Set a temporary password for a non-admin library user."""
    user = get_user_by_id_admin(user_id)
    if not user or user.get("role") == "admin":
        flash(translate("admin_reset_user_invalid"), "danger")
        return redirect(url_for("admin.users"))

    if request.method == "POST":
        temporary_password = request.form.get("temporary_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not temporary_password:
            flash(translate("admin_reset_password_required"), "danger")
            return redirect(url_for("admin.users"))
        if temporary_password != confirm_password:
            flash(translate("admin_reset_password_mismatch"), "danger")
            return redirect(url_for("admin.users"))
        if not check_password_policy(temporary_password)["all_ok"]:
            flash(translate("admin_reset_password_weak"), "danger")
            return redirect(url_for("admin.users"))
        if not reset_user_password_admin(user_id, generate_password_hash(temporary_password)):
            flash(translate("admin_reset_user_invalid"), "danger")
            return redirect(url_for("admin.users"))
        flash(translate("admin_reset_success"), "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/reset_password.html", user=user)


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
        # Phase 6: role is controlled by the official university record and
        # the application layer guarantees exactly one admin account, so a
        # submitted role value is ignored and the existing role is kept.
        update_user_admin(user_id, name, email, faculty_id)
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
    dependencies = get_user_dependency_counts(user_id)
    if dependencies and (dependencies.get("borrows", 0) or dependencies.get("fines", 0) or dependencies.get("notifications", 0)):
        flash(translate("dependency_warning") + f" ({dependencies.get('borrows', 0)} borrow records, {dependencies.get('fines', 0)} fines)", "warning")
        return redirect(url_for("admin.users"))
    delete_user_admin(user_id)
    flash("User ကို ဖျက်ပြီးပါပြီ။", "success")
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
    search = request.args.get("search", "").strip()
    availability = request.args.get("availability") or None
    resource_type = request.args.get("resource_type") or None
    try:
        category_id = int(request.args["category_id"]) if request.args.get("category_id") else None
    except ValueError:
        category_id = None
    # faculty dropdown value may contain comma-separated faculty ids (one
    # faculty name can map to several department rows in the faculties table)
    faculty_ids = None
    if request.args.get("faculty_id"):
        try:
            faculty_ids = [int(v) for v in str(request.args["faculty_id"]).split(",") if v.strip().isdigit()]
            faculty_ids = [v for v in faculty_ids if v > 0] or None
        except ValueError:
            faculty_ids = None
    faculty_id = faculty_ids
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    # Phase 3 archive lifecycle: ?archive=1 shows the Archived Books workspace.
    archive_mode = request.args.get("archive") == "1"
    if archive_mode:
        books_page = get_admin_archived_page(search=search or None, page=page, per_page=25)
        query_args = request.args.to_dict(flat=True)
        query_args.pop("archive", None)
        query_args["page"] = max(1, books_page["page"] - 1)
        pagination_prev_url = url_for("admin.books", archive="1", **query_args)
        query_args["page"] = min(books_page["pages"], books_page["page"] + 1)
        pagination_next_url = url_for("admin.books", archive="1", **query_args)
        return render_template(
            "admin/books.html", books=books_page["records"], books_page=books_page,
            book_summary=get_admin_book_summary(), categories=get_all_categories(), faculties=get_all_faculties(),
            search=search, category_id=category_id, faculty_id=faculty_id, faculty_id_list=[",".join(str(v) for v in faculty_ids)] if faculty_ids else [""], availability=availability,
            resource_type=resource_type, pagination_prev_url=pagination_prev_url, pagination_next_url=pagination_next_url,
            archive_mode=True, archived_count=int(get_admin_book_summary().get("archived_books") or 0),
        )
    books_page = get_admin_book_page(search=search or None, category_id=category_id, faculty_ids=faculty_ids, availability=availability, resource_type=resource_type, page=page, per_page=25)
    query_args = request.args.to_dict(flat=True)
    query_args["page"] = max(1, books_page["page"] - 1)
    pagination_prev_url = url_for("admin.books", **query_args)
    query_args["page"] = min(books_page["pages"], books_page["page"] + 1)
    pagination_next_url = url_for("admin.books", **query_args)
    return render_template(
        "admin/books.html", books=books_page["records"], books_page=books_page,
        book_summary=get_admin_book_summary(), categories=get_all_categories(), faculties=get_all_faculties(),
        search=search, category_id=category_id, faculty_id=faculty_id, faculty_id_list=[",".join(str(v) for v in faculty_ids)] if faculty_ids else [""], availability=availability,
        resource_type=resource_type, pagination_prev_url=pagination_prev_url, pagination_next_url=pagination_next_url,
        archive_mode=False, archived_count=int(get_admin_book_summary().get("archived_books") or 0),
    )


@admin_bp.route("/books/add", methods=["GET","POST"])
@login_required
@admin_required
def book_add():
    categories = get_all_categories()
    authors    = get_all_authors()
    faculties  = get_all_faculties()
    if request.method == "POST":
        title            = request.form.get("title","").strip()
        isbn             = request.form.get("isbn","").strip() or None
        author_name      = request.form.get("author_name","").strip() or None
        author_id        = request.form.get("author_id") or None
        category_id      = request.form.get("category_id") or None
        faculty_id       = request.form.get("faculty_id") or None
        description      = request.form.get("description","").strip()
        resource_type    = request.form.get("resource_type","book")
        publish_date     = request.form.get("publish_date") or None
        total_copies     = request.form.get("total_copies", 0)
        # is_physical ကို form string ('1'/'on'/'0') မှ bool သို့ convert လုပ်သည့် method ကို
        # ရှေ့ဆက်လက်သုံးရန် helper ထားသည်။
        is_physical = request.form.get("is_physical", "0") not in ("", "0", "false", "no")
        publisher        = request.form.get("publisher", "").strip() or None
        edition          = request.form.get("edition", "").strip() or None
        publication_year = request.form.get("publication_year", "").strip() or None

        # PDF သည် optional ဖြစ်သည် — Physical Book အတွက် မလိုအပ် (Phase 1)
        pdf_file = save_uploaded_file(
            request.files.get("pdf_file"),
            current_app.config["UPLOAD_FOLDER_BOOKS"],
            current_app.config["ALLOWED_PDF_EXTENSIONS"],
        ) or None
        cover_image = save_uploaded_file(
            request.files.get("cover_image"),
            current_app.config["UPLOAD_FOLDER_COVERS"],
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
        )

        try:
            book_id = add_book(title, isbn, author_name, author_id, category_id, faculty_id,
                               description, resource_type, pdf_file, cover_image,
                               publish_date, total_copies, is_physical,
                               publisher=publisher, edition=edition,
                               publication_year=publication_year)
        except BookStateError as ex:
            flash(translate(str(ex)) or str(ex), "danger")
            return redirect(url_for("admin.book_add"))

        # Book QR feature retired (approved scope) — no generation/management.
        # Borrow QR (physical-borrow workflow) is a separate, untouched system.

        # 🔔 Student အားလုံးကို New Book notification ပို့သည်
        notify_all_students(
            title=f"📚 New Book Added: {title}",
            message=f'Library ထဲသို့ "{title}" စာအုပ်အသစ် ထည့်သွင်းပြီးပါပြီ။',
            ntype="new_book"
        )

        flash(translate("book_added_success"), "success")
        return redirect(url_for("admin.books"))
    return render_template("admin/book_form.html",
                           book=None, categories=categories,
                           authors=authors, faculties=faculties,
                           state_hints=book_state_hints(),
                           no_department=translate("no_department"),
                           all_departments=translate("all_departments"))


@admin_bp.route("/books/edit/<int:book_id>", methods=["GET","POST"])
@login_required
@admin_required
def book_edit(book_id):
    book       = get_book_by_id(book_id)
    categories = get_all_categories()
    authors    = get_all_authors()
    faculties  = get_all_faculties()
    if request.method == "POST":
        title            = request.form.get("title","").strip()
        isbn             = request.form.get("isbn","").strip() or None
        author_name      = request.form.get("author_name","").strip() or None
        author_id        = request.form.get("author_id") or None
        category_id      = request.form.get("category_id") or None
        faculty_id       = request.form.get("faculty_id") or None
        description      = request.form.get("description","").strip()
        resource_type    = request.form.get("resource_type","book")
        publish_date     = request.form.get("publish_date") or None
        total_copies     = request.form.get("total_copies", 0)
        is_physical = request.form.get("is_physical", "0") not in ("", "0", "false", "no")
        remove_pdf = request.form.get("remove_pdf") not in (None, "", "0", "false", "no")
        publisher        = request.form.get("publisher", "").strip() or None
        edition          = request.form.get("edition", "").strip() or None
        publication_year = request.form.get("publication_year", "").strip() or None

        pdf_file = save_uploaded_file(
            request.files.get("pdf_file"),
            current_app.config["UPLOAD_FOLDER_BOOKS"],
            current_app.config["ALLOWED_PDF_EXTENSIONS"],
        ) or None
        cover_image = save_uploaded_file(
            request.files.get("cover_image"),
            current_app.config["UPLOAD_FOLDER_COVERS"],
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
        ) or None

        try:
            update_book(book_id, title, isbn, author_name, author_id, category_id, faculty_id,
                        description, resource_type, publish_date, total_copies,
                        pdf_file=pdf_file, cover_image=cover_image,
                        is_physical=is_physical, remove_pdf=remove_pdf,
                        publisher=publisher, edition=edition,
                        publication_year=publication_year)
        except BookStateError as ex:
            flash(translate(str(ex)) or str(ex), "danger")
            return redirect(url_for("admin.book_edit", book_id=book_id))
        flash(translate("book_updated_success"), "success")
        return redirect(url_for("admin.books"))
    return render_template("admin/book_form.html",
                           book=book, categories=categories,
                           authors=authors, faculties=faculties,
                           state_hints=book_state_hints(),
                           no_department=translate("no_department"),
                           all_departments=translate("all_departments"))


@admin_bp.route("/books/delete/<int:book_id>", methods=["POST"])
@login_required
@admin_required
def book_delete(book_id):
    """Legacy hard-delete is retired (Phase 3). Any direct call is routed to
    the archive lifecycle instead — books must be archived first and are only
    permanently removable after the dependency audit passes."""
    book = get_book_by_id_admin(book_id)
    if not book:
        flash(translate("book_not_found") or "Book not found", "danger")
        return redirect(url_for("admin.books"))
    if book.get("is_archived"):
        return permanent_delete_flow(book_id)
    ok = archive_book(book_id)
    flash(translate("book_archived_success") or "စာအုပ်ကို Archive လုပ်ပြီးပါပြီ။", "success" if ok else "warning")
    return redirect(url_for("admin.books"))


@admin_bp.route("/books/archive/<int:book_id>", methods=["POST"])
@login_required
@admin_required
def book_archive(book_id):
    book = get_book_by_id_admin(book_id)
    if not book:
        flash(translate("book_not_found") or "Book not found", "danger")
        return redirect(url_for("admin.books"))
    if book.get("is_archived"):
        flash(translate("book_already_archived") or "စာအုပ်ကို Archive လုပ်ပြီးသားဖြစ်သည်", "warning")
        return redirect(url_for("admin.books"))
    archive_book(book_id)
    flash(translate("book_archived_success") or "စာအုပ်ကို Archive လုပ်ပြီးပါပြီ။", "success")
    return redirect(url_for("admin.books"))


@admin_bp.route("/books/restore/<int:book_id>", methods=["POST"])
@login_required
@admin_required
def book_restore(book_id):
    book = get_book_by_id_admin(book_id)
    if not book or not book.get("is_archived"):
        flash(translate("book_not_archived") or "Archive လုပ်ထားသော စာအုပ်မဟုတ်ပါ", "warning")
        return redirect(url_for("admin.books"))
    restore_book(book_id)
    flash(translate("book_restored_success") or "စာအုပ်ကို Active ပြန်လည်ပြုလုက်ပြီးပါပြီ။", "success")
    return redirect(url_for("admin.books", archive="1"))


@admin_bp.route("/books/permanent-delete/<int:book_id>", methods=["POST"])
@login_required
@admin_required
def book_permanent_delete(book_id):
    return permanent_delete_flow(book_id)


def permanent_delete_flow(book_id):
    """Dependency-checked permanent delete for ARCHIVED books only.

    Historical records (borrow / fine / bookmark / download / read history)
    are never removed. If any dependency exists the delete is BLOCKED and the
    exact reasons are reported back to the admin.
    """
    book = get_book_by_id_admin(book_id)
    if not book:
        flash(translate("book_not_found") or "Book not found", "danger")
        return redirect(url_for("admin.books"))
    if not book.get("is_archived"):
        flash(translate("book_not_archived") or "Archive လုပ်ထားသော စာအုပ်ကိုသာ Permanent Delete လုပ်နိုင်သည်", "warning")
        return redirect(url_for("admin.books"))
    audit = get_book_dependency_audit(book_id)
    if audit["has_dependencies"]:
        reasons = [f"{table}: {audit[table]} record(s)" for table, n in audit.items()
                   if table != "has_dependencies" and n > 0]
        reason_text = "; ".join(reasons)
        msg = (translate("book_delete_blocked") or "စာအုပ်၏ မှတ်တမ်းများ ရှိနေသောကြောင့် Permanent Delete လုပ်၍ မရပါ။ ") + "(" + reason_text + ")"
        flash(msg, "danger")
        return redirect(url_for("admin.books"))
    # Clean of all history — permanent delete is safe (nothing historical to lose).
    try:
        delete_book(book_id)
        # Remove uploaded assets so no orphan files remain.
        for rel in (book.get("pdf_file"), book.get("cover_image")):
            if rel:
                try:
                    # External Library Storage — filename only in DB; resolve via
                    # storage root constants (no machine-specific absolute path).
                    from config import Config
                    if r2_is_enabled():
                        # Try both prefixes because this loop handles PDF and cover names.
                        for prefix in ("books", "covers"):
                            try:
                                delete_object(prefix, rel)
                            except R2StorageError:
                                pass
                    candidates = [
                        os.path.join(Config.LIBRARY_STORAGE_BOOKS, rel),
                        os.path.join(Config.LIBRARY_STORAGE_COVERS, rel),
                    ]
                    removed = False
                    for cpath in candidates:
                        if os.path.exists(cpath):
                            os.remove(cpath)
                            removed = True
                            break
                    # Fallback: legacy static/uploads/ files for pre-migration setups
                    if not removed:
                        legacy = os.path.join(current_app.root_path, "static", "uploads", rel)
                        if os.path.exists(legacy):
                            os.remove(legacy)
                except OSError:
                    pass
        flash(translate("book_permanent_deleted") or "စာအုပ်ကို အနှစ်ချုပ်အနေနဲ့ Permanent Delete လုပ်ပြီးပါပြီ။", "success")
    except Exception:
        flash("Permanent Delete အောင်မြင်စွာ မလုပ်နိုင်ပါ", "danger")
    return redirect(url_for("admin.books"))


# ============================================================
# CATEGORY MANAGEMENT
# ============================================================
@admin_bp.route("/categories")
@login_required
@admin_required
def categories():
    cats = get_admin_category_rows()
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
    dependency_count = get_category_dependency_count(cat_id)
    if dependency_count:
        flash(translate("dependency_warning") + f" ({dependency_count} books)", "warning")
        return redirect(url_for("admin.categories"))
    delete_category(cat_id)
    flash("Category ကို ဖျက်ပြီးပါပြီ။", "success")
    return redirect(url_for("admin.categories"))
# ============================================================


# ============================================================
# AUTHOR MANAGEMENT
# ============================================================
@admin_bp.route("/authors")
@login_required
@admin_required
def authors():
    return render_template("admin/authors.html", authors=get_all_authors())


@admin_bp.route("/authors/add", methods=["POST"])
@login_required
@admin_required
def author_add():
    name = request.form.get("name", "").strip()
    bio = request.form.get("bio", "").strip()
    if name:
        add_author(name, bio)
        flash("Author added.", "success")
    return redirect(url_for("admin.authors"))


@admin_bp.route("/authors/edit/<int:author_id>", methods=["POST"])
@login_required
@admin_required
def author_edit(author_id):
    name = request.form.get("name", "").strip()
    bio = request.form.get("bio", "").strip()
    if name:
        update_author(author_id, name, bio)
        flash("Author updated.", "success")
    return redirect(url_for("admin.authors"))


@admin_bp.route("/authors/delete/<int:author_id>", methods=["POST"])
@login_required
@admin_required
def author_delete(author_id):
    dependency_count = get_author_dependency_count(author_id)
    if dependency_count:
        flash(translate("dependency_warning") + f" ({dependency_count} books)", "warning")
        return redirect(url_for("admin.authors"))
    delete_author(author_id)
    flash("Author deleted.", "success")
    return redirect(url_for("admin.authors"))


# ============================================================
# FACULTY MANAGEMENT
# ============================================================
@admin_bp.route("/faculties")
@login_required
@admin_required
def faculties():
    all_faculties = get_admin_faculty_rows()
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
    dependencies = get_faculty_dependency_counts(faculty_id)
    if dependencies and (dependencies.get("books", 0) or dependencies.get("users", 0)):
        flash(translate("dependency_warning") + f" ({dependencies.get('books', 0)} books, {dependencies.get('users', 0)} users)", "warning")
        return redirect(url_for("admin.faculties"))
    delete_faculty(faculty_id)
    flash("Faculty ကို ဖျက်ပြီးပါပြီ။", "success")
    return redirect(url_for("admin.faculties"))


# ============================================================
# DEPARTMENT MANAGEMENT
# ============================================================
@admin_bp.route("/departments")
@login_required
@admin_required
def departments():
    rows = []
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT f.faculty_id, f.faculty_name, f.department, "
        "(SELECT COALESCE(SUM(total_copies),0) FROM books WHERE books.faculty_id = f.faculty_id AND is_archived = 0) AS book_count, "
        "(SELECT COUNT(*) FROM categories WHERE categories.faculty_id = f.faculty_id) AS category_count "
        "FROM faculties f ORDER BY f.faculty_name ASC, f.department ASC"
    )
    for r in cur.fetchall():
        rows.append(dict(r))
    cur.close()
    return render_template("admin/departments.html", dept_rows=rows)


@admin_bp.route("/departments/add", methods=["POST"])
@login_required
@admin_required
def department_add():
    faculty_name = request.form.get("faculty_name", "").strip()
    department = request.form.get("department", "").strip()
    if department:
        # Find existing faculty row with matching faculty name; fall back to first match.
        cur = mysql.connection.cursor()
        cur.execute("SELECT faculty_id FROM faculties WHERE LOWER(faculty_name) = LOWER(%s) LIMIT 1", (faculty_name,))
        existing = cur.fetchone()
        cur.close()
        if existing:
            update_faculty(existing["faculty_id"], faculty_name, department)
        else:
            add_faculty(faculty_name, department)
        flash("Department ထည့်ပြီးပါပြီ။", "success")
    return redirect(url_for("admin.departments"))


@admin_bp.route("/departments/edit/<int:dept_id>", methods=["POST"])
@login_required
@admin_required
def department_edit(dept_id):
    faculty_name = request.form.get("faculty_name", "").strip()
    department = request.form.get("department", "").strip()
    update_faculty(dept_id, faculty_name, department)
    flash("Department ကို Update လုပ်ပြီးပါပြီ။", "success")
    return redirect(url_for("admin.departments"))


@admin_bp.route("/departments/delete/<int:dept_id>", methods=["POST"])
@login_required
@admin_required
def department_delete(dept_id):
    dependencies = get_faculty_dependency_counts(dept_id)
    if dependencies and (dependencies.get("books", 0) or dependencies.get("users", 0) or dependencies.get("categories", 0)):
        flash(translate("dependency_warning") + f" ({dependencies.get('books', 0)} books, {dependencies.get('users', 0)} users, {dependencies.get('categories', 0)} categories)", "warning")
        return redirect(url_for("admin.departments"))
    delete_faculty(dept_id)
    flash("Department ကို ဖျက်ပြီးပါပြီ။", "success")
    return redirect(url_for("admin.departments"))


# ============================================================
# BORROW MANAGEMENT
# ============================================================
@admin_bp.route("/borrows")
@login_required
@admin_required
def borrows():
    # Mark overdue records automatically on page load using the existing job logic.
    mark_overdue_records()
    status_filter = request.args.get("status") or None
    search_query = request.args.get("search", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        faculty_id = int(request.args["faculty_id"]) if request.args.get("faculty_id") else None
    except ValueError:
        faculty_id = None
    try:
        category_id = int(request.args["category_id"]) if request.args.get("category_id") else None
    except ValueError:
        category_id = None
    try:
        start_date = date.fromisoformat(request.args["from"]) if request.args.get("from") else None
    except ValueError:
        start_date = None
    try:
        end_date = date.fromisoformat(request.args["to"]) if request.args.get("to") else None
    except ValueError:
        end_date = None
    request_page = get_all_borrow_requests(
        status=status_filter,
        search=search_query or None,
        start_date=start_date,
        end_date=end_date,
        faculty_id=faculty_id,
        category_id=category_id,
        page=page,
        per_page=25,
    )
    stats = get_borrow_stats()
    fine_total = get_fine_total()
    query_args = request.args.to_dict(flat=True)
    query_args["page"] = max(1, request_page["page"] - 1)
    pagination_prev_url = url_for("admin.borrows", **query_args)
    query_args["page"] = min(request_page["pages"], request_page["page"] + 1)
    pagination_next_url = url_for("admin.borrows", **query_args)
    borrow_status_urls = {}
    for tab_key, tab_status in [("all", None), ("pending", "pending"), ("approved", "approved"), ("borrowed", "borrowed"), ("overdue", "overdue"), ("returned", "returned"), ("rejected", "rejected")]:
        tab_args = request.args.to_dict(flat=True)
        tab_args.pop("page", None)
        if tab_status:
            tab_args["status"] = tab_status
        else:
            tab_args.pop("status", None)
        borrow_status_urls[tab_key] = url_for("admin.borrows", **tab_args)
    return render_template(
        "admin/borrows.html",
        requests=request_page["records"],
        request_page=request_page,
        stats=stats,
        fine_total=fine_total,
        status_filter=status_filter,
        search=search_query,
        start_date=start_date.isoformat() if start_date else "",
        end_date=end_date.isoformat() if end_date else "",
        faculty_id=faculty_id,
        category_id=category_id,
        faculties=get_all_faculties(),
        categories=get_all_categories(),
        pagination_prev_url=pagination_prev_url,
        pagination_next_url=pagination_next_url,
        borrow_status_urls=borrow_status_urls,
        today=date.today().strftime("%Y-%m-%d"),
        today_date=date.today(),
    )


@admin_bp.route("/borrows/approve/<int:borrow_id>", methods=["POST"])
@login_required
@admin_required
def borrow_approve(borrow_id):
    try:
        qr_folder = current_app.config["UPLOAD_FOLDER_QRCODES"]
        borrow_id_code = approve_borrow(borrow_id, qr_folder, request.host_url.rstrip('/'))
        br = get_borrow_by_id(borrow_id)
        if br:
            notify_borrow_approved(br["user_id"], br["student_name"], br["book_title"], borrow_id_code, br["borrow_id"])
        flash(f"Borrow Request ကို Approve လုပ်ပြီးပါပြီ။ ID: {borrow_id_code}", "success")
    except Exception:
        current_app.logger.exception("Admin borrow approval failed", extra={"borrow_id": borrow_id})
        mysql.connection.rollback()
        flash(translate("operation_failed"), "danger")
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
        notify_borrow_issued(br["user_id"], br["student_name"], br["book_title"], br["borrow_id_code"], borrowed_date, due_date, br["borrow_id"])
        flash("စာအုပ် ထုတ်ပေးမှု (Issue) အောင်မြင်ပါသည်။", "success")
    except Exception:
        current_app.logger.exception("Admin borrow issue failed", extra={"borrow_id": borrow_id})
        mysql.connection.rollback()
        flash(translate("operation_failed"), "danger")
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
    if request.form.get("confirm_return") != "1":
        flash("Return confirmation မပြည့်စုံပါ။ စာအုပ်ကို မပြန်အပ်ရသေးပါ။", "danger")
        return redirect(url_for("admin.borrows"))

    current = get_borrow_by_id(borrow_id)
    if not current:
        flash("Borrow record မတွေ့ပါ။", "danger")
        return redirect(url_for("admin.borrows"))
    if current.get("status") not in ("borrowed", "overdue"):
        flash(f"လက်ရှိ status ({current.get('status')}) ဖြင့် Return လုပ်၍မရပါ။", "danger")
        return redirect(url_for("admin.borrows"))

    # Re-check the live estimated/fine state immediately before the transaction.
    preview_late_days, preview_fine = calculate_fine(borrow_id)
    try:
        result = return_book(borrow_id)
    except Exception:
        current_app.logger.exception("Admin borrow return failed", extra={"borrow_id": borrow_id})
        mysql.connection.rollback()
        flash(translate("operation_failed"), "danger")
        return redirect(url_for("admin.borrows"))

    if result["fine_amount"] > 0:
        flash(
            f"Book ပြန်အပ်ပြီး — Late {result['late_days']} days, "
            f"Final Fine: {result['fine_amount']:,.0f} MMK ထည့်ထားပါသည်။",
            "warning",
        )
    else:
        flash("Book ပြန်အပ်မှု၊ stock restoration နှင့် notification ကို transaction တစ်ခုအတွင်း မှတ်တမ်းတင်ပြီးပါပြီ။", "success")
    return redirect(url_for("admin.borrows"))


# ============================================================
# FINE MANAGEMENT
# ============================================================
@admin_bp.route("/fines")
@login_required
@admin_required
def fines():
    status_filter = request.args.get("status") or None
    search_filter = request.args.get("search", "").strip()
    year_options = get_fine_report_years()
    try:
        selected_year = int(request.args.get("year") or year_options[0])
    except (TypeError, ValueError):
        selected_year = year_options[0]
    if selected_year not in year_options:
        selected_year = year_options[0]
    try:
        faculty_id = int(request.args["faculty_id"]) if request.args.get("faculty_id") else None
    except ValueError:
        faculty_id = None
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        start_date = date.fromisoformat(request.args["from"]) if request.args.get("from") else None
    except ValueError:
        start_date = None
    try:
        end_date = date.fromisoformat(request.args["to"]) if request.args.get("to") else None
    except ValueError:
        end_date = None
    fine_page = get_all_fines(
        status=status_filter,
        search=search_filter or None,
        start_date=start_date,
        end_date=end_date,
        faculty_id=faculty_id,
        page=page,
        per_page=25,
    )
    fine_summary = get_fine_summary()
    monthly_fines = get_monthly_fine_report(selected_year)
    query_args = request.args.to_dict(flat=True)
    query_args["page"] = max(1, fine_page["page"] - 1)
    pagination_prev_url = url_for("admin.fines", **query_args)
    query_args["page"] = min(fine_page["pages"], fine_page["page"] + 1)
    pagination_next_url = url_for("admin.fines", **query_args)
    fine_status_urls = {}
    for tab_key, tab_status in [("all", None), ("unpaid", "unpaid"), ("paid", "paid")]:
        tab_args = request.args.to_dict(flat=True)
        tab_args.pop("page", None)
        if tab_status:
            tab_args["status"] = tab_status
        else:
            tab_args.pop("status", None)
        fine_status_urls[tab_key] = url_for("admin.fines", **tab_args)
    return render_template(
        "admin/fines.html",
        fines=fine_page["records"],
        fine_page=fine_page,
        status_filter=status_filter,
        search_filter=search_filter,
        start_date=start_date.isoformat() if start_date else "",
        end_date=end_date.isoformat() if end_date else "",
        faculty_id=faculty_id,
        faculties=get_all_faculties(),
        pagination_prev_url=pagination_prev_url,
        pagination_next_url=pagination_next_url,
        fine_status_urls=fine_status_urls,
        fine_summary=fine_summary,
        monthly_fines=monthly_fines,
        year_options=year_options,
        selected_year=selected_year,
    )


@admin_bp.route("/fines/paid/<int:fine_id>", methods=["POST"])
@login_required
@admin_required
def fine_paid(fine_id):
    try:
        result = mark_fine_paid(fine_id, "Cash")  # Phase 6: cash-only for new markings; historic values preserved
        if result.get("already_paid"):
            flash("ဒီ Fine ကို အရင်ကပင် Paid အဖြစ် မှတ်တမ်းတင်ထားပြီးပါပြီ။", "info")
        else:
            flash("Fine ကို ပေးချေပြီးကြောင်း payment method နှင့်အတူ မှတ်တမ်းတင်ပြီးပါပြီ။", "success")
    except Exception:
        current_app.logger.exception("Admin fine payment failed", extra={"fine_id": fine_id})
        mysql.connection.rollback()
        flash(translate("payment_failed"), "danger")
    return redirect(url_for("admin.fines"))


# ============================================================
# REPORTS
# ============================================================
@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    today = date.today()
    report_type = request.args.get("report", "borrowing")
    try:
        start_date = date.fromisoformat(request.args.get("from") or (today - timedelta(days=364)).isoformat())
    except ValueError:
        start_date = today - timedelta(days=364)
    try:
        end_date = date.fromisoformat(request.args.get("to") or today.isoformat())
    except ValueError:
        end_date = today
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        faculty_id = int(request.args["faculty_id"]) if request.args.get("faculty_id") else None
    except ValueError:
        faculty_id = None
    try:
        category_id = int(request.args["category_id"]) if request.args.get("category_id") else None
    except ValueError:
        category_id = None
    report = get_admin_report(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        status=request.args.get("status") or None,
        search=request.args.get("search") or None,
        faculty_id=faculty_id,
        category_id=category_id,
        page=page,
        per_page=25,
    )
    query_args = request.args.to_dict(flat=True)
    query_args["report"] = report_type if report_type in {"borrowing", "overdue", "fines", "book_usage"} else "borrowing"
    query_args["page"] = max(1, report["page"] - 1)
    pagination_prev_url = url_for("admin.reports", **query_args)
    query_args["page"] = min(report["pages"], report["page"] + 1)
    pagination_next_url = url_for("admin.reports", **query_args)
    return render_template(
        "admin/reports.html",
        report=report,
        report_type=report_type if report_type in {"borrowing", "overdue", "fines", "book_usage"} else "borrowing",
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        status=request.args.get("status", ""),
        search=request.args.get("search", ""),
        faculty_id=faculty_id,
        category_id=category_id,
        faculties=get_all_faculties(),
        categories=get_all_categories(),
        pagination_prev_url=pagination_prev_url,
        pagination_next_url=pagination_next_url,
    )


# ============================================================
# CHARTS
# ============================================================
@admin_bp.route("/charts")
@login_required
@admin_required
def charts():
    mark_overdue_records()
    today = date.today()
    def month_start_offset(months):
        month_index = today.year * 12 + today.month - 1 - months
        return date(month_index // 12, month_index % 12 + 1, 1)

    presets = {
        "7d": (today - timedelta(days=6), today, "day", "Last 7 days"),
        "30d": (today - timedelta(days=29), today, "day", "Last 30 days"),
        "3m": (month_start_offset(2), today, "month", "Last 3 months"),
        "6m": (month_start_offset(5), today, "month", "Last 6 months"),
        "1y": (month_start_offset(11), today, "month", "Last 1 year"),
    }
    period = request.args.get("period", "1y")
    if period in {"1", "3", "12"}:
        period = {"1": "30d", "3": "3m", "12": "1y"}[period]
    if period not in presets:
        period = "1y"
    start_date, end_date, granularity, period_label = presets[period]
    stats = get_dashboard_stats()
    borrow_stats = get_borrow_stats()
    fine_summary = get_fine_summary()
    return render_template(
        "admin/charts.html",
        stats=stats,
        borrow_stats=borrow_stats,
        most_borrowed=get_most_borrowed_books(10),
        borrow_trend=get_borrowing_trend(start_date, end_date, granularity),
        faculty_counts=get_borrow_by_faculty(start_date, end_date),
        category_counts=get_borrow_by_category(start_date, end_date),
        status_stats=get_borrow_status_stats(),
        fine_summary=fine_summary,
        fine_trend=get_fine_trend(start_date, end_date, granularity),
        downloads_trend=get_monthly_downloads(12),
        period=period,
        period_label=period_label,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )


# ============================================================
# ANNOUNCEMENTS
# ============================================================
@admin_bp.route("/announcements")
@login_required
@admin_required
def announcements():
    search = request.args.get("search", "").strip()
    all_ann = get_all_announcements(search=search or None)
    # Phase 4 (display-only): audience = registered students + teachers
    audience = sum(r["cnt"] or 0 for r in get_user_role_stats() if r.get("role") in ("student", "teacher"))
    return render_template("admin/announcements.html", announcements=all_ann, search=search, audience=audience)


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


# ============================================================
# UNIVERSITY RECORDS (Phase 5 — official records admin)
# Records sit inside the Users sidebar section: they are the
# official university identity source, separate from user
# accounts (users are created by self-registration against a
# record; admins manage records, not accounts).
# ============================================================

ERROR_KEY_TO_FLASH = {
    "missing_fields": "ur_error_missing_fields",
    "missing_student_id": "ur_error_missing_student_id",
    "invalid_email": "ur_error_invalid_email",
    "invalid_role": "ur_error_invalid_role",
    "invalid_faculty": "ur_error_invalid_faculty",
    "duplicate_email": "ur_error_duplicate_email",
    "duplicate_id": "ur_error_duplicate_id",
    "not_found": "ur_error_not_found",
}


def _ur_status_choices():
    """Display-ordered 4-state status choices (admin form/filter)."""
    return [
        ("active", translate("ur_active")),
        ("inactive", translate("ur_inactive")),
        ("graduated", translate("ur_graduated")),
        ("suspended", translate("ur_suspended")),
    ]


@admin_bp.route("/university-records")
@login_required
@admin_required
def university_records():
    search = (request.args.get("search") or "").strip()
    role_filter = (request.args.get("role") or "").strip() or None
    faculty_filter = (request.args.get("faculty_id") or "").strip() or None
    status_filter = (request.args.get("status") or "").strip() or None
    page = request.args.get("page", "1")
    records_page = get_records(
        search=search or None,
        role=role_filter,
        faculty_id=faculty_filter,
        status=status_filter or None,
        page=page,
        per_page=25,
    )
    common = dict(
        records_page=records_page,
        search=search,
        role_filter=role_filter or "",
        faculty_filter=faculty_filter or "",
        status_filter=status_filter or "",
        faculties=get_all_faculties(),
        status_choices=_ur_status_choices(),
        user_summary=get_admin_user_summary(),
        **get_record_counts(),
    )
    if records_page["page"] > 1:
        common["pagination_prev_url"] = url_for(
            "admin.university_records", search=search, role=role_filter,
            faculty_id=faculty_filter, status=status_filter,
            page=records_page["page"] - 1,
        )
    if records_page["page"] < records_page["pages"]:
        common["pagination_next_url"] = url_for(
            "admin.university_records", search=search, role=role_filter,
            faculty_id=faculty_filter, status=status_filter,
            page=records_page["page"] + 1,
        )
    return render_template("admin/university_records.html", **common)


@admin_bp.route("/university-records/add", methods=["GET", "POST"])
@login_required
@admin_required
def university_record_add():
    faculties = get_all_faculties()
    if request.method == "POST":
        university_email = request.form.get("university_email", "").strip()
        university_id = request.form.get("university_id", "").strip() or None
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "").strip()
        faculty_id = request.form.get("faculty_id") or None
        department = request.form.get("department", "").strip() or None
        year = request.form.get("year", "").strip() or None
        status = request.form.get("status", "active").strip()
        if not all([university_email, full_name]):
            flash(translate("ur_error_missing_fields"), "danger")
            return redirect(url_for("admin.university_record_add"))
        record_id, error_key = create_record(
            university_email, university_id, full_name, role,
            faculty_id=faculty_id, department=department, year=year,
            is_active=1, status=status,
        )
        if error_key:
            flash(translate(ERROR_KEY_TO_FLASH.get(error_key, error_key)), "danger")
            return render_template(
                "admin/record_form.html", record=None, faculties=faculties,
                status_choices=_ur_status_choices(),
            )
        flash(translate("ur_add_success"), "success")
        return redirect(url_for("admin.university_records"))
    return render_template(
        "admin/record_form.html", record=None, faculties=faculties,
        status_choices=_ur_status_choices(),
    )


@admin_bp.route("/university-records/edit/<int:record_id>",
                methods=["GET", "POST"])
@login_required
@admin_required
def university_record_edit(record_id):
    record = get_record_by_id(record_id)
    faculties = get_all_faculties()
    if record is None:
        flash(translate("ur_error_not_found"), "danger")
        return redirect(url_for("admin.university_records"))
    if request.method == "POST":
        lock_identity = bool(record.get("registered"))
        university_id = request.form.get("university_id", "").strip() or None
        department = request.form.get("department", "").strip() or None
        year = request.form.get("year", "").strip() or None
        status = request.form.get("status", record.get("status")).strip()
        rows, error_key = update_record(
            record_id,
            university_email=record["university_email"],
            university_id=university_id,
            full_name=record["full_name"],
            role=record["role"],
            faculty_id=record.get("faculty_id"),
            department=department,
            year=year,
            is_active=record.get("is_active"),
            lock_identity=lock_identity,
            status=status,
        )
        if error_key:
            flash(translate(ERROR_KEY_TO_FLASH.get(error_key, error_key)), "danger")
            return render_template(
                "admin/record_form.html", record=record, faculties=faculties,
                status_choices=_ur_status_choices(),
            )
        flash(translate("ur_update_success"), "success")
        return redirect(url_for("admin.university_records"))
    return render_template(
        "admin/record_form.html", record=record, faculties=faculties,
        status_choices=_ur_status_choices(),
    )


@admin_bp.route("/university-records/delete/<int:record_id>", methods=["POST"])
@login_required
@admin_required
def university_record_delete(record_id):
    """Delete an official record only when no user account is registered.

    The model performs the authoritative safety check as well, so a forged
    request cannot delete a record that already produced a user account.
    """
    try:
        safety = delete_record_safe(record_id)
    except Exception:
        current_app.logger.exception(
            "Admin university record deletion failed",
            extra={"record_id": record_id},
        )
        mysql.connection.rollback()
        flash(translate("operation_failed"), "danger")
        return redirect(url_for("admin.university_records"))

    if not safety["exists"]:
        flash(translate("ur_error_not_found"), "danger")
    elif not safety["deletable"]:
        # Registered records are permanently protected by the model guard.
        flash(translate("ur_error_delete_registered"), "danger")
    else:
        flash(translate("ur_delete_success"), "success")
    return redirect(url_for("admin.university_records"))
