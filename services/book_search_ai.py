"""Natural-language adapter for the existing Book Search implementation.

The model only extracts search parameters. All book rows come from the existing
models.book_model.search_books() query; the model never invents results.
"""

from __future__ import annotations

import json
import re
from typing import Any

from models.book_model import get_all_authors, get_all_categories, search_books
from services.ai_service import AIServiceError, generate_response

_ALLOWED_RESOURCE_TYPES = {
    "book",
    "ebook",
    "thesis",
    "journal",
    "research_paper",
    "reference_book",
    "teachers_guide",
}


def _clean_json(text: str) -> dict[str, Any]:
    value = text.strip()
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE)
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AIServiceError("AI returned invalid search parameters.") from exc
    if not isinstance(payload, dict):
        raise AIServiceError("AI returned an invalid search parameter object.")
    return payload


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def extract_book_search_intent(question: str) -> dict[str, Any]:
    """Extract only supported search fields from a natural-language question."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    categories = [str(row.get("category_name", "")) for row in get_all_categories()]
    authors = [str(row.get("author_name", "")) for row in get_all_authors()]
    prompt = (
        "Extract search parameters from the user's library-search request. "
        "Return JSON only with exactly these keys: intent, keyword, isbn, "
        "author_name, category_name, resource_type, sort_by. "
        "intent must be BOOK_SEARCH. Use null for unknown fields. "
        "keyword should contain the title or topic phrase, not conversational words. "
        "isbn should contain only an ISBN when present. "
        "resource_type must be one of book, ebook, thesis, journal, "
        "research_paper, reference_book, teachers_guide, or null. "
        f"Known categories: {categories[:200]}\n"
        f"Known authors: {authors[:200]}\n"
        f"User request: {question[:4000]}"
    )
    payload = _clean_json(
        generate_response(
            prompt,
            system_prompt=(
                "You are a strict JSON parameter extractor for a library search. "
                "Do not answer the user, do not create books, and do not add keys."
            ),
            max_output_tokens=1200,
            response_schema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "enum": ["BOOK_SEARCH"]},
                    "keyword": {"type": ["string", "null"]},
                    "isbn": {"type": ["string", "null"]},
                    "author_name": {"type": ["string", "null"]},
                    "category_name": {"type": ["string", "null"]},
                    "resource_type": {"type": ["string", "null"]},
                    "sort_by": {"type": ["string", "null"]},
                },
                "required": [
                    "intent", "keyword", "isbn", "author_name",
                    "category_name", "resource_type", "sort_by",
                ],
                "additionalProperties": False,
            },
            schema_name="book_search_intent",
        )
    )
    if payload.get("intent") != "BOOK_SEARCH":
        raise AIServiceError("The request was not identified as a book search.")

    result = {
        "intent": "BOOK_SEARCH",
        "keyword": _text(payload.get("keyword")),
        "isbn": _text(payload.get("isbn")),
        "author_name": _text(payload.get("author_name")),
        "category_name": _text(payload.get("category_name")),
        "resource_type": _text(payload.get("resource_type")),
        "sort_by": _text(payload.get("sort_by")),
    }
    if result["resource_type"] not in (None, *_ALLOWED_RESOURCE_TYPES):
        result["resource_type"] = None
    return result


def _lookup_id(rows: list[dict[str, Any]], name: str | None, key: str) -> int | None:
    if not name:
        return None
    needle = name.casefold()
    for row in rows:
        value = str(row.get(key, "")).strip()
        if value.casefold() == needle:
            return int(row[f"{key[:-5]}_id"] if key.endswith("_name") else row["id"])
    return None


def _resolve_params(intent: dict[str, Any]) -> dict[str, Any]:
    categories = get_all_categories()
    authors = get_all_authors()
    category_name = intent.get("category_name")
    author_name = intent.get("author_name")
    category_id = None
    author_id = None
    if category_name:
        for row in categories:
            if str(row.get("category_name", "")).casefold() == category_name.casefold():
                category_id = row.get("category_id")
                category_name = row.get("category_name")
                break
    if author_name:
        for row in authors:
            if str(row.get("author_name", "")).casefold() == author_name.casefold():
                author_id = row.get("author_id")
                author_name = row.get("author_name")
                break

    keyword_parts = []
    if intent.get("isbn"):
        keyword_parts.append(intent["isbn"])
    if intent.get("keyword"):
        keyword_parts.append(intent["keyword"])
    if category_name and not category_id:
        keyword_parts.append(category_name)
    if author_name and not author_id:
        keyword_parts.append(author_name)

    return {
        "keyword": " ".join(keyword_parts) or None,
        "category_id": category_id,
        "faculty_id": None,
        "author_id": author_id,
        "resource_type": intent.get("resource_type"),
    }


def search_from_question(question: str) -> dict[str, Any]:
    """Understand a question, call existing search_books(), and format DB rows."""
    intent = extract_book_search_intent(question)
    params = _resolve_params(intent)
    books = search_books(**params)
    result_books = [
        {
            key: book.get(key)
            for key in (
                "book_id",
                "title",
                "isbn",
                "author_name",
                "category_name",
                "faculty_name",
                "resource_type",
                "cover_image",
                "view_count",
                "download_count",
                "available_copies",
            )
            if key in book
        }
        for book in books
    ]
    count = len(result_books)
    answer = (
        f"Found {count} matching book(s) from the library database."
        if count
        else "No matching books were found in the library database."
    )
    return {
        "intent": intent["intent"],
        "search_params": params,
        "books": result_books,
        "count": count,
        "answer": answer,
    }
