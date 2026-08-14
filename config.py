"""
config.py
---------
Flask App Configuration.
Reads values from the .env file using python-dotenv.
XAMPP ရဲ့ MySQL default setting (root user, password blank) ကို သုံးထားပါတယ်။
"""

import os
from dotenv import load_dotenv

# .env file ကို load လုပ်ပါ
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Flask Secret Key (session, CSRF စသည်တို့အတွက်)
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback_secret_key")

    # ---------------- OpenAI AI Integration ----------------
    # Secrets are read only from the environment/.env and never sent to templates.
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    OPENAI_TIMEOUT_SECONDS = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "20"))
    OPENAI_MAX_INPUT_CHARS = int(os.environ.get("OPENAI_MAX_INPUT_CHARS", "12000"))
    OPENAI_MAX_OUTPUT_TOKENS = int(os.environ.get("OPENAI_MAX_OUTPUT_TOKENS", "1600"))
    AI_MAX_QUESTION_CHARS = int(os.environ.get("AI_MAX_QUESTION_CHARS", "2000"))
    AI_RATE_LIMIT_REQUESTS = int(os.environ.get("AI_RATE_LIMIT_REQUESTS", "20"))
    AI_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("AI_RATE_LIMIT_WINDOW_SECONDS", "60"))
    AI_HEALTHCHECK_ENABLED = os.environ.get("AI_HEALTHCHECK_ENABLED", "false").lower() == "true"
    AI_HEALTHCHECK_TOKEN = os.environ.get("AI_HEALTHCHECK_TOKEN")
    AI_PRODUCTION = os.environ.get("FLASK_ENV", "production").lower() == "production"

    # ---------------- PDF AI Foundation Limits ----------------
    PDF_MAX_EXTRACT_BYTES = int(os.environ.get("PDF_MAX_EXTRACT_BYTES", 50 * 1024 * 1024))
    PDF_MAX_EXTRACT_PAGES = int(os.environ.get("PDF_MAX_EXTRACT_PAGES", "100"))
    PDF_MAX_TEXT_CHARS = int(os.environ.get("PDF_MAX_TEXT_CHARS", "500000"))
    PDF_CHUNK_CHARS = int(os.environ.get("PDF_CHUNK_CHARS", "1800"))
    PDF_CHUNK_OVERLAP = int(os.environ.get("PDF_CHUNK_OVERLAP", "200"))
    PDF_SUMMARY_MAX_CHUNKS = int(os.environ.get("PDF_SUMMARY_MAX_CHUNKS", "24"))
    PDF_QA_TOP_K = int(os.environ.get("PDF_QA_TOP_K", "6"))

    # ---------------- MySQL Configuration (Railway & Local Fallback) ----------------
    MYSQL_HOST = os.environ.get("MYSQLHOST") or os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_USER = os.environ.get("MYSQLUSER") or os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQLPASSWORD") or os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQLDATABASE") or os.environ.get("MYSQL_DB", "digital_library_db")
    MYSQL_PORT = int(os.environ.get("MYSQLPORT") or os.environ.get("MYSQL_PORT", 3306))
    MYSQL_CURSORCLASS = "DictCursor"  # query results ကို dict အနေနဲ့ ပြန်ရအောင်

    # ---------------- File Upload Configuration ----------------
    UPLOAD_FOLDER_BOOKS = os.path.join(BASE_DIR, "static/uploads/books")
    UPLOAD_FOLDER_COVERS = os.path.join(BASE_DIR, "static/uploads/covers")
    UPLOAD_FOLDER_QRCODES = os.path.join(BASE_DIR, "static/uploads/qrcodes")

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))  # 50MB

    ALLOWED_PDF_EXTENSIONS = {"pdf"}
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

    # Session ကို browser ပိတ်ရင် ပျောက်အောင် (False ဆို permanent)
    SESSION_PERMANENT = False
