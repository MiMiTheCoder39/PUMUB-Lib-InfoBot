from app import create_app

app = create_app()
app.config.update(TESTING=True, SECRET_KEY="auth-test")
client = app.test_client()

for path in ("/admin/dashboard", "/admin/borrows", "/admin/fines", "/admin/charts", "/admin/reports"):
    response = client.get(path)
    assert response.status_code in (301, 302), (path, response.status_code)
    assert "/auth/login" in response.headers.get("Location", ""), (path, response.headers.get("Location"))

with client.session_transaction() as sess:
    sess["user_id"] = 99
    sess["role"] = "student"
    sess["name"] = "Student"

for path in ("/admin/dashboard", "/admin/borrows", "/admin/fines", "/admin/charts", "/admin/reports"):
    response = client.get(path)
    assert response.status_code in (301, 302), (path, response.status_code)
    assert "/student/dashboard" in response.headers.get("Location", "") or "/auth" in response.headers.get("Location", ""), (path, response.headers.get("Location"))

for path, data in (
    ("/admin/borrows/approve/1", {}),
    ("/admin/borrows/reject/1", {}),
    ("/admin/fines/paid/1", {"payment_method": "Cash"}),
):
    response = client.post(path, data=data)
    assert response.status_code in (301, 302), (path, response.status_code)
    assert "/student/dashboard" in response.headers.get("Location", "") or "/auth" in response.headers.get("Location", ""), (path, response.headers.get("Location"))

print("Admin authorization guard checks passed")
