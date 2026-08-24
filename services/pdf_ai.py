"""Grounded PDF summarization and document Q&A service.

The service accepts an already authenticated user's role and resolves the
book through the existing model. It never returns PDF bytes and never sends
unauthorized documents to the AI provider.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from flask import current_app

from models.book_model import get_book_by_id
from services.ai_service import AIServiceError, answer_from_context, summarize_text
from services.pdf_text import PDFExtractionError, extract_and_chunk_pdf
from utils.r2_storage import R2StorageError, download_bytes, is_enabled as r2_is_enabled

RESTRICTED_TYPES = {"thesis", "research_paper", "reference_book", "teachers_guide"}
SUMMARY_MODES = {
    "short": "Produce a short summary in 3-5 sentences.",
    "medium": "Produce a concise summary in 4-6 short sentences or bullet points.",
    "detailed": "Produce a detailed, structured summary covering the main ideas, scope, and important facts.",
}


def _assert_pdf_access(book: dict[str, Any] | None, role: str | None) -> dict[str, Any]:
    if not book:
        raise LookupError("Book was not found.")
    if book.get("resource_type") in RESTRICTED_TYPES and role != "teacher":
        raise PermissionError("This PDF is restricted to teacher accounts.")
    filename = (book.get("pdf_file") or "").strip()
    if not filename:
        raise PDFExtractionError("This book has no PDF file.")
    if r2_is_enabled():
        return {"book": book, "filename": filename}
    upload_folder = Path(current_app.config["UPLOAD_FOLDER_BOOKS"]).resolve()
    pdf_path = (upload_folder / filename).resolve()
    if upload_folder not in pdf_path.parents:
        raise PDFExtractionError("Invalid PDF path.")
    return {"book": book, "filename": filename, "pdf_path": pdf_path}


def _limits() -> dict[str, int]:
    return {
        "max_bytes": int(current_app.config.get("PDF_MAX_EXTRACT_BYTES", 50 * 1024 * 1024)),
        "max_pages": int(current_app.config.get("PDF_MAX_EXTRACT_PAGES", 100)),
        "max_chars": int(current_app.config.get("PDF_MAX_TEXT_CHARS", 500000)),
        "chunk_chars": int(current_app.config.get("PDF_CHUNK_CHARS", 1800)),
        "overlap": int(current_app.config.get("PDF_CHUNK_OVERLAP", 200)),
    }


def _extract(book_id: int, role: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    access = _assert_pdf_access(get_book_by_id(book_id), role)
    if r2_is_enabled():
        temp_path = None
        try:
            pdf_bytes, _ = download_bytes("books", access["filename"])
            with NamedTemporaryFile(prefix="libinfo-r2-", suffix=".pdf", delete=False) as temp:
                temp.write(pdf_bytes)
                temp_path = temp.name
            return access["book"], extract_and_chunk_pdf(temp_path, **_limits())
        except R2StorageError as exc:
            raise PDFExtractionError("PDF file could not be read from storage.") from exc
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
    extracted = extract_and_chunk_pdf(access["pdf_path"], **_limits())
    return access["book"], extracted


def _chunk_terms(text: str) -> set[str]:
    return {term.lower() for term in re.findall(r"[\w]{3,}", text or "")}


def _relevant_chunks(question: str, chunks: list[str], top_k: int) -> list[str]:
    if not chunks:
        return []
    terms = _chunk_terms(question)
    if not terms:
        return chunks[:top_k]
    ranked = []
    for index, chunk in enumerate(chunks):
        chunk_terms = _chunk_terms(chunk)
        score = len(terms & chunk_terms)
        ranked.append((score, -index, chunk))
    ranked.sort(reverse=True)
    selected = [chunk for score, _, chunk in ranked[:top_k] if score > 0]
    return selected or chunks[:top_k]


def summarize_pdf(book_id: int, role: str | None, mode: str = "medium", *, language: str = "my") -> dict[str, Any]:
    mode = (mode or "medium").lower().strip()
    if mode not in SUMMARY_MODES:
        raise ValueError("mode must be short, medium, or detailed")
    book, extracted = _extract(book_id, role)
    chunks = extracted.get("chunks") or []
    if not chunks:
        return {
            "status": "no_text",
            "mode": mode,
            "book": {"book_id": book.get("book_id"), "title": book.get("title")},
            "summary": (
                "ဒီ PDF ထဲက စာသားကို အကျဉ်းချုပ်ရန် ထုတ်ယူမရပါ။"
                if str(language).lower().startswith("my") else
                "No extractable text was found in this PDF."
            ),
            "warnings": extracted.get("warnings", []),
        }

    # Bound the number of intermediate summaries to the configured document size.
    max_summary_chunks = int(current_app.config.get("PDF_SUMMARY_MAX_CHUNKS", 24))
    working_chunks = chunks[:max_summary_chunks]
    chunk_summaries = []
    for chunk in working_chunks:
        chunk_summaries.append(summarize_text(
            chunk,
            max_output_tokens=220 if mode == "short" else 320,
        ))
    final_context = [
        "AUTHORITATIVE PDF EXCERPTS AND INTERMEDIATE SUMMARIES. Use only these facts.",
        *chunk_summaries,
    ]
    summary = answer_from_context(
        SUMMARY_MODES[mode],
        final_context,
        max_output_tokens=300 if mode == "short" else (600 if mode == "medium" else 1000),
        system_prompt=(
            "Write a natural, readable summary using only the supplied PDF excerpts and intermediate summaries. "
            "Do not invent facts. Keep it concise: answer the main point first, then give 3-6 key points or short sentences. "
            + ("Respond in Myanmar language." if str(language).lower().startswith("my") else "Respond in English.")
        ),
    )
    return {
        "status": "ok",
        "mode": mode,
        "book": {"book_id": book.get("book_id"), "title": book.get("title")},
        "summary": summary,
        "pages_processed": extracted.get("pages_processed", 0),
        "truncated": extracted.get("truncated", False),
        "warnings": extracted.get("warnings", []),
    }


def answer_pdf_question(book_id: int, role: str | None, question: str, *, language: str = "my") -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question is required")
    max_question_chars = int(current_app.config.get("AI_MAX_QUESTION_CHARS", 2000))
    if len(question.strip()) > max_question_chars:
        raise ValueError(f"question exceeds the {max_question_chars}-character limit")
    book, extracted = _extract(book_id, role)
    chunks = extracted.get("chunks") or []
    if not chunks:
        return {
            "status": "no_text",
            "book": {"book_id": book.get("book_id"), "title": book.get("title")},
            "answer": (
                "ဒီ PDF ထဲက စာသားကို ဖတ်ရှုရန် ထုတ်ယူမရပါ။"
                if str(language).lower().startswith("my") else
                "No extractable text was found in this PDF."
            ),
            "warnings": extracted.get("warnings", []),
        }
    top_k = int(current_app.config.get("PDF_QA_TOP_K", 6))
    relevant = _relevant_chunks(question, chunks, max(1, top_k))
    answer = answer_from_context(
        question,
        [
            "AUTHORITATIVE PDF CONTEXT. Answer only from these excerpts. "
            "If the answer is not present, say that it was not found in the PDF.",
            *relevant,
        ],
        max_output_tokens=700,
        system_prompt=(
            "Answer naturally using only the supplied PDF excerpts. If the answer is not present, say so clearly. "
            + ("Respond in Myanmar language." if str(language).lower().startswith("my") else "Respond in English.")
        ),
    )
    return {
        "status": "ok",
        "book": {"book_id": book.get("book_id"), "title": book.get("title")},
        "answer": answer,
        "matched_chunks": len(relevant),
        "truncated": extracted.get("truncated", False),
        "warnings": extracted.get("warnings", []),
    }
