"""Phase 5 addition: append get_user_pending_borrow() to models/borrow_model.py.

Read-only helper: returns True if the user has an active (pending/approved/
borrowed/overdue) borrow request for the given book. Used by the Book
Details page to show the "Request sent — awaiting approval" state.
Idempotent: does nothing if the function already exists.
"""
import sys

SRC = "/home/ubuntu/work/source/lib-infobot-phase7-windows-setup/models/borrow_model.py"

FUNC = '''
# ─── Phase 5: Pending-request detection (read-only) ───────────
def get_user_pending_borrow(user_id, book_id):
    """Read-only: True when the user has an active request for this book.

    Active means the request lifecycle has not reached a terminal state
    ('returned' / 'rejected'), matching the active-state sets used
    elsewhere in this module.
    """
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT borrow_id FROM borrow_requests "
            "WHERE user_id=%s AND book_id=%s "
            "AND status IN ('pending','approved','borrowed','overdue') "
            "LIMIT 1",
            (user_id, book_id),
        )
        return cur.fetchone() is not None
    finally:
        cur.close()
'''


def main() -> int:
    with open(SRC, "r", encoding="utf-8") as f:
        content = f.read()
    if "def get_user_pending_borrow" in content:
        print("already present; no change")
        return 0
    with open(SRC, "a", encoding="utf-8") as f:
        f.write(FUNC + "\n")
    print("get_user_pending_borrow appended OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
