"""
routes/file_routes.py
----------------------
External Library Storage file-serving blueprint (Option A migration).

Covers, borrow QR codes နှင့် profile pictures ကို app source tree အပြင်
(LIBRARY_STORAGE_ROOT) မှ access-controlled routes များဖြင့် serve လုပ်သည်။
static/uploads/ မှ public static asset အဖြစ် ဆက်မပြတော့။

- PDF ကိုမူ student_bp ရှိ /student/book/<id>/file route ကဆက် serve နေသည်
  (ထို route သည် resource_type access control + security headers ပါပြီးသား)။
- QR generator (utils/qrcode_gen.py) ကို မပြောင်း။ folder ကို Config မှ
  ထပ်ပို့သောကြောင့် target ပြောင်းရုံဖြင့် အလုပ်လုပ်သည်။
"""
import mimetypes
import os
from io import BytesIO
from flask import (
    Blueprint, send_file, send_from_directory, current_app, abort, session, request
)
from werkzeug.utils import secure_filename

from utils.decorators import login_required
from utils.r2_storage import (
    R2StorageError,
    download_bytes,
    is_enabled as r2_is_enabled,
    upload_path,
)

file_bp = Blueprint("library_file", __name__, url_prefix="/library/file")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def _safe_name(name):
    """secure_filename လုပ်ပြီး လွန်ကဲသော အရွယ်အစား မဖြစ်စေရ စစ်သည်။"""
    if not name:
        return None
    safe = secure_filename(name)
    if not safe or len(safe) > 120 or len(safe.split(".")) > 2:
        return None
    return safe


def _regenerate_missing_borrow_qr(filename, folder):
    """Recreate legacy borrow QR files that were generated before R2 upload.

    The QR filename contains only the approved borrow code. Regeneration is
    deterministic, protected by the route's login check, and does not change
    the borrow record or approval status.
    """
    if not filename.startswith("qr_borrow_") or not filename.endswith(".png"):
        return False
    borrow_code = filename[len("qr_borrow_"):-len(".png")]
    if not borrow_code.startswith("BR-") or len(borrow_code) > 80:
        return False
    from utils.qrcode_gen import generate_borrow_qr

    os.makedirs(folder, exist_ok=True)
    generated = generate_borrow_qr(
        borrow_code,
        folder,
        request.host_url.rstrip("/"),
    )
    return generated == filename and os.path.isfile(os.path.join(folder, filename))


def _serve(bucket_key, name, require_login=True):
    if require_login and "user_id" not in session:
        abort(401)
    safe = _safe_name(name)
    if not safe:
        abort(404)
    ext = safe.rsplit(".", 1)[1].lower() if "." in safe else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        abort(400)
    if r2_is_enabled():
        prefix = bucket_key.replace("LIBRARY_STORAGE_", "").lower()
        try:
            data, content_type = download_bytes(prefix, safe)
        except R2StorageError:
            # During storage migration, an older generated QR may still exist
            # in the configured local folder. Recreate legacy borrow QR files
            # when needed, then let the local/legacy checks serve the result.
            current_app.logger.warning("R2 object missing; trying local fallback: %s/%s", prefix, safe)
            if prefix == "qrcodes":
                local_qr_folder = current_app.config["LIBRARY_STORAGE_QRCODES"]
                if _regenerate_missing_borrow_qr(safe, local_qr_folder):
                    try:
                        upload_path(os.path.join(local_qr_folder, safe), "qrcodes", safe)
                    except R2StorageError:
                        current_app.logger.warning("Could not backfill regenerated QR to R2: %s", safe)
        else:
            response = send_file(
            BytesIO(data),
            mimetype=content_type or mimetypes.guess_type(safe)[0] or "application/octet-stream",
            download_name=safe,
            as_attachment=False,
        )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "private, no-store"
            return response

    folder = current_app.config[bucket_key]
    # Path traversal ကာကွယ် (filename အပေါ် ပထမ စစ်ရမည်)
    real_folder = os.path.realpath(folder)
    target = os.path.join(real_folder, safe)
    if os.path.realpath(target)[:len(real_folder)] != real_folder:
        abort(400)
    if not os.path.isfile(target):
        # Pre-migration legacy: static/uploads/<bucket>/ ထဲကျန်နေသော ဖိုင်များ
        # အတွက် static root ထဲမှ read-only fallback (serve သာ၊ save မလုပ်)
        legacy_bucket = bucket_key.replace("LIBRARY_STORAGE_", "").lower()
        if legacy_bucket == "profiles":
            # Pre-migration profile pictures သည် covers folder အောက်တွင် save ထားသောကြောင့်
            legacy_bucket = "covers"
        legacy_folder = os.path.join(current_app.root_path, "static", "uploads", legacy_bucket)
        real_legacy = os.path.realpath(legacy_folder)
        legacy_target = os.path.join(real_legacy, safe)
        if os.path.realpath(legacy_target)[:len(real_legacy)] != real_legacy or not os.path.isfile(legacy_target):
            abort(404)
        resp = send_from_directory(legacy_folder, safe, as_attachment=False)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Cache-Control"] = "private, no-store"
        return resp
    resp = send_from_directory(folder, safe, as_attachment=False)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@file_bp.route("/cover/<filename>")
def file_cover(filename):
    # Covers သည် catalog များ (home page, search) တွင် guest များလည်း မြင်ရသော
    # public display assets ဖြစ်သောကြောင့် login မတောင်း — path traversal
    # ကာကွယ်မှုများ (_safe_name + realpath check) က file_routes level မှာ ရှိသည်။
    return _serve("LIBRARY_STORAGE_COVERS", filename, require_login=False)


@file_bp.route("/qrcode/<filename>")
@login_required
def file_qrcode(filename):
    return _serve("LIBRARY_STORAGE_QRCODES", filename)


@file_bp.route("/profile/<filename>")
@login_required
def file_profile(filename):
    return _serve("LIBRARY_STORAGE_PROFILES", filename)
