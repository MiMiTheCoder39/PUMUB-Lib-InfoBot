"""Safe PDF text extraction and chunking foundation.

This module is intentionally not wired into PDF serving or chatbot routes in
PHASE 4. It reads only an already-authorized local path supplied by backend
code; it does not download URLs, execute files, or mutate library records.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyPDF2 import PdfReader


class PDFExtractionError(RuntimeError):
    """A PDF could not be safely read or exceeded configured limits."""


def chunk_text(text: str, *, chunk_chars: int = 1800, overlap: int = 200) -> list[str]:
    """Split text into bounded overlapping chunks without producing empty chunks."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        return []
    chunk_chars = int(chunk_chars)
    overlap = int(overlap)
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")
    if overlap < 0 or overlap >= chunk_chars:
        raise ValueError("overlap must be between 0 and chunk_chars - 1")

    normalized = text.replace("\x00", " ").strip()
    step = chunk_chars - overlap
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_chars, len(normalized))
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break
        start += step
    return chunks


def extract_pdf_text(
    pdf_path: str | Path,
    *,
    max_bytes: int = 50 * 1024 * 1024,
    max_pages: int = 100,
    max_chars: int = 500_000,
) -> dict[str, Any]:
    """Extract bounded text from a local PDF and report safe truncation state."""
    path = Path(pdf_path)
    if not path.is_file():
        raise PDFExtractionError("PDF file does not exist.")
    if path.stat().st_size <= 0:
        return {
            "status": "empty",
            "text": "",
            "pages_processed": 0,
            "total_pages": 0,
            "truncated": False,
            "warnings": ["PDF file is empty."],
        }
    if path.stat().st_size > int(max_bytes):
        raise PDFExtractionError("PDF file exceeds the extraction size limit.")
    if int(max_pages) <= 0 or int(max_chars) <= 0:
        raise ValueError("max_pages and max_chars must be positive")

    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")
            except Exception as exc:
                raise PDFExtractionError("Encrypted PDF cannot be read safely.") from exc
            if not decrypted:
                raise PDFExtractionError("Encrypted PDF cannot be read safely.")
    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError("PDF could not be opened or parsed.") from exc

    total_pages = len(reader.pages)
    page_limit = min(total_pages, int(max_pages))
    warnings: list[str] = []
    if total_pages > page_limit:
        warnings.append(f"Only the first {page_limit} pages were processed.")

    text_parts: list[str] = []
    truncated = False
    current_chars = 0
    for index in range(page_limit):
        try:
            page_text = reader.pages[index].extract_text() or ""
        except Exception:
            warnings.append(f"Page {index + 1} could not be extracted.")
            continue
        if not page_text.strip():
            continue
        remaining = int(max_chars) - current_chars
        if remaining <= 0:
            truncated = True
            break
        clean_text = page_text.replace("\x00", " ").strip()
        if len(clean_text) > remaining:
            clean_text = clean_text[:remaining]
            truncated = True
        text_parts.append(clean_text)
        current_chars += len(clean_text)
        if truncated:
            break

    text = "\n\n".join(text_parts).strip()
    if not text:
        warnings.append("No extractable text was found; the PDF may be scanned or image-only.")
        status = "empty"
    else:
        status = "truncated" if truncated else "ok"
    return {
        "status": status,
        "text": text,
        "pages_processed": page_limit,
        "total_pages": total_pages,
        "truncated": truncated,
        "warnings": warnings,
    }


def extract_and_chunk_pdf(
    pdf_path: str | Path,
    *,
    max_bytes: int = 50 * 1024 * 1024,
    max_pages: int = 100,
    max_chars: int = 500_000,
    chunk_chars: int = 1800,
    overlap: int = 200,
) -> dict[str, Any]:
    """Extract bounded PDF text and create reusable chunks without persistence."""
    extracted = extract_pdf_text(
        pdf_path,
        max_bytes=max_bytes,
        max_pages=max_pages,
        max_chars=max_chars,
    )
    extracted["chunks"] = chunk_text(extracted["text"], chunk_chars=chunk_chars, overlap=overlap)
    return extracted
