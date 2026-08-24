from datetime import date, datetime
from app import create_app
from flask import render_template, session

app = create_app()
app.config.update(TESTING=True, SECRET_KEY="render-test")

with app.test_request_context("/admin/dashboard"):
    session.update(user_id=1, role="admin", name="Render Admin", language="en")
    render_template(
        "admin/dashboard.html",
        stats={"total_books": 5, "total_students": 3, "active_borrows": 2, "overdue": 1, "unpaid_fines": 1000},
        recent_requests=[{"student_name":"Student", "borrow_id_code":"BR-1", "book_title":"Book", "status":"pending", "request_date":datetime.now()}],
        most_borrowed=[{"title":"Book", "author_name":"Author", "borrow_count":2}],
        status_stats=[{"status":"borrowed", "cnt":2}],
        borrow_months=["2026-08"], borrow_data=[2],
    )

with app.test_request_context("/admin/borrows"):
    session.update(user_id=1, role="admin", name="Render Admin", language="en")
    row = {
        "borrow_id":1, "borrow_id_code":"BR-1", "student_name":"Student", "student_id":"S-1", "faculty_name":"Faculty",
        "book_title":"Book", "author_name":"Author", "category_name":"Category", "available_copies":2,
        "request_date":datetime.now(), "issued_date":datetime.now(), "borrowed_date":datetime.now(), "due_date":date.today(), "return_date":None,
        "status":"overdue", "late_days":2, "estimated_fine":2000, "fine_amount":0, "fine_paid":0, "fine_id":None,
        "active_borrow_count":1,
    }
    render_template("admin/borrows.html", requests=[row], request_page={"total":1,"page":1,"pages":1,"per_page":25}, stats={"pending":0,"approved":0,"borrowed":0,"overdue":1,"returned":0,"rejected":0}, fine_total=0, status_filter="overdue", search="", start_date="", end_date="", faculty_id=None, category_id=None, faculties=[], categories=[], borrow_status_urls={"all":"/admin/borrows","pending":"/admin/borrows?status=pending","approved":"/admin/borrows?status=approved","borrowed":"/admin/borrows?status=borrowed","overdue":"/admin/borrows?status=overdue","returned":"/admin/borrows?status=returned","rejected":"/admin/borrows?status=rejected"}, pagination_prev_url="/admin/borrows", pagination_next_url="/admin/borrows", today=date.today().isoformat(), today_date=date.today())

with app.test_request_context("/admin/fines"):
    session.update(user_id=1, role="admin", name="Render Admin", language="en")
    fine = {
        "fine_id":1, "student_name":"Student", "student_id":"S-1", "book_title":"Book", "author_name":"Author", "category_name":"Category",
        "borrow_id":1, "borrow_id_code":"BR-1", "borrow_status":"overdue", "amount":2000, "reason":"Late Return", "is_paid":0,
        "created_at":datetime.now(), "paid_at":None, "payment_method":None, "due_date":date.today(), "return_date":None,
        "issued_date":datetime.now(), "borrowed_date":datetime.now(), "late_days":2,
    }
    render_template("admin/fines.html", fines=[fine], fine_page={"total":1,"page":1,"pages":1,"per_page":25}, status_filter=None, search_filter="", start_date="", end_date="", faculty_id=None, faculties=[], fine_status_urls={"all":"/admin/fines","unpaid":"/admin/fines?status=unpaid","paid":"/admin/fines?status=paid"}, pagination_prev_url="/admin/fines", pagination_next_url="/admin/fines", fine_summary={"all_time_total":2000,"unpaid_total":2000,"paid_total":0,"overdue_total":2000}, monthly_fines=[{"month":"August","generated":2000,"paid":0,"outstanding":2000}], year_options=[2026], selected_year=2026)

with app.test_request_context("/admin/charts"):
    session.update(user_id=1, role="admin", name="Render Admin", language="en")
    render_template("admin/charts.html", stats={"total_books":5,"total_students":3,"active_borrows":2}, borrow_stats={"overdue":1}, most_borrowed=[{"title":"Book","borrow_count":2}], borrow_trend=[{"period":"2026-08","total":2}], faculty_counts=[{"faculty_name":"Faculty","borrow_count":2}], category_counts=[{"category_name":"Category","borrow_count":2}], status_stats=[{"status":"borrowed","cnt":2}], fine_summary={"all_time_total":2000,"unpaid_total":2000,"paid_total":0}, fine_trend=[{"period":"2026-08","generated":2000,"paid":0}], period="1y", period_label="Last 1 year", start_date="2026-08-01", end_date="2026-08-15")

with app.test_request_context("/admin/reports"):
    session.update(user_id=1, role="admin", name="Render Admin", language="en")
    render_template("admin/reports.html", report={"rows":[],"total":0,"page":1,"pages":1}, report_type="borrowing", start_date="2026-01-01", end_date="2026-08-15", status="", search="", faculty_id=None, category_id=None, faculties=[], categories=[], pagination_prev_url="/admin/reports", pagination_next_url="/admin/reports")

print("Admin template render smoke checks passed")
