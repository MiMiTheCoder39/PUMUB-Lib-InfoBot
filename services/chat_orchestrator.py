"""Database-first orchestration for the PUMUB library chatbot.

The chatbot may use the configured LLM providers for intent extraction and for
wording answers from supplied library records, but it never uses a free-form
LLM answer for an unsupported question.
"""

from __future__ import annotations

from typing import Any

from models.book_model import get_book_by_id
from services.ai_service import answer_from_context, generate_response
from services.book_information_ai import answer_book_information, resolve_book_reference
from services.book_search_ai import search_from_question
from services.pdf_ai import answer_pdf_question, summarize_pdf
from utils.i18n import TRANSLATIONS
from utils.recommender import get_recommendations


def _language(language: str | None) -> str:
    return "en" if str(language or "my").lower().startswith("en") else "my"


def _is_myanmar(text: str) -> bool:
    return any("\u1000" <= char <= "\u109f" for char in text)


def detect_message_language(text: str) -> str:
    """Choose response language from the user's message, not UI settings.

    Any Myanmar Unicode text selects Myanmar. A message containing Latin
    letters but no Myanmar text selects English. Numbers/symbols alone default
    to Myanmar as requested by the library's UX rule.
    """
    if _is_myanmar(text):
        return "my"
    if any(("A" <= char <= "Z") or ("a" <= char <= "z") for char in text):
        return "en"
    return "my"


def _text(language: str, myanmar: str, english: str) -> str:
    return myanmar if _language(language) == "my" else english


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


def _recommendations(user_id: int, language: str) -> dict[str, Any]:
    rows = get_recommendations(user_id, top_n=8) or []
    books = [_public_book(row) for row in rows]
    return {
        "intent": "BOOK_RECOMMENDATION",
        "status": "ok" if books else "not_found",
        "answer": _text(
            language,
            "စာကြည့်တိုက်ထဲရှိ သင့် activity ကိုအခြေခံပြီး အကြံပြုထားသောစာအုပ်များ ဖြစ်ပါတယ်။"
            if books else
            "အကြံပြုရန် စာကြည့်တိုက် activity အချက်အလက် မလုံလောက်သေးပါ။",
            "Here are recommendations based only on your library activity."
            if books else
            "There is not enough library activity to recommend books yet.",
        ),
        "books": books,
    }


def _rules_answer(question: str, language: str) -> str | None:
    """Answer from the same bilingual rules dictionary used by the Rules page."""
    lowered = question.casefold()
    is_myanmar = _is_myanmar(question)
    rules_terms = (
        "rule", "rules", "library policy", "opening hours", "borrow limit",
        "ငှားရမ်းခွင့်", "စည်းကမ်း", "စာကြည့်ခန်း", "ဖွင့်ချိန်", "ဒဏ်ကြေး",
        "download စည်းကမ်း", "account စည်းကမ်း",
    )
    if not any(term in (question if is_myanmar else lowered) for term in rules_terms):
        return None

    catalog = TRANSLATIONS.get("my" if _language(language) == "my" else "en", {})
    selected: list[str] = []
    if any(term in lowered for term in ("hour", "open", "close")) or any(term in question for term in ("ဖွင့်ချိန်", "ပိတ်ချိန်")):
        selected += ["rules_hours_title", "rules_hours_weekdays", "rules_hours_closed"]
    if any(term in lowered for term in ("reading room", "silence", "phone", "smoking", "food")) or any(term in question for term in ("စာကြည့်ခန်း", "တိတ်တိတ်", "ဖုန်း", "ဆေးလိပ်", "စားသောက်")):
        selected += ["rules_reading_room_title", "rules_reading_room_silence", "rules_reading_room_phone", "rules_reading_room_food", "rules_reading_room_seating"]
    if any(term in lowered for term in ("borrow", "loan", "duration", "limit", "due date")) or any(term in question for term in ("ငှား", "ကာလ", "သတ်မှတ်ရက်", "due date")):
        selected += ["rules_borrowing_title", "rules_borrowing_student", "rules_borrowing_teacher", "rules_borrowing_duration", "rules_return_on_time"]
    if any(term in lowered for term in ("fine", "overdue", "late")) or any(term in question for term in ("ဒဏ်ကြေး", "နောက်ကျ")):
        selected += ["rules_fine_title", "rules_fine_amount", "rules_fine_teacher"]
    if any(term in lowered for term in ("download", "digital", "account", "bookmark", "password")) or any(term in question for term in ("download", "account", "bookmark", "password")):
        selected += ["rules_digital", "rules_download", "rules_account", "rules_responsibility"]
    if any(term in lowered for term in ("prohibited", "photocopy", "copy", "damage")) or any(term in question for term in ("မိတ္တူ", "ဖျက်ဆီး", "တားမြစ်")):
        selected += ["rules_conduct_damage", "rules_conduct_copy", "rules_prohibited"]

    # A broad “library rules” question gets the main rules categories.
    if not selected:
        selected = [
            "rules_official_source_title", "rules_hours_weekdays", "rules_hours_closed",
            "rules_borrow_limit", "rules_duration", "rules_fine", "rules_digital",
            "rules_account", "rules_prohibited", "rules_help",
        ]
    lines = [str(catalog[key]) for key in selected if catalog.get(key)]
    if not lines:
        return None
    return answer_from_context(
        question,
        [
            "AUTHORITATIVE LIBRARY RULES CONTEXT. Use these rules as the factual basis, "
            "but explain them naturally and do not add unsupported policy details.",
            *lines,
        ],
        max_output_tokens=500,
        system_prompt=(
            "You are LibInfoBot. Explain the supplied library rules naturally in a helpful conversational tone. "
            "Use only the supplied rules for policy facts. Keep the answer clear and concise: use 3-6 short sentences or bullet points, answer the user's exact question first, and avoid a long preamble. "
            + ("Respond in Myanmar language." if _language(language) == "my" else "Respond in English.")
        ),
    )


