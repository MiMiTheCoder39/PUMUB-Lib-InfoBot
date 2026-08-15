# Borrow/Fine hardening deployment notes

This change set keeps the existing web service command:

```text
web: gunicorn app:app
```

## 1. Database migration

Before deploying the new application code, back up the Railway MySQL database. Run `migrations/001_borrow_fine_hardening.sql` through DBeaver against the Railway database. The migration is non-destructive: it does not drop tables or delete rows. It first prints duplicate fine rows; the `fines.borrow_id` unique key must not be added until that preflight result is empty.

The migration adds `fines.payment_method`, adds a unique `fines.borrow_id` guard, adds nullable `notifications.borrow_id` plus an index, and expands the notification type enum to match the existing borrow/fine notification code.

## 2. Web deployment

Deploy the application source after the migration succeeds. The web service continues to start with `gunicorn app:app`. Railway environment variables remain the source of truth for the Flask secret and MySQL connection values; do not commit `.env`.

## 3. Overdue/reminder execution

The source includes a short-lived entrypoint:

```text
python jobs/overdue_job.py
```

Create a separate Railway service from the same repository, set its start command to that command, and configure the service's Cron Schedule in Railway Settings. Railway cron schedules use UTC and must run a short-lived process that exits after the task; the minimum interval is five minutes. A daily schedule is sufficient for the library policy. The existing web service must not be changed to the cron command.

The job performs, in order: mark borrowed records past due as overdue, send one due-soon reminder per borrow per day, and send one overdue reminder per borrow per day. The web routes also retain a safe page-load refresh as a fallback, but the cron service is the production mechanism.

## 4. Verification after deployment

Check the web service logs for a successful Gunicorn startup, then run the cron service once manually. Verify that the job exits successfully and that the Railway database shows the new columns/indexes. Test one approved issue, one on-time return, one late return, one repeated return, one fine payment, and one repeated payment before allowing general use.

Official Railway references: [Cron Jobs](https://docs.railway.com/cron-jobs) and [Flask deployment](https://docs.railway.com/guides/flask).
