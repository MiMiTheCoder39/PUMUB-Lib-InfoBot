"""
utils/identity_check.py
-----------------------
Authoritative registration identity verification (Phase H + Phase J).

Phase H  — exact match against the official `university_records` table
           (email + university ID).

Phase J  — EMAIL-ONLY matching: teachers carry no university ID, so the
           submitted official email alone must exactly match an active
           record. The matched record's official fields (full_name,
           role, faculty_id, department, year, university_id) are
           returned to the route, which LOCKS them into the session.
           The applicant never selects or submits any identity field.

The lookup strategy is swappable: swapping `verify_identity` to
another source (e.g. an external university API) requires no route
changes — only this module is replaced.
"""

from utils.i18n import translate
from models.university_records import get_record_by_email


def verify_identity(email: str):
    """Exact case-insensitive match of the submitted email against
    `university_records` (Phase J — email-only).

    Returns a dict:
        valid        bool — the record matched and is eligible
        errors       list[str] — translated flash messages when valid
                     is False (empty when valid)
        official_name / role / faculty_id / department / year /
        university_id — the official record fields (None when not
                     matched); the route locks these into the session

    This function is the ONLY place the record source is consulted,
    so registration cannot be verified around by any other path.
    """
    result = {
        "valid": False,
        "errors": [],
        "official_name": None,
        "role": None,
        "faculty_id": None,
        "department": None,
        "year": None,
        "university_id": None,
        "status": None,
    }

    email = (email or "").strip()
    if not email:
        result["errors"].append(translate("verify_email_required"))
        return result

    record = get_record_by_email(email)

    # --- No record, or email mismatch --------------------------
    if record is None:
        # NOTE: the message is generic on purpose — it never reveals
        # whether the email or the (absent) ID was the problem.
        result["errors"].append(translate("verify_no_record"))
        return result

    # --- Four-state status check (status ENUM) ---
    # Checked BEFORE the legacy is_active flag so that a record with
    # status suspended/graduated reports its actual state, while rows
    # created before the status column fall back to is_active only.
    status = (record.get("status") or "").strip().lower()
    if status in ("suspended", "graduated"):
        result["errors"].append(translate(
            "verify_record_suspended" if status == "suspended"
            else "verify_record_graduated"))
        return result

    # --- Active-status fallback (existing is_active only) ---------
    if not int(record["is_active"]):
        result["errors"].append(translate("verify_record_inactive"))
        return result

    # --- Duplicate account gate (email basis) ------------------
    from models.university_records import count_users_registered_from_email
    if count_users_registered_from_email(record["university_email"]):
        result["errors"].append(translate("verify_duplicate_email"))
        return result

    # --- Verified: lock the official record into the result ------
    result["valid"] = True
    result["status"] = record["status"]
    result["official_name"] = record["full_name"]
    result["role"] = record["role"]                       # auto-assigned
    result["faculty_id"] = record["faculty_id"]           # FK (may be None)
    result["department"] = record["department"]           # may be None
    result["year"] = record["year"]                       # may be None
    result["university_id"] = record["university_id"]     # NULL for teachers
    return result
