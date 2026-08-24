"""
utils/recommender.py
-----------------------
Book Recommendation System
--------------------------
Algorithm: Content-Based Filtering
- Book ရဲ့ title + category + author + description တွေကို
  TF-IDF Vector အဖြစ် ပြောင်းပြီး Cosine Similarity နှိုင်းယှဉ်သည်။
- User ဖတ်ထားတဲ့ / download လုပ်ထားတဲ့ books တွေကို အခြေခံပြီး
  ဆင်တူသော books တွေ recommend ပေးသည်။

Fallback: scikit-learn မရှိရင် popular books ပြသည်။
"""

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    np = None
    TfidfVectorizer = None
    cosine_similarity = None
    SKLEARN_AVAILABLE = False

from models.db import mysql


def _get_all_books_for_recommend():
    """Recommendation အတွက် books အားလုံး fetch (content fields ပါ)."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.book_id, b.title, b.description,
               COALESCE(a.author_name,'') AS author_name,
               COALESCE(c.category_name,'') AS category_name,
               b.cover_image, b.download_count
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.author_id
        LEFT JOIN categories c ON b.category_id = c.category_id
        WHERE COALESCE(b.is_archived, 0) = 0
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


def _get_user_read_book_ids(user_id):
    """User ဖတ်ဖူးတဲ့ book id list."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT DISTINCT book_id FROM read_history WHERE user_id = %s
        UNION
        SELECT DISTINCT book_id FROM downloads WHERE user_id = %s
        UNION
        SELECT DISTINCT book_id FROM bookmarks WHERE user_id = %s
    """, (user_id, user_id, user_id))
    rows = cur.fetchall()
    cur.close()
    return [r["book_id"] for r in rows]


def get_recommendations(user_id, top_n=8):
    """
    User အတွက် recommended books list ပြန်ပေးသည်။
    User history မရှိရင် popular books ပြသည်။
    sklearn မရှိရင် popular books ပြသည်။
    """
    all_books = _get_all_books_for_recommend()

    if not all_books:
        return []

    user_book_ids = _get_user_read_book_ids(user_id)

    # History မရှိရင် popular books ပြ
    if not user_book_ids:
        sorted_books = sorted(all_books, key=lambda x: x["download_count"], reverse=True)
        return [b for b in sorted_books[:top_n]]

    if not SKLEARN_AVAILABLE:
        # Fallback: category match လုပ်ပြီး popular order
        user_ids_set = set(user_book_ids)
        return [b for b in sorted(all_books,
                key=lambda x: x["download_count"], reverse=True)
                if b["book_id"] not in user_ids_set][:top_n]

    # ── TF-IDF Cosine Similarity ──────────────────────────────
    # Content string တည်ဆောက်ပါ
    book_ids = [b["book_id"] for b in all_books]
    contents = []
    for b in all_books:
        text = " ".join(filter(None, [
            b["title"] or "",
            b["category_name"] or "",
            b["author_name"] or "",
            (b["description"] or "")[:200],
        ]))
        contents.append(text)

    # TF-IDF matrix
    vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
    try:
        tfidf_matrix = vectorizer.fit_transform(contents)
    except Exception:
        return [b for b in sorted(all_books,
                key=lambda x: x["download_count"], reverse=True)
                if b["book_id"] not in set(user_book_ids)][:top_n]

    # User ဖတ်ထားတဲ့ books ရဲ့ index တွေ ရှာ
    user_indices = [i for i, bid in enumerate(book_ids) if bid in set(user_book_ids)]

    if not user_indices:
        return [b for b in all_books[:top_n]]

    # User profile vector = user ဖတ်ထားတဲ့ books ရဲ့ average TF-IDF
    user_vector = np.asarray(tfidf_matrix[user_indices].mean(axis=0))

    # Cosine similarity တွက်
    sim_scores = cosine_similarity(user_vector, tfidf_matrix)[0]

    # User ဖတ်ဖူးတဲ့ book တွေ exclude လုပ်ပြီး top N ရွေး
    scored = [
        (i, score) for i, score in enumerate(sim_scores)
        if book_ids[i] not in set(user_book_ids)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    recommended = [all_books[i] for i, _ in scored[:top_n]]
    return recommended