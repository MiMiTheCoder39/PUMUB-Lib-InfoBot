"""
utils/file_utils.py
----------------------
File upload အတွက် helper functions: extension validation, safe filename generation.
Book PDF, Cover Image, Profile Picture အားလုံး ဒီ helper တွေကို သုံးပါမယ်။
"""

import os
import uuid
from werkzeug.utils import secure_filename


def allowed_file(filename, allowed_extensions):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_extensions


def generate_unique_filename(original_filename):
    """Original filename ကို secure လုပ်ပြီး UUID prefix တပ်ပါမယ် (overwrite မဖြစ်အောင်)."""
    safe_name = secure_filename(original_filename)
    ext = safe_name.rsplit(".", 1)[1].lower() if "." in safe_name else ""
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    return unique_name


def save_uploaded_file(file_storage, upload_folder, allowed_extensions):
    """
    file_storage: request.files['xyz']
    upload_folder: absolute path (Config.UPLOAD_FOLDER_*)
    Returns: saved filename (string) သို့မဟုတ် None (file မရှိရင်/extension မမှန်ရင်)
    """
    if not file_storage or file_storage.filename == "":
        return None

    if not allowed_file(file_storage.filename, allowed_extensions):
        return None

    filename = generate_unique_filename(file_storage.filename)
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file_storage.save(filepath)
    return filename