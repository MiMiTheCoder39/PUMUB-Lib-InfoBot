"""Regression tests for user profile username/avatar editing.

The database-backed helpers are stubbed so the test can run without a live DB.
"""

from io import BytesIO
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import app as app_module
from routes import student_routes
from utils import decorators


application = app_module.create_app()
application.config.update(TESTING=True, SECRET_KEY="profile-test-secret")

BASE_USER = {
    "user_id": 7,
    "name": "Test Student",
    "email": "student@example.com",
    "username": "old_user",
    "role": "student",
    "faculty_id": None,
    "profile_image": None,
}


def _login_as_student(client):
    with client.session_transaction() as session:
        session["user_id"] = BASE_USER["user_id"]
        session["role"] = "student"
        session["name"] = BASE_USER["name"]
        session["username"] = BASE_USER["username"]


def _patch(mapping):
    originals = []
    for obj, name, replacement in mapping:
        originals.append((obj, name, getattr(obj, name)))
        setattr(obj, name, replacement)
    return originals


def _restore(originals):
    for obj, name, original in originals:
        setattr(obj, name, original)


def test_username_and_avatar_update_refresh_session():
    calls = []
    saved_user = dict(BASE_USER)

    def fake_get_user(user_id):
        return dict(saved_user)

    def fake_get_username(username):
        return None

    def fake_save(file_storage, folder, allowed):
        calls.append((file_storage.filename, folder, allowed))
        return "new-avatar.png"

    def fake_update(user_id, name, email, faculty_id, profile_image=None, username=None):
        calls.append(("update", user_id, username, profile_image))

    originals = _patch([
        (decorators, "get_user_by_id", fake_get_user),
        (decorators, "get_record_by_email", lambda email: {"status": "active"}),
        (student_routes, "get_user_by_id", fake_get_user),
        (student_routes, "get_all_faculties", lambda: []),
        (student_routes, "get_user_by_username", fake_get_username),
        (student_routes, "save_uploaded_file", fake_save),
        (student_routes, "update_profile", fake_update),
    ])
    try:
        with application.test_client() as client:
            _login_as_student(client)
            response = client.post(
                "/student/profile",
                data={
                    "username": "new_user",
                    "profile_image": (BytesIO(b"fake-image"), "avatar.png"),
                },
                content_type="multipart/form-data",
            )
            with client.session_transaction() as session:
                assert session["username"] == "new_user"
                assert session["profile_image"] == "new-avatar.png"
    finally:
        _restore(originals)

    assert response.status_code == 302
    assert ("update", 7, "new_user", "new-avatar.png") in calls
    assert calls[0][0] == "avatar.png"


def test_duplicate_username_is_rejected():
    update_calls = []
    originals = _patch([
        (decorators, "get_user_by_id", lambda user_id: dict(BASE_USER)),
        (decorators, "get_record_by_email", lambda email: {"status": "active"}),
        (student_routes, "get_user_by_id", lambda user_id: dict(BASE_USER)),
        (student_routes, "get_all_faculties", lambda: []),
        (student_routes, "get_user_by_username", lambda username: {"user_id": 99}),
        (student_routes, "update_profile", lambda *args, **kwargs: update_calls.append(True)),
    ])
    try:
        with application.test_client() as client:
            _login_as_student(client)
            response = client.post("/student/profile", data={"username": "taken_name"})
    finally:
        _restore(originals)

    assert response.status_code == 302
    assert not update_calls


def test_invalid_username_is_rejected():
    update_calls = []
    originals = _patch([
        (decorators, "get_user_by_id", lambda user_id: dict(BASE_USER)),
        (decorators, "get_record_by_email", lambda email: {"status": "active"}),
        (student_routes, "get_user_by_id", lambda user_id: dict(BASE_USER)),
        (student_routes, "get_all_faculties", lambda: []),
        (student_routes, "update_profile", lambda *args, **kwargs: update_calls.append(True)),
    ])
    try:
        with application.test_client() as client:
            _login_as_student(client)
            response = client.post("/student/profile", data={"username": "bad name!"})
    finally:
        _restore(originals)

    assert response.status_code == 302
    assert not update_calls


def test_template_wires_username_upload_and_nav_avatar():
    profile_template = (PROJECT_ROOT / "templates/user/profile.html").read_text(encoding="utf-8")
    base_template = (PROJECT_ROOT / "templates/base.html").read_text(encoding="utf-8")
    assert 'name="username"' in profile_template
    assert 'name="profile_image"' in profile_template
    assert "profile_image" in base_template
    assert "library_file.file_profile" in base_template


if __name__ == "__main__":
    test_username_and_avatar_update_refresh_session()
    test_duplicate_username_is_rejected()
    test_invalid_username_is_rejected()
    test_template_wires_username_upload_and_nav_avatar()
    print("PROFILE_EDIT_TESTS: PASS")