def _faq_answer(question: str, language: str) -> str | None:
    lowered = question.casefold()
    myanmar_terms = {
        "borrow": ("ငှား", "ငှားထား", "ငှားရမ်း", "ငှားလို့"),
        "return": ("ပြန်အပ်", "ပြန်ပေး", "စာအုပ်အပ်"),
        "fine": ("ဒဏ်ကြေး", "အကြွေး", "fine"),
        "hours": ("ဖွင့်ချိန်", "ပိတ်ချိန်", "ဘယ်အချိန်", "ဖွင့်လဲ"),
        "contact": ("ဆက်သွယ်", "ဖုန်း", "အီးမေးလ်", "email"),
    }
    english_terms = {
        "borrow": ("borrow", "loan", "checkout"),
        "return": ("return", "returned"),
        "fine": ("fine", "penalty", "clearance"),
        "hours": ("hour", "open", "close"),
        "contact": ("contact", "email", "phone"),
    }
    answers = {
        "borrow": _text(language, "စာအုပ်ငှားရန် စာအုပ်အသေးစိတ်စာမျက်နှာမှ request လုပ်ပါ။ အတည်ပြုခြင်းနှင့် return မှတ်တမ်းများကို Library staff က စီမံပါသည်။", "You can request a book from its details page. Library staff approve, issue, and record returns."),
        "return": _text(language, "ငှားထားသောစာအုပ်ကို သတ်မှတ်ထားသော due date မတိုင်မီ ပြန်အပ်ပါ။ My Borrowings မှာ အခြေအနေကိုကြည့်နိုင်ပါတယ်။", "Return borrowed books by the configured due date. You can check the status from My Borrowings."),
        "fine": _text(language, "လက်ရှိ fine နှင့် clearance အခြေအနေကို account menu ထဲက Fines မှာကြည့်နိုင်ပါတယ်။ ပမာဏက Library database မှလာပါတယ်။", "You can view current fines and clearance status from the Fines page. Amounts come from the library database."),
        "hours": _text(language, "လက်ရှိစာကြည့်တိုက်ဖွင့်ချိန်ကို နောက်ဆုံး announcement သို့မဟုတ် Library desk မှာ စစ်ဆေးပါ။", "Please check the latest library announcement or contact the library desk for current opening hours."),
        "contact": _text(language, "Library desk သို့မဟုတ် library@pumub.edu.mm ကို ဆက်သွယ်နိုင်ပါတယ်။", "You can contact the library desk or library@pumub.edu.mm."),
    }
    for key, terms in english_terms.items():
        if any(term in lowered for term in terms):
            return answers[key]
    for key, terms in myanmar_terms.items():
        if any(term in question for term in terms):
            return answers[key]
    return None


def _is_greeting(question: str) -> bool:
    lowered = question.casefold().strip()
    return lowered in {"hi", "hello", "hey", "မင်္ဂလာပါ", "ဟယ်လို", "မင်္ဂလာပါ bot"}


def _is_book_search(question: str) -> bool:
    lowered = question.casefold()
    english = ("book", "books", "find", "search", "available", "how many books", "show me")
    myanmar = ("စာအုပ်", "စာအုပ်တွေ", "ရှာပေး", "ရှိလား", "ရှိမရှိ", "ဘာတွေရှိ")
    return any(term in lowered for term in english) or any(term in question for term in myanmar)


def _is_book_information(question: str) -> bool:
    lowered = question.casefold()
    english = ("who wrote", "author", "isbn", "book information", "about this book", "details of")
    myanmar = ("ရေးထားလဲ", "စာရေးသူ", "စာရေးဆရာ", "isbn", "အကြောင်းပြော", "အကြောင်းသိချင်")
    return any(term in lowered for term in english) or any(term in question for term in myanmar)


def _is_summary_request(question: str) -> bool:
    lowered = question.casefold()
    english = ("summarize", "summarise", "summary", "give me an overview", "main ideas")
    myanmar = ("အကျဉ်းချုပ်", "အနှစ်ချုပ်", "ချုပ်ပေး", "အဓိကအချက်")
    return any(term in lowered for term in english) or any(term in question for term in myanmar)


