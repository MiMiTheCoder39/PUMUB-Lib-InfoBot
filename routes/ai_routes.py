"""AI endpoints added incrementally without replacing existing library routes."""

import hmac

from flask import Blueprint, current_app, jsonify, request, session

from services.ai_rate_limit import consume
from services.ai_service import AIServiceError
from services.book_search_ai import search_from_question
from services.book_information_ai import answer_book_information
from services.pdf_ai import answer_pdf_question, summarize_pdf
from services.pdf_text import PDFExtractionError
from services.chat_orchestrator import detect_message_language, handle_chat
from utils.decorators import library_user_required, login_required

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


def _rate_limit_response():
    user_id = session.get("user_id")
    key = f"user:{user_id}" if user_id is not None else f"ip:{request.remote_addr or 'unknown'}"
    allowed, retry_after = consume(
        key,
        limit=current_app.config.get("AI_RATE_LIMIT_REQUESTS", 20),
        window_seconds=current_app.config.get("AI_RATE_LIMIT_WINDOW_SECONDS", 60),
    )
    if allowed:
        return None
    response = jsonify({"error": "AI request rate limit exceeded. Please try again later."})
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


def _ai_unavailable_response(question: str = ""):
    language = detect_message_language(question or "")
    message = (
        "လက်ရှိ AI ဝန်ဆောင်မှု ခဏမရသေးပါ။ ခဏအကြာ ပြန်မေးကြည့်ပါ။"
        if language == "my"
        else "The AI service is temporarily unavailable. Please try again shortly."
    )
    return jsonify({"error": message}), 503


def _validate_question(payload):
    if not isinstance(payload, dict):
        return None, (jsonify({"error": "JSON object body is required"}), 400)
    question = (payload.get("question") or "").strip()
    max_chars = int(current_app.config.get("AI_MAX_QUESTION_CHARS", 2000))
    if not question:
        return None, (jsonify({"error": "question is required"}), 400)
    if len(question) > max_chars:
        return None, (jsonify({"error": f"question exceeds the {max_chars}-character limit"}), 413)
    return question, None


@ai_bp.post("/chat")
@login_required
@library_user_required
def ai_chat():
    """Dispatch LibInfoBot messages to existing, authorized backend services."""
    payload = request.get_json(silent=True) or {}
    question, error = _validate_question(payload)
    if error:
        return error
    limited = _rate_limit_response()
    if limited:
        return limited
    raw_book_id = payload.get("book_id") if isinstance(payload, dict) else None
    try:
        book_id = int(raw_book_id) if raw_book_id is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "book_id must be an integer"}), 400
    try:
        return jsonify(handle_chat(
            question,
            user_id=int(session["user_id"]),
            role=session.get("role"),
            book_id=book_id,
            action=payload.get("action"),
            mode=payload.get("mode", "medium"),
            language=detect_message_language(question),
        ))
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except PDFExtractionError as exc:
        return jsonify({"error": str(exc)}), 422
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError as exc:
        current_app.logger.exception("LibInfoBot AI request failed: %s", exc)
        return _ai_unavailable_response(question)


@ai_bp.get("/health")
def ai_health():
    """Verify Flask -> AI service -> OpenAI -> response when explicitly enabled."""
    from services.ai_service import generate_response

    if not current_app.config.get("AI_HEALTHCHECK_ENABLED", False):
        return jsonify({"status": "disabled"}), 404
    if current_app.config.get("AI_PRODUCTION", True):
        configured_token = current_app.config.get("AI_HEALTHCHECK_TOKEN")
        supplied_token = request.headers.get("X-AI-Health-Token", "")
        if not configured_token or not hmac.compare_digest(str(supplied_token), str(configured_token)):
            return jsonify({"status": "disabled"}), 404
    try:
        response = generate_response(
            "Reply with exactly: AI_CONNECTION_OK",
            system_prompt="Return only the requested health-check token.",
            max_output_tokens=256,
        )
    except AIServiceError:
        current_app.logger.exception("AI health check failed")
        return jsonify({"status": "error", "message": "AI health check failed."}), 503
    return jsonify({"status": "ok", "response": response})


@ai_bp.post("/book-information")
@login_required
@library_user_required
def ai_book_information():
    """Answer questions about one actual database book using grounded context."""
    payload = request.get_json(silent=True) or {}
    question, error = _validate_question(payload)
    if error:
        return error
    limited = _rate_limit_response()
    if limited:
        return limited
    raw_book_id = payload.get("book_id")
    try:
        book_id = int(raw_book_id) if raw_book_id is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "book_id must be an integer"}), 400
    try:
        return jsonify(answer_book_information(
            question,
            book_id=book_id,
            role=session.get("role"),
            language=detect_message_language(question),
        ))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError as exc:
        current_app.logger.exception("Book information AI request failed: %s", exc)
        return _ai_unavailable_response(question)


@ai_bp.post("/pdf-summary")
@login_required
@library_user_required
def ai_pdf_summary():
    """Summarize an authorized existing library PDF; no PDF bytes are returned."""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object body is required"}), 400
    raw_book_id = payload.get("book_id")
    try:
        book_id = int(raw_book_id)
    except (TypeError, ValueError):
        return jsonify({"error": "book_id must be an integer"}), 400
    limited = _rate_limit_response()
    if limited:
        return limited
    try:
        return jsonify(summarize_pdf(book_id, session.get("role"), payload.get("mode", "medium"), language=detect_message_language(payload.get("question") or "")))
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except PDFExtractionError as exc:
        return jsonify({"error": str(exc)}), 422
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError as exc:
        current_app.logger.exception("PDF summary AI request failed: %s", exc)
        return _ai_unavailable_response(str(payload.get("question") or ""))


@ai_bp.post("/pdf-question")
@login_required
@library_user_required
def ai_pdf_question():
    """Answer only from relevant chunks of an authorized existing library PDF."""
    payload = request.get_json(silent=True) or {}
    question, error = _validate_question(payload)
    if error:
        return error
    raw_book_id = payload.get("book_id") if isinstance(payload, dict) else None
    try:
        book_id = int(raw_book_id)
    except (TypeError, ValueError):
        return jsonify({"error": "book_id must be an integer"}), 400
    limited = _rate_limit_response()
    if limited:
        return limited
    try:
        return jsonify(answer_pdf_question(book_id, session.get("role"), question, language=detect_message_language(question)))
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except PDFExtractionError as exc:
        return jsonify({"error": str(exc)}), 422
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError as exc:
        current_app.logger.exception("PDF question AI request failed: %s", exc)
        return _ai_unavailable_response(question)


@ai_bp.post("/book-search")
@login_required
@library_user_required
def ai_book_search():
    """Natural-language interface to the existing Book Search query."""
    payload = request.get_json(silent=True) or {}
    question, error = _validate_question(payload)
    if error:
        return error
    limited = _rate_limit_response()
    if limited:
        return limited
    try:
        return jsonify(search_from_question(question, language=detect_message_language(question)))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError as exc:
        current_app.logger.exception("Book search AI request failed: %s", exc)
        return _ai_unavailable_response(question)
