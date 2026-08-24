

"""
app.py  -  Digital Library Management System
"""

from flask import Flask, render_template, redirect, url_for, session, current_app
from config import Config
from models.db import mysql
from utils.i18n import current_language, translate, localize_notification_title, localize_notification_message

from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.admin_routes import admin_bp
from routes.ai_routes import ai_bp
from routes.file_routes import file_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mysql.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(file_bp)

    @app.context_processor
    def inject_globals():
        unread_notif_count = 0
        profile_image = session.get("profile_image")
        if "user_id" in session and session.get("role") in ("student", "teacher"):
            try:
                from models.notification_model import get_unread_count
                unread_notif_count = get_unread_count(session["user_id"])
            except Exception:
                unread_notif_count = 0
            # Refresh the avatar from the database so an existing session also
            # sees a profile picture uploaded before the current login.
            try:
                from models.user_model import get_user_by_id
                current_user = get_user_by_id(session["user_id"])
                if current_user is not None:
                    profile_image = current_user.get("profile_image")
                    session["profile_image"] = profile_image
            except Exception:
                pass
        all_faculties = []
        try:
            from models.user_model import get_all_faculties
            all_faculties = get_all_faculties()
        except Exception:
            all_faculties = []
        def _status_label(status):
            """Localized label for the four-state record status."""
            try:
                return translate(
                    {"active": "ur_active", "inactive": "ur_inactive",
                     "graduated": "ur_graduated",
                     "suspended": "ur_suspended"}.get(status, "ur_active"))
            except Exception:
                return status or ""

        def _status_badge_class(status):
            """Soft pill class for the four-state record status (V2)."""
            cls = {
                "active": "admin-status admin-status-active",
                "inactive": "admin-status admin-status-inactive",
                "graduated": "admin-status admin-status-graduated",
                "suspended": "admin-status admin-status-suspended",
            }
            return cls.get(status, "admin-status admin-status-inactive")

        return {
            "unread_notif_count": unread_notif_count,
            "profile_image": profile_image,
            "current_language": current_language(),
            "supported_languages": (("my", "မြန်မာ"), ("en", "English")),
            "all_faculties": all_faculties,
            "t": translate,
            "status_label": _status_label,
            "status_badge_class": _status_badge_class,
            "notification_title": localize_notification_title,
            "notification_message": localize_notification_message,
        }

    @app.route("/")
    def home():
        # Admin -> admin dashboard
        if "user_id" in session and session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))

        # Logged-in student/teacher -> student dashboard
        if "user_id" in session and session.get("role") in ("student", "teacher"):
            return redirect(url_for("student.dashboard"))

        # Guest -> show public home.html with books data
        popular_books = []
        recent_books = []
        faculties = []
        categories = []
        try:
            from models.book_model import get_popular_books, get_all_categories, get_all_books, search_books
            from models.user_model import get_all_faculties
            popular_books = get_popular_books(limit=10)
            recent_books = get_all_books(limit=10)
            faculties = get_all_faculties()
            categories = get_all_categories()
            # Enrich faculties with books (full count + shelf preview)
            for faculty in faculties:
                fid = faculty.get('faculty_id')
                all_books_for_faculty = search_books(faculty_id=fid, primary_only=True)
                faculty['book_count'] = len(all_books_for_faculty)
                faculty['books'] = all_books_for_faculty[:6]
            # Announcements + categories with covers
            from models.report_model import (
                get_all_announcements, get_books_by_category_for_shelf,
                get_active_users, get_most_borrowed_books,
            )
            announcements = get_all_announcements()[:5]
            top_score_users = get_active_users(limit=10)
            most_borrowed_books = get_most_borrowed_books(limit=10)
            if not most_borrowed_books:
                most_borrowed_books = popular_books
            for cat in categories:
                cat['books'] = get_books_by_category_for_shelf(cat.get('category_id'), limit=4)
                cat['book_count'] = 0
        except Exception as exc:
            # Keep the public page renderable even if an optional shelf query fails.
            current_app.logger.exception("Homepage enrichment failed: %s", exc)
            announcements = locals().get("announcements", [])
            top_score_users = locals().get("top_score_users", [])
            most_borrowed_books = locals().get("most_borrowed_books", [])
            categories = locals().get("categories", []) or []
            for cat in categories:
                cat.setdefault("books", [])
                cat.setdefault("book_count", len(cat["books"]))

        return render_template("home.html",
                               popular_books=popular_books,
                               recent_books=recent_books,
                               faculties=faculties,
                               categories=categories,
                               announcements=announcements,
                               top_score_users=top_score_users,
                               most_borrowed_books=most_borrowed_books,
                               supported_languages=(("my", "မြန်မာ"), ("en", "English")),
                               current_language=current_language())

    @app.route("/library-rules")
    def library_rules_public():
        """Public Library Rules page (no login required)."""
        return render_template("user/rules.html")

    @app.route("/test-db")
    def test_db():
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT 1")
            r = cur.fetchone()
            cur.close()
            return f"OK: {r}"
        except Exception as e:
            return f"Error: {e}"

    return app


app = create_app()

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
