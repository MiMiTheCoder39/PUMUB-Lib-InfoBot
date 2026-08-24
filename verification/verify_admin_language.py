from app import create_app
from flask import render_template, session

app = create_app()
app.config.update(TESTING=True, SECRET_KEY="language-test")

for language, expected in (("en", "Borrowing Trend"), ("my", "Borrowing Trend")):
    with app.test_request_context("/admin/charts"):
        session.update(user_id=1, role="admin", name="Admin", language=language)
        html = render_template(
            "admin/charts.html",
            stats={"total_books":1,"total_students":1,"active_borrows":1},
            borrow_stats={"overdue":0},
            most_borrowed=[], borrow_trend=[], faculty_counts=[], category_counts=[],
            status_stats=[], fine_summary={"all_time_total":0,"unpaid_total":0,"paid_total":0},
            fine_trend=[], period="1y", period_label="Last 1 year", start_date="2026-01-01", end_date="2026-08-15",
        )
        assert expected in html
        assert "admin-language-links" in html

print("Admin language render checks passed")
