"""Grounded natural-language information about books already in the library.

This service reuses get_book_by_id/search_books and never exposes private file,
QR, counter, or account fields to the model or caller.
"""

from __future__ import annotations

import json
import re
from typing import Any

from models.book_model import get_book_by_id, search_books
from services.ai_service import AIServiceError, answer_from_context, generate_response

_RESTRICTED_TYPES = {"thesis", "research_paper", "reference_book", "teachers_guide"}
_ALLOWED_FIELDS = (
    "book_id",
    "title",
    "isbn",
    "author_name",
    "category_name",
    "faculty_name",
    "description",
    "resource_type",
    "publish_date",
    "total_copies",
    "available_copies",
)


def _parse_intent(text: str) -> dict[str, Any]:
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AIServiceError("AI returned invalid book-information parameters.") from exc
    if not isinstance(payload, dict) or payload.get("intent") != "BOOK_INFORMATION":
        raise AIServiceError("The request was not identified as book information.")
    return payload


def _extract_book_reference(question: str) -> dict[str, Any]:
    prompt = (
        "Extract a book reference from this library question. Return JSON only "
        "with exactly these keys: intent, title, isbn. Set unknown values to null. "
        "intent must be BOOK_INFORMATION. Do not answer the question and do not "
        "invent a title, ISBN, author, or book. The title may be a partial phrase.\n"
        f"Question: {question[:4000]}"
    )
    return _parse_intent(
        generate_response(
            prompt,
            system_prompt=(
                "You are a strict JSON extractor. Extract only a title or ISBN "
                "explicitly present in the user question. Return no extra keys."
            ),
            max_output_tokens=1200,
            response_schema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "enum": ["BOOK_INFORMATION"]},
                    "title": {"type": ["string", "null"]},
                    "isbn": {"type": ["string", "null"]},
                },
                "required": ["intent", "title", "isbn"],
                "additionalProperties": False,
            },
            schema_name="book_information_reference",
        )
    )


def _safe_book(book: dict[str, Any]) -> dict[str, Any]:
    return {field: book.get(field) for field in _ALLOWED_FIELDS}


def _resolve_book(question: str, book_id: int | None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if book_id is not None:
        book = get_book_by_id(int(book_id))
        return (book, []) if book else (None, [])

    reference = _extract_book_reference(question)
    identifier = str(reference.get("isbn") or reference.get("title") or "").strip()
    if not identifier:
        return None, []
    matches = search_books(keyword=identifier, limit=5)
    if len(matches) == 1:
        return matches[0], []
    return None, matches


def answer_book_information(
    question: str,
    *,
    book_id: int | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    """Return an OpenAI-grounded answer using one actual database book."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    book, matches = _resolve_book(question, book_id)
    if book is None and matches:
        candidates = [
            {key: item.get(key) for key in ("book_id", "title", "author_name", "isbn")}
            for item in matches
        ]
        return {
            "intent": "BOOK_INFORMATION",
            "status": "ambiguous",
            "answer": "More than one library book matched. Please provide a book_id or a more specific title/ISBN.",
            "books": candidates,
        }
    if book is None:
        return {
            "intent": "BOOK_INFORMATION",
            "status": "not_found",
            "answer": "The requested book was not found in the library database.",
            "book": None,
        }

    if book.get("resource_type") in _RESTRICTED_TYPES and role != "teacher":
        return {
            "intent": "BOOK_INFORMATION",
            "status": "forbidden",
            "answer": "This resource's information is restricted to teacher accounts.",
            "book": {"book_id": book.get("book_id"), "title": book.get("title")},
        }

    safe_book = _safe_book(book)
    availability = {
        "available": int(book.get("available_copies") or 0) > 0,
        "available_copies": int(book.get("available_copies") or 0),
        "total_copies": int(book.get("total_copies") or 0),
    }
    context = [
        "AUTHORITATIVE LIBRARY DATABASE RECORD (use only these facts):",
        json.dumps(safe_book, ensure_ascii=False, default=str),
        "Derived availability from the record:",
        json.dumps(availability, ensure_ascii=False),
    ]
    answer = answer_from_context(question, context, max_output_tokens=1000)
    return {
        "intent": "BOOK_INFORMATION",
        "status": "ok",
        "answer": answer,
        "book": safe_book,
        "availability": availability,
    }
