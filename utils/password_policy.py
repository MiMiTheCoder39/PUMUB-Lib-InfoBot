"""
utils/password_policy.py
------------------------
Strong password policy (Phase C). Enforced SERVER-SIDE on every
registration request (direct HTTP POSTs that bypass the UI hit the
same rules here) and mirrored client-side by the live checklist UI.

Rule set: 8+ characters, at least one uppercase, at least one
lowercase, at least one digit, at least one special character.
"""


def check_password_policy(password: str) -> dict:
    """Return per-requirement booleans plus the combined verdict."""
    ok_length = len(password) >= 8
    ok_upper = any(ch.isupper() for ch in password)
    ok_lower = any(ch.islower() for ch in password)
    ok_digit = any(ch.isdigit() for ch in password)
    ok_special = any(not ch.isalnum() for ch in password)
    return {
        "all_ok": bool(ok_length and ok_upper and ok_lower
                       and ok_digit and ok_special),
        "ok_length": ok_length,
        "ok_upper": ok_upper,
        "ok_lower": ok_lower,
        "ok_digit": ok_digit,
        "ok_special": ok_special,
    }
