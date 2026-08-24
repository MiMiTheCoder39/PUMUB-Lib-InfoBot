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
    OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    # Convenience aliases: if a .env uses GROQ_API_KEY / GROQ_MODEL instead of
    # the OPENAI_* names, fall back to them automatically. This keeps the
    # chatbot working even when the example template names are used.
    if not OPENAI_API_KEY:
        OPENAI_API_KEY = os.environ.get("GROQ_API_KEY")
    if OPENAI_MODEL in (None, "gpt-5-mini"):
        OPENAI_MODEL = os.environ.get("GROQ_MODEL", OPENAI_MODEL)
    if not OPENAI_API_BASE:
        OPENAI_API_BASE = os.environ.get("GROQ_API_BASE", "https://api.groq.com/openai/v1")

    # ---------------- Gemini Secondary Provider (key2) ----------------
    # ဒီ project က primary key (Groq) + secondary key (Gemini) နှစ်ကြိမ် setup ကို
    # ထောက်ပံ့ပါတယ်။ AI_PROVIDER ပြောင်းလိုက်ရင် ချက်ချင်း provider ရွေ့သွားမယ်။
    # Gemini ကို OpenAI-compatible endpoint ဖြင့် ချိတ်သုံးပြီး chat.completions
    # style ကိုသုံးရာမှာ structured JSON extraction နဲ့ general chat နှစ်မျိုးလုံး
    # ထောက်ပံ့ပါတယ်။
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    # Primary provider ရွေးချယ်ရန်: "primary" (default, Groq) သို့မဟုတ် "gemini"
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "primary").lower()
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

    # Connection charset — utf8mb4 (4-byte) ဖြစ်ရန်။ utf8 (utf8mb3) သည် 4-byte
    # characters (emoji စသည်) ကို INSERT လုပ်လျှင် MySQL error 1366 ဖြင့်
    # crash ဖြစ်စေသည်။ Railway တွင် MYSQL_CHARSET=utf8mb4 env var ထည့်ပေးပါ။
    MYSQL_CHARSET = os.environ.get("MYSQL_CHARSET", "utf8mb4")

    # ---------------- File Upload Configuration (External Library Storage) ----------------
    # LIBRARY_STORAGE_ROOT ကို environment variable ဖြင့် configure လုပ်ပါ။
    # App source tree အပြင် ဖြစ်ရန် — static/uploads/ အတွင်း ထည့်လျှင် source
    # ZIP size ကြီးလာမည် (Option A — External Library Storage migration).
    # Default သည် app root ၏ parent directory အောက်တွင် library_storage/ ဖြစ်ပြီး
    # local dev အတွက်သာ။ Railway တွင် LIBRARY_STORAGE_ROOT env var မဖြစ်မနေ set ပါ။
    _LSR_DEFAULT = os.path.join(os.path.dirname(BASE_DIR), "library_storage")
    LIBRARY_STORAGE_ROOT = os.environ.get("LIBRARY_STORAGE_ROOT") or _LSR_DEFAULT
    LIBRARY_STORAGE_BOOKS = os.path.join(LIBRARY_STORAGE_ROOT, "books")
    LIBRARY_STORAGE_COVERS = os.path.join(LIBRARY_STORAGE_ROOT, "covers")
    LIBRARY_STORAGE_QRCODES = os.path.join(LIBRARY_STORAGE_ROOT, "qrcodes")
    LIBRARY_STORAGE_PROFILES = os.path.join(LIBRARY_STORAGE_ROOT, "profiles")
    # Legacy names — အရင် code ကို မထိအောင် alias ထားခြင်း (တန်ဖိုးများ external storage ဖြစ်သွားပြီ)
    UPLOAD_FOLDER_BOOKS = LIBRARY_STORAGE_BOOKS
    UPLOAD_FOLDER_COVERS = LIBRARY_STORAGE_COVERS
    UPLOAD_FOLDER_QRCODES = LIBRARY_STORAGE_QRCODES

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))  # 50MB

    ALLOWED_PDF_EXTENSIONS = {"pdf"}
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

    # Session ကို browser ပိတ်ရင် ပျောက်အောင် (False ဆို permanent)
    SESSION_PERMANENT = False
