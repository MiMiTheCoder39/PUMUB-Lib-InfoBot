"""Regression tests for the admin university-record delete endpoint.

These tests stub the database-backed safety helper and verify the HTTP flow,
so they can run without a live MySQL database.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import app as app_module
from routes import admin_routes


application = app_module.create_app()
application.config.update(TESTING=True, SECRET_KEY="route-test-secret")


def _login_as_admin(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "admin"
        session["name"] = "Test Admin"


def test_delete_route_is_registered_and_post_only():
    rule = next(
        rule for rule in application.url_map.iter_rules()
        if rule.endpoint == "admin.university_record_delete"
    )
    assert str(rule) == "/admin/university-records/delete/<int:record_id>"
    assert "POST" in rule.methods
    assert "GET" not in rule.methods


def test_unregistered_record_is_deleted(monkeypatch):
    calls = []

    def fake_delete(record_id):
        calls.append(record_id)
        return {"exists": True, "registered": False, "deletable": True, "reason": "none"}

    monkeypatch.setattr(admin_routes, "delete_record_safe", fake_delete)
    with application.test_client() as client:
        _login_as_admin(client)
        response = client.post("/admin/university-records/delete/3")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/university-records")
    assert calls == [3]


def test_registered_record_is_blocked(monkeypatch):
    def fake_delete(record_id):
        return {
            "exists": True,
            "registered": True,
            "deletable": False,
            "reason": "registered_record_blocked",
        }

    monkeypatch.setattr(admin_routes, "delete_record_safe", fake_delete)
    with application.test_client() as client:
        _login_as_admin(client)
        response = client.post("/admin/university-records/delete/4")
        with client.session_transaction() as session:
            flashed = session.get("_flashes", [])

    assert response.status_code == 302
    assert any("registered" in str(message).lower() or "register" in str(message).lower()
               for _, message in flashed)


def test_missing_record_is_reported(monkeypatch):
    def fake_delete(record_id):
        return {"exists": False, "registered": False, "deletable": False, "reason": "record_not_found"}

    monkeypatch.setattr(admin_routes, "delete_record_safe", fake_delete)
    with application.test_client() as client:
        _login_as_admin(client)
        response = client.post("/admin/university-records/delete/999")
        with client.session_transaction() as session:
            flashed = session.get("_flashes", [])

    assert response.status_code == 302
    assert any("မရှိ" in str(message) or "not found" in str(message).lower()
               for _, message in flashed)


def test_template_points_to_delete_endpoint():
    template = (PROJECT_ROOT / "templates/admin/university_records.html").read_text(encoding="utf-8")
    assert "`/admin/university-records/delete/${id}`" in template
    assert "if not r.registered" in template


if __name__ == "__main__":
    tests = [
        test_delete_route_is_registered_and_post_only,
        test_unregistered_record_is_deleted,
        test_registered_record_is_blocked,
        test_missing_record_is_reported,
        test_template_points_to_delete_endpoint,
    ]
    for test in tests:
        test(type("MonkeyPatch", (), {"setattr": lambda self, obj, name, value: setattr(obj, name, value)})()) if "monkeypatch" in test.__code__.co_varnames else test()
    print("UNIVERSITY_RECORD_DELETE_ROUTE_TESTS: PASS")
