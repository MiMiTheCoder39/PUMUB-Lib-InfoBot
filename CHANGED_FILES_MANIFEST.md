# Borrow/Fine changed-files bundle

This bundle contains only the files changed or added for the approved Borrow/Overdue/Fine implementation. It is **not** a replacement for the whole project. Copy each file into the matching path in the existing GitHub project.

## Modified existing files

- `models/borrow_model.py`
- `models/notification_model.py`
- `routes/admin_routes.py`
- `routes/student_routes.py`
- `templates/admin/borrows.html`
- `templates/admin/fines.html`
- `templates/base.html`
- `templates/user/borrow_history.html`
- `templates/user/notifications.html`

## New files

- `templates/user/fines.html`
- `migrations/001_borrow_fine_hardening.sql`
- `jobs/overdue_job.py`
- `jobs/__init__.py`
- `RAILWAY_BORROW_FINE_DEPLOYMENT.md`

## Safe apply order

1. Make a Git branch or commit the current working state before copying anything.
2. Copy the modified existing files to the matching paths; do not delete unrelated files.
3. Add the new files and directories.
4. Back up Railway MySQL and review/run the migration SQL in DBeaver. Confirm the duplicate-fine preflight query returns zero rows before the unique key is added.
5. Deploy the web service with the existing `web: gunicorn app:app` command.
6. Configure a separate Railway cron service with `python jobs/overdue_job.py`; do not replace the web service command.
