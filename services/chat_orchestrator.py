"""LibInfoBot conversation orchestration over existing library services.

This module does not implement search, recommendations, book details, or PDF
processing. It only chooses an existing service based on explicit request
metadata or conservative language hints.
"""

from __future__ import annotations

from typing import Any

from flask import current_app

from models.book_model import get_book_by_id
from services.book_information_ai import answer_book_information
from services.book_search_ai import search_from_question
from services.ai_service import generate_response
from services.pdf_ai import answer_pdf_question, summarize_pdf
from utils.recommender import get_recommendations

FAQ = {
    "borrow": "You can request a book from its details page. Library staff approve, issue, and record returns from the admin borrowing workflow.",
    "return": "For return questions, check My Borrowings or contact the library desk. Return status and fines are controlled by the library records.",
    "fine": "You can view your current fines and clearance status from your account menu. Fine amounts and payment state come from the library database.",
    "hours": "For current opening hours, please check the latest library announcement or contact the library desk.",
    "contact": "You can contact the library at library@pumub.edu.mm or visit the Polytechnic University (Maubin) library desk.",
}


def _public_book(book: dict[str, Any]) -> dict[str, Any]:
    return {
        "book_id": book.get("book_id"),
        "title": book.get("title"),
        "author_name": book.get("author_name") or book.get("author"),
        "isbn": book.get("isbn"),
        "category_name": book.get("category_name") or book.get("category"),
        "resource_type": book.get("resource_type"),
        "available_copies": book.get("available_copies"),
    }


def _recommendations(user_id: int) -> dict[str, Any]:
    rows = get_recommendations(user_id, top_n=8) or []
    books = [_public_book(row) for row in rows]
    return {
        "intent": "BOOK_RECOMMENDATION",
        "status": "ok" if books else "not_found",
        "answer": "Here are recommendations based on your library activity." if books else "I do not have enough library activity to recommend books yet.",
        "books": books,
    }


def _faq_answer(question: str) -> str | None:
    lowered = question.lower()
    for terms, answer in (
        (("borrow", "loan", "checkout"), FAQ["borrow"]),
        (("return", "returned"), FAQ["return"]),
        (("fine", "penalty", "clearance"), FAQ["fine"]),
        (("hour", "open", "close"), FAQ["hours"]),
        (("contact", "email", "phone"), FAQ["contact"]),
    ):
        if any(term in lowered for term in terms):
            return answer
    return None


def handle_chat(question: str, *, user_id: int, role: str | None, book_id: int | None = None, action: str | None = None, mode: str = "medium") -> dict[str, Any]:
    if action == "pdf_summary":
        if book_id is None:
            raise ValueError("Select a book before requesting a PDF summary.")
        return {"intent": "PDF_SUMMARY", **summarize_pdf(book_id, role, mode)}
    if action == "pdf_question":
        if book_id is None:
            raise ValueError("Select a book before asking a PDF question.")
        return {"intent": "PDF_QA", **answer_pdf_question(book_id, role, question)}
    if action == "book_information" or book_id is not None:
        return answer_book_information(question, book_id=book_id, role=role)

    lowered = question.lower()
    if any(term in lowered for term in ("recommend", "suggest", "suggestion", "what should i read")):
        return _recommendations(user_id)
    faq = _faq_answer(question)
    if faq:
        return {"intent": "LIBRARY_FAQ", "status": "ok", "answer": faq, "books": []}
    if any(term in lowered for term in ("help", "what can you do", "how can you help")):
        return {
            "intent": "GENERAL_LIBRARY_ASSISTANCE",
            "status": "ok",
            "answer": "I can search the library, explain a book record, recommend books from your library activity, summarize an authorized PDF, answer questions from an authorized PDF, and explain basic library services.",
            "books": [],
        }
    return {
        "intent": "GENERAL_LIBRARY_CHAT",
        "status": "ok",
        "answer": generate_response(
            question,
            system_prompt=(
                "You are LibInfoBot, a helpful digital-library assistant. "
                "Answer briefly and accurately. If the question needs live "
                "library records, ask the user to search the library or provide "
                "a book title, author, or ISBN."
            ),
        ),
        "books": [],
    }
