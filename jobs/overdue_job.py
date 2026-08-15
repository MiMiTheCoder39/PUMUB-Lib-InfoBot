"""Railway cron entrypoint for deterministic overdue state and notifications."""

from app import app
from models.db import mysql
from models.borrow_model import mark_overdue_records
from models.notification_model import send_due_reminders, send_due_date_reminders


if __name__ == "__main__":
    with app.app_context():
        try:
            changed = mark_overdue_records()
            due_soon = send_due_date_reminders(days_before=3)
            overdue = send_due_reminders()
            print({"overdue_marked": changed, "due_soon_notifications": due_soon, "overdue_notifications": overdue})
        finally:
            try:
                mysql.connection.close()
            except Exception:
                pass
