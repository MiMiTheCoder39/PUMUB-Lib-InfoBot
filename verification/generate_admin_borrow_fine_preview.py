from datetime import date, datetime
from pathlib import Path
from app import create_app
from flask import render_template, session

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "admin_preview"
OUT.mkdir(exist_ok=True)
app = create_app()
app.config.update(TESTING=True, SECRET_KEY="preview-test")

row = {
    "borrow_id": 1, "borrow_id_code": "BR-2026-0001", "student_name": "Preview Student", "student_id": "ST-001",
    "faculty_name": "Faculty of Computing", "department": "Information Technology", "book_title": "Digital Library Operations",
    "author_name": "Preview Author", "category_name": "Library Science", "available_copies": 4,
    "request_date": datetime(2026, 8, 10), "issued_date": datetime(2026, 8, 11), "borrowed_date": datetime(2026, 8, 11),
    "due_date": date(2026, 8, 13), "return_date": None, "status": "overdue", "late_days": 2,
    "estimated_fine": 2000, "fine_amount": 0, "fine_paid": 0, "fine_id": None, "active_borrow_count": 1,
}

with app.test_request_context("/admin/borrows"):
    session.update(user_id=1, role="admin", name="Preview Admin", language="en")
    html = render_template(
        "admin/borrows.html", requests=[row], request_page={"total": 1, "page": 1, "pages": 1, "per_page": 25},
        stats={"pending": 3, "approved": 2, "borrowed": 8, "overdue": 1, "returned": 17, "rejected": 0}, fine_total=2000,
        status_filter="overdue", search="", start_date="", end_date="", faculty_id=None, category_id=None,
        faculties=[], categories=[], borrow_status_urls={key: "/admin/borrows" for key in ("all", "pending", "approved", "borrowed", "overdue", "returned", "rejected")},
        pagination_prev_url="/admin/borrows", pagination_next_url="/admin/borrows", today=date.today().isoformat(), today_date=date.today(),
    )
    (OUT / "borrows.html").write_text(html, encoding="utf-8")

fine = {
    "fine_id": 1, "student_name": "Preview Student", "student_id": "ST-001", "book_title": "Digital Library Operations",
    "author_name": "Preview Author", "category_name": "Library Science", "borrow_id": 1, "borrow_id_code": "BR-2026-0001",
    "borrow_status": "overdue", "amount": 2000, "reason": "Late Return", "is_paid": 0, "created_at": datetime(2026, 8, 14),
    "paid_at": None, "payment_method": None, "due_date": date(2026, 8, 13), "return_date": None,
    "issued_date": datetime(2026, 8, 11), "borrowed_date": datetime(2026, 8, 11), "late_days": 2,
}

with app.test_request_context("/admin/fines"):
    session.update(user_id=1, role="admin", name="Preview Admin", language="en")
    html = render_template(
        "admin/fines.html", fines=[fine], fine_page={"total": 1, "page": 1, "pages": 1, "per_page": 25},
        status_filter="unpaid", search_filter="", start_date="", end_date="", faculty_id=None, faculties=[],
        fine_status_urls={"all": "/admin/fines", "unpaid": "/admin/fines?status=unpaid", "paid": "/admin/fines?status=paid"},
        pagination_prev_url="/admin/fines", pagination_next_url="/admin/fines",
        fine_summary={"all_time_total": 2000, "unpaid_total": 2000, "paid_total": 0},
        monthly_fines=[{"month": "August", "generated": 2000, "paid": 0, "outstanding": 2000}], year_options=[2026], selected_year=2026,
    )
    (OUT / "fines.html").write_text(html, encoding="utf-8")

print(f"Wrote {OUT / 'borrows.html'} and {OUT / 'fines.html'}")