def _is_recommendation(question: str) -> bool:
    lowered = question.casefold()
    english = ("recommend", "suggest", "suggestion", "what should i read", "similar book", "similar books")
    myanmar = ("အကြံပြု", "ညွှန်း", "ဆင်တူ", "ဖတ်ရမယ့်")
    return any(term in lowered for term in english) or any(term in question for term in myanmar)


def _out_of_scope(language: str) -> dict[str, Any]:
    return {
        "intent": "OUT_OF_SCOPE",
        "status": "not_available",
        "answer": _text(
            language,
            "ဒီမေးခွန်းအတွက် လက်ရှိ Library database/knowledge base ထဲမှာ အတည်ပြုနိုင်တဲ့အချက်အလက် မတွေ့ပါဘူး။ စာအုပ်အမည်၊ စာရေးသူ၊ ISBN သို့မဟုတ် Library service အကြောင်း မေးမြန်းနိုင်ပါတယ်။",
            "I cannot verify that from the current library database or knowledge base. Please ask about a book title, author, ISBN, or a library service.",
        ),
        "books": [],
    }


def handle_chat(
    question: str,
    *,
    user_id: int,
    role: str | None,
    book_id: int | None = None,
    action: str | None = None,
    mode: str = "medium",
    language: str = "my",
) -> dict[str, Any]:
    language = detect_message_language(question)
    if action == "pdf_summary":
        if book_id is None:
            raise ValueError("Select a book before requesting a PDF summary.")
        return {"intent": "PDF_SUMMARY", **summarize_pdf(book_id, role, mode, language=language)}
    if action == "pdf_question":
        if book_id is None:
            raise ValueError("Select a book before asking a PDF question.")
        return {"intent": "PDF_QA", **answer_pdf_question(book_id, role, question, language=language)}
    if action == "book_information" or book_id is not None:
        return answer_book_information(question, book_id=book_id, role=role, language=language)

    if _is_greeting(question):
        return {
            "intent": "GREETING",
            "status": "ok",
            "answer": _text(language, "မင်္ဂလာပါ။ PUMUB Library ထဲရှိ စာအုပ်များနှင့် Library service များကို ကူညီရှာဖွေပေးနိုင်ပါတယ်။", "Hello. I can help you search books and library services available in PUMUB Library."),
            "books": [],
        }
    rules = _rules_answer(question, language)
    if rules:
        return {"intent": "LIBRARY_RULES", "status": "ok", "answer": rules, "books": []}
    if _is_summary_request(question):
        book, matches = resolve_book_reference(question)
        if book is None and matches:
            titles = ", ".join(str(item.get("title") or "") for item in matches[:5])
            return {
                "intent": "PDF_SUMMARY",
                "status": "ambiguous",
                "answer": _text(
                    language,
                    f"စာအုပ်တစ်အုပ်ထက်ပိုပြီး ကိုက်ညီနေပါတယ်။ ဘယ်စာအုပ်ကို အကျဉ်းချုပ်ပေးရမလဲ ရွေးပြောပါ — {titles}",
                    f"More than one library book matched. Please specify which book to summarize: {titles}",
                ),
                "books": [_public_book(item) for item in matches[:5]],
            }
        if book is None:
            return {
                "intent": "PDF_SUMMARY",
                "status": "needs_book",
                "answer": _text(
                    language,
                    "အကျဉ်းချုပ်ပေးရန် စာအုပ်အမည် သို့မဟုတ် ISBN ကို ပြောပေးပါ။",
                    "Please provide the book title or ISBN you want me to summarize.",
                ),
                "books": [],
            }
        return {"intent": "PDF_SUMMARY", **summarize_pdf(book["book_id"], role, mode, language=language)}
    if _is_recommendation(question):
        return _recommendations(user_id, language)
    faq = _faq_answer(question, language)
    if faq:
        return {"intent": "LIBRARY_FAQ", "status": "ok", "answer": faq, "books": []}
    if _is_book_information(question):
        return answer_book_information(question, book_id=None, role=role, language=language)
    if _is_book_search(question):
        return search_from_question(question, language=language)

    # General conversation is intentionally allowed. The response language is
    # still selected from the user's message, while library-search intents use
    # the database-backed services above.
    return {
        "intent": "GENERAL_LIBRARY_CHAT",
        "status": "ok",
        "answer": generate_response(
            question,
            system_prompt=(
                "You are LibInfoBot, a helpful digital-library assistant. "
                "Answer naturally and accurately, without pretending to have "
                "live library facts that were not supplied. Keep the answer clear and concise: use 3-6 short sentences or bullet points, answer the exact question first, and do not write a long essay unless the user asks for detail. "
                + ("Respond in Myanmar language." if language == "my" else "Respond in English.")
            ),
            max_output_tokens=700,
        ),
        "books": [],
    }
