"""
utils/reset_token.py
--------------------
Swappable secure password-reset token module (Phase F).

- Raw tokens are 24 uppercase alphanumeric characters displayed in
  6 groups of 4 (e.g. GPMG-X2NK-ZJT6-85J3-JUUD-348G) — single-use,
  15-minute expiry, stored as a scrypt hash (Phase B/C family).
- Constant-time comparison on redemption; the token is consumed
  (marked used) and all other pending tokens for that user are
  invalidated on successful redemption.
- No email/SMTP: the raw token is returned once to the route, which
  shows it in-app and keeps it in the session for verification.
"""

import datetime
import random
import string
import secrets

from werkzeug.security import generate_password_hash, check_password_hash

# Same scrypt family as Phase B/C password hashing.
HASH_METHOD = "scrypt:32768:8:1"
TOKEN_LIFETIME_MINUTES = 15
TOKEN_LENGTH = 24
GROUP_SIZE = 4

_ALPHABET = string.ascii_uppercase + string.digits


def _ping(conn):
    try:
        conn.ping(reconnect=True)
    except Exception:
        pass


def create_reset_token(user_id):
    """Create a single-use token for `user_id`.

    Invalidates any other PENDING (unused, unexpired) tokens for the
    user first, so each user holds at most one live token.

    Returns the raw token string (the ONLY place it is ever visible);
    the hash + expiry are stored in `reset_tokens`.
    """
    from models.db import mysql
    _ping(mysql.connection)
    raw = "".join(random.SystemRandom().choice(_ALPHABET)
                  for _ in range(TOKEN_LENGTH))
    hashed = generate_password_hash(raw, method=HASH_METHOD)
    expires_at = (datetime.datetime.utcnow()
                  + datetime.timedelta(minutes=TOKEN_LIFETIME_MINUTES))

    cur = mysql.connection.cursor()
    try:
        # Invalidate other pending tokens for this user.
        cur.execute(
            "UPDATE reset_tokens SET used = 1 WHERE user_id = %s "
            "AND used = 0 AND expires_at > NOW()",
            (int(user_id),),
        )
        cur.execute(
            "INSERT INTO reset_tokens (user_id, token_hash, expires_at, used) "
            "VALUES (%s, %s, %s, 0)",
            (int(user_id), hashed, expires_at),
        )
        mysql.connection.commit()
    finally:
        cur.close()
    return raw


def _find_pending(user_id):
    """Return (id, token_hash) of the live token for `user_id`, or None."""
    from models.db import mysql
    _ping(mysql.connection)
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT id, token_hash FROM reset_tokens "
            "WHERE user_id = %s AND used = 0 AND expires_at > NOW() "
            "ORDER BY created_at DESC LIMIT 1",
            (int(user_id),),
        )
        return cur.fetchone()
    finally:
        cur.close()


def consume_token(user_id, raw_token):
    """Constant-time verify + consume a token.

    Marks the token used and invalidates every other pending token for
    the user. Returns True on success, False on miss/expiry/reuse.
    """
    from models.db import mysql
    if not raw_token or not user_id:
        return False
    row = _find_pending(user_id)
    if not row:
        return False
    token_id, token_hash = row["id"], row["token_hash"]
    if not check_password_hash(token_hash, raw_token):
        return False
    _ping(mysql.connection)
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "UPDATE reset_tokens SET used = 1 WHERE id = %s",
            (token_id,),
        )
        cur.execute(
            "UPDATE reset_tokens SET used = 1 "
            "WHERE user_id = %s AND used = 0",
            (int(user_id),),
        )
        mysql.connection.commit()
    finally:
        cur.close()
    return True


def invalidate_user_tokens(user_id):
    """Mark every pending token for `user_id` as used."""
    from models.db import mysql
    _ping(mysql.connection)
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "UPDATE reset_tokens SET used = 1 "
            "WHERE user_id = %s AND used = 0",
            (int(user_id),),
        )
        mysql.connection.commit()
    finally:
        cur.close()


def cleanup_expired_tokens():
    """Remove expired rows (safe to call periodically)."""
    from models.db import mysql
    _ping(mysql.connection)
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM reset_tokens WHERE expires_at < NOW()")
        mysql.connection.commit()
    finally:
        cur.close()


def format_token(raw):
    """Display as 6 groups of 4: GPMG-X2NK-ZJT6-85J3-JUUD-348G."""
    if not raw or len(raw) != TOKEN_LENGTH:
        return raw or ""
    return "-".join(raw[i:i + GROUP_SIZE]
                    for i in range(0, TOKEN_LENGTH, GROUP_SIZE))
