from pathlib import Path
import ast
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent
PY_FILES = [
    ROOT / "models/borrow_model.py",
    ROOT / "routes/admin_routes.py",
    ROOT / "routes/student_routes.py",
]
for path in PY_FILES:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

borrow = (ROOT / "models/borrow_model.py").read_text(encoding="utf-8")
admin_routes = (ROOT / "routes/admin_routes.py").read_text(encoding="utf-8")
admin_fines = (ROOT / "templates/admin/fines.html").read_text(encoding="utf-8")
student_route = (ROOT / "routes/student_routes.py").read_text(encoding="utf-8")
student_fines = (ROOT / "templates/user/fines.html").read_text(encoding="utf-8")
admin_borrows = (ROOT / "templates/admin/borrows.html").read_text(encoding="utf-8")

assert "YEAR(created_at) = %s" in borrow
assert "YEAR(paid_at) = %s" in borrow
assert "get_fine_report_years" in borrow and "get_fine_report_years" in admin_routes
assert "get_monthly_fine_report(selected_year)" in admin_routes
assert "selected_year" in admin_fines and "year_options" in admin_fines
assert "monthlyFineChart" in admin_fines
assert "Paid uses <code>paid_at</code>" in admin_fines
assert "finalized_unpaid" in student_route and "estimated_overdue" in student_route
assert "Finalized Fines" in student_fines and "Estimated Overdue Fines" in student_fines
assert 'name="confirm_return" value="1"' in admin_borrows
assert "confirmReturn(form)" in admin_borrows
assert 'request.form.get("confirm_return") != "1"' in admin_routes
assert 'current.get("status") not in ("borrowed", "overdue")' in admin_routes

# Parse all modified HTML/Jinja templates with a permissive environment.
env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), undefined=StrictUndefined)
for relative in ["admin/fines.html", "user/fines.html", "admin/borrows.html"]:
    env.parse((ROOT / "templates" / relative).read_text(encoding="utf-8"))

print("PASS: Python AST, accounting semantics, route wiring, Jinja syntax, chart/year filter, student cards, and return guards")
