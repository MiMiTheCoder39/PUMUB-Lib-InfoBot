"""AI-primary personalized book recommendations with deterministic fallback.

The deterministic recommender remains the candidate generator and fallback. AI is
used once to rank those real database books and provide short explanations; it
cannot invent books because returned IDs are validated against the candidate set.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from services.ai_service import AIServiceError, generate_response
from utils.recommender import get_recommendations

logger = logging.getLogger(__name__)


def _parse_ranked_response(raw: str) -> list[dict[str, Any]]:
    """Parse the model's JSON without trusting any fields from it."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    payload = json.loads(text)
    rows = payload.get("recommendations", []) if isinstance(payload, dict) else []
    return rows if isinstance(rows, list) else []


RECOMMENDATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "book_id": {"type": "integer"},
                    "reason": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["book_id", "reason", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["recommendations"],
    "additionalProperties": False,
}


def _candidate_prompt(profile: str, candidates: list[dict[str, Any]], top_n: int) -> str:
    # The model needs faculty/borrow context, not the user's name.
    safe_profile = "\n".join(
        line for line in (profile or "").splitlines()
        if not line.lower().startswith("user name:")
    )
    candidate_lines = []
    for book in candidates:
        candidate_lines.append(
            json.dumps(
                {
                    "book_id": int(book["book_id"]),
                    "title": book.get("title") or "",
                    "author": book.get("author_name") or "",
                    "category": book.get("category_name") or "",
                    "description": (book.get("description") or "")[:500],
                    "resource_type": book.get("resource_type") or "",
                },
                ensure_ascii=False,
            )
        )
    return (
        "You are a careful university librarian. Rank real books for this user.\n"
        "Use ONLY the candidate books below. Never invent a book_id, title, author, or fact.\n"
        f"Return at most {top_n} recommendations in JSON only, with this exact shape:\n"
        '{"recommendations":[{"book_id":123,"reason":"one short Burmese sentence"}]}\n'
        "Prefer books matching the user's activity/profile and diversify categories when reasonable. "
        "If evidence is weak, give a neutral reason rather than claiming the user read a book.\n\n"
        f"USER PROFILE:\n{safe_profile or 'No profile details available.'}\n\n"
        "CANDIDATE BOOKS:\n" + "\n".join(candidate_lines)
    )


def get_smart_recommendations(user_id: int, top_n: int = 8) -> List[Dict[str, Any]]:
    """Return AI-ranked recommendations, with the existing engine as fallback."""
    top_n = max(1, min(int(top_n), 20))
    # Generate a wider deterministic candidate pool so AI can choose among real books.
    # A wider real-book pool gives the model room to diversify categories/authors.
    candidate_pool_size = min(24, max(12, top_n * 2 + 4))
    candidates = get_recommendations(user_id, top_n=candidate_pool_size)
    if not candidates:
        return []

    candidate_by_id = {int(book["book_id"]): book for book in candidates if book.get("book_id") is not None}
    fallback = list(candidate_by_id.values())[:top_n]
    try:
        # Keep recommendation startup-safe when an older deployment lacks
        # the optional profile-context helper; ranking will still use candidates.
        try:
            from services.retrieval_orchestrator import get_user_profile_context
            profile = get_user_profile_context(user_id)
        except (ImportError, AttributeError):
            profile = ""
        raw = generate_response(
            _candidate_prompt(profile, list(candidate_by_id.values()), top_n),
            system_prompt=(
                "Return only the supplied JSON schema. Ground every recommendation in the supplied candidate list. "
                "Do not include markdown or commentary outside the JSON. Keep each reason under 160 characters. "
                "Set confidence between 0 and 1; use a lower confidence when evidence is weak."
            ),
            max_output_tokens=700,
            response_schema=RECOMMENDATION_RESPONSE_SCHEMA,
            schema_name="book_recommendations",
        )
        ranked_rows = _parse_ranked_response(raw)
    except (AIServiceError, ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.warning("AI recommendation ranking unavailable; using deterministic fallback: %s", exc)
        return fallback
    except Exception as exc:  # defensive provider/parser fallback
        logger.warning("Unexpected AI recommendation error; using deterministic fallback: %s", exc)
        return fallback

    ranked: list[dict[str, Any]] = []
    used_ids: set[int] = set()
    for row in ranked_rows:
        if not isinstance(row, dict):
            continue
        try:
            book_id = int(row.get("book_id"))
        except (TypeError, ValueError):
            continue
        book = candidate_by_id.get(book_id)
        if not book or book_id in used_ids:
            continue
        reason = str(row.get("reason") or "").strip()
        if reason:
            book = dict(book)
            book["ai_hook"] = reason[:320]
            try:
                book["ai_confidence"] = max(0.0, min(1.0, float(row.get("confidence", 0.0))))
            except (TypeError, ValueError):
                book["ai_confidence"] = 0.0
        ranked.append(book)
        used_ids.add(book_id)
        if len(ranked) >= top_n:
            break

    # Complete partial model output deterministically, preserving only real books.
    for book in fallback:
        if int(book["book_id"]) not in used_ids:
            ranked.append(book)
            if len(ranked) >= top_n:
                break
    return ranked[:top_n]
