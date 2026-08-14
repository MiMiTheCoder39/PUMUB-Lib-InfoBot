"""
utils/qrcode_gen.py
--------------------
QR Code generators:
  1. generate_book_qr    — Book detail page link (existing)
  2. generate_borrow_qr  — Borrow transaction QR (NEW)
"""

import os
import qrcode
from PIL import Image


def generate_book_qr(book_id, book_title, qr_folder,
                     base_url="http://127.0.0.1:5000"):
    """
    Book detail page QR Code.
    QR content: /student/book/<book_id>
    Returns: saved filename
    """
    url = f"{base_url}/student/book/{book_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    os.makedirs(qr_folder, exist_ok=True)

    filename = f"qr_book_{book_id}.png"
    filepath = os.path.join(qr_folder, filename)
    img.save(filepath)
    return filename


def generate_borrow_qr(borrow_id_code, qr_folder,
                       base_url="http://127.0.0.1:5000"):
    """
    Borrow transaction QR Code.
    QR content: /admin/borrows/scan/<borrow_id_code>
    Admin scans this to open issue form.
    Returns: saved filename
    """
    url = f"{base_url}/admin/borrows/scan/{borrow_id_code}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#16324f", back_color="white")
    os.makedirs(qr_folder, exist_ok=True)

    filename = f"qr_borrow_{borrow_id_code}.png"
    filepath = os.path.join(qr_folder, filename)
    img.save(filepath)
    return filename