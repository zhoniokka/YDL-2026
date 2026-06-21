"""
rag.py — поиск по индексу (retrieval) и сборка ответа (generation).

Загружает FAISS-индекс из data/index/, ищет релевантные чанки, и при
достаточной релевантности формирует ответ через Gemma. Если данных нет —
возвращает официальный отказ на языке вопроса, не обращаясь к модели.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

import gemma_client

DATA_DIR = Path(__file__).parent / "data"
INDEX_DIR = DATA_DIR / "index"
INDEX_FILE = INDEX_DIR / "faiss.index"
META_FILE = INDEX_DIR / "meta.json"

# Сколько чанков доставать из индекса.
TOP_K = 4

# Порог релевантности (косинусная близость, [-1..1]).
# Если лучший score ниже — модель не вызывается, отдаём официальный отказ.
# Вынесен в константу, чтобы подстраивать на тестах.
SCORE_THRESHOLD = 0.35


# --- Загрузка индекса -------------------------------------------------------

@lru_cache(maxsize=1)
def _load():
    """Лениво загружает индекс, метаданные и модель эмбеддингов (один раз)."""
    if not INDEX_FILE.exists() or not META_FILE.exists():
        raise FileNotFoundError(
            "Индекс не найден. Запустите: python scrape.py && python build_index.py"
        )
    # faiss.read_index не открывает пути с не-ASCII символами на Windows —
    # читаем байты через Python и десериализуем из памяти.
    raw = np.frombuffer(INDEX_FILE.read_bytes(), dtype="uint8")
    index = faiss.deserialize_index(raw)
    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    model = SentenceTransformer(meta["model"])
    return index, meta["records"], model


def load_resources():
    """Публичная точка прогрева тяжёлых ресурсов (индекс + модель эмбеддингов).

    Удобно обернуть в @st.cache_resource, чтобы загрузить один раз.
    """
    return _load()


# --- Определение языка вопроса ----------------------------------------------

# Буквы, специфичные для казахского алфавита.
_KAZAKH_CHARS = set("әғқңөұүһі")


def detect_lang(text: str) -> str:
    """Определяет язык вопроса: kk / ru / en. По умолчанию ru."""
    low = text.lower()
    if any(ch in _KAZAKH_CHARS for ch in low):
        return "kk"
    if re.search(r"[а-яё]", low):
        return "ru"
    if re.search(r"[a-z]", low):
        return "en"
    return "ru"


# --- Поиск ------------------------------------------------------------------

def search(question: str, top_k: int = TOP_K) -> list[dict]:
    """Возвращает top_k релевантных чанков с полем score (по убыванию)."""
    index, records, model = _load()
    vec = model.encode(
        [question], convert_to_numpy=True, normalize_embeddings=True
    ).astype(np.float32)
    scores, idx = index.search(vec, top_k)

    hits = []
    for score, i in zip(scores[0], idx[0]):
        if i < 0:
            continue
        rec = dict(records[i])
        rec["score"] = float(score)
        hits.append(rec)
    return hits


def _build_context(hits: list[dict]) -> str:
    """Склеивает найденные чанки в нумерованный контекст для модели."""
    blocks = []
    for n, h in enumerate(hits, 1):
        blocks.append(f"[Источник {n}] {h['title']} ({h['url']})\n{h['text']}")
    return "\n\n".join(blocks)


# --- Главная функция RAG ----------------------------------------------------

def answer(question: str, lang: str | None = None) -> dict:
    """
    Полный RAG-цикл.

    lang — язык ответа (kk/ru/en). Если не передан, определяется автоматически.
    Возвращает {"answer": str, "sources": list[str]}.
    sources — список url использованных чанков; при официальном отказе пуст.
    """
    lang = lang or detect_lang(question)
    refusal = gemma_client.refusal_text(lang)

    hits = search(question)

    # Нет результатов или лучший score ниже порога — модель НЕ вызываем.
    if not hits or hits[0]["score"] < SCORE_THRESHOLD:
        return {"answer": refusal, "sources": []}

    context = _build_context(hits)

    lang_names = {"kk": "казахском (қазақша)", "ru": "русском", "en": "английском (English)"}
    system = (
        "Ты — официальный ИИ-помощник по грантам и программам фонда Есенова.\n"
        "СТРОГИЕ ПРАВИЛА:\n"
        "1. Отвечай ТОЛЬКО на основе приведённого ниже текста (чанков). "
        "Не используй внешние знания.\n"
        "2. НИКОГДА не выдумывай даты, суммы, дедлайны, требования и условия. "
        "Если конкретного факта нет в тексте — не сообщай его.\n"
        f"3. Отвечай на том же языке, что и вопрос — на {lang_names.get(lang, 'русском')}.\n"
        "4. Если ответа на вопрос в приведённом тексте НЕТ, верни СЛОВО В СЛОВО "
        "следующий официальный отказ, ничего в нём не меняя (особенно контакты):\n"
        f"<<<{refusal}>>>\n"
        "Выводи только сам текст отказа, без кавычек и угловых скобок."
    )
    user = (
        f"Текст (чанки):\n{context}\n\n"
        f"Вопрос: {question}\n\n"
        "Ответь, строго соблюдая правила выше."
    )

    reply = gemma_client.ask_gemma(system, user, temperature=0.0)

    # Если модель вернула официальный отказ — источники не показываем.
    if _is_refusal(reply, refusal):
        return {"answer": refusal, "sources": []}

    # Уникальные url использованных чанков, в порядке релевантности.
    sources, seen = [], set()
    for h in hits:
        if h["url"] not in seen:
            sources.append(h["url"])
            seen.add(h["url"])

    return {"answer": reply, "sources": sources}


def _is_refusal(reply: str, refusal: str) -> bool:
    """Грубое сравнение: модель вернула официальный отказ?"""
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip().strip("<>«»\"' ").lower()

    return norm(reply) == norm(refusal)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "Какие гранты предлагает фонд Есенова?"
    result = answer(q)
    print(f"\n[lang={detect_lang(q)}]")
    print("Ответ:\n", result["answer"])
    print("\nИсточники:", result["sources"])
