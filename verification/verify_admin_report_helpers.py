from datetime import date, datetime
from types import SimpleNamespace

from models import report_model


class FakeCursor:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute(self, query, params=()):
        self.calls.append((query, params))

    def fetchone(self):
        response = self.responses.pop(0)
        return response

    def fetchall(self):
        response = self.responses.pop(0)
        return response

    def close(self):
        pass


class FakeConnection:
    def __init__(self, responses):
        self.cursor_obj = FakeCursor(responses)

    def cursor(self):
        return self.cursor_obj


def run_report(report_type, row):
    connection = FakeConnection([{"total": 1}, [row]])
    report_model.mysql = SimpleNamespace(connection=connection)
    result = report_model.get_admin_report(
        report_type=report_type,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 15),
        page=1,
        per_page=25,
    )
    assert result["total"] == 1
    assert result["pages"] == 1
    assert len(result["rows"]) == 1
    assert len(connection.cursor_obj.calls) == 2
    return result["rows"][0]


borrow_row = run_report("borrowing", {
    "due_date": date(2026, 8, 10),
    "return_date": None,
    "status": "overdue",
})
assert borrow_row["late_days"] == 5

fine_row = run_report("fines", {
    "due_date": date(2026, 8, 10),
    "return_date": datetime(2026, 8, 13, 12, 0),
    "is_paid": 0,
})
assert fine_row["late_days"] == 3

usage_row = run_report("book_usage", {
    "book_id": 1,
    "borrow_count": 4,
    "active_count": 1,
})
assert usage_row["borrow_count"] == 4

periods = report_model._iter_periods(date(2026, 8, 1), date(2026, 8, 3), "day")
assert [key for key, _ in periods] == ["2026-08-01", "2026-08-02", "2026-08-03"]
print("Admin report helper contract checks passed")
