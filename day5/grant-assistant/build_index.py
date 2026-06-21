"""
build_index.py — построение FAISS-индекса из собранных страниц.

Читает data/pages.jsonl, режет тексты на чанки, считает эмбеддинги
(sentence-transformers) и сохраняет индекс + метаданные в data/index/.

Запускать после scrape.py:
    python scrape.py
    python build_index.py
"""

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).parent / "data"
PAGES_FILE = DATA_DIR / "pages.json"
INDEX_DIR = DATA_DIR / "index"
INDEX_FILE = INDEX_DIR / "faiss.index"
META_FILE = INDEX_DIR / "meta.json"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 800       # символов в чанке
CHUNK_OVERLAP = 150    # перекрытие между чанками


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Разбивает текст на перекрывающиеся куски."""
    text = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def load_documents() -> list[dict]:
    if not PAGES_FILE.exists():
        raise FileNotFoundError(
            f"Нет файла {PAGES_FILE}. Сначала запустите: python scrape.py"
        )
    return json.loads(PAGES_FILE.read_text(encoding="utf-8"))


def main() -> None:
    docs = load_documents()
    print(f"[index] документов: {len(docs)}")

    records = []  # метаданные по каждому чанку
    for doc in docs:
        for chunk in chunk_text(doc["text"]):
            records.append({
                "url": doc["url"],
                "lang": doc.get("lang", "unknown"),
                "title": doc["title"],
                "text": chunk,
            })
    print(f"[index] чанков: {len(records)}")
    if not records:
        raise SystemExit("[index] нет данных для индексации.")

    print(f"[index] загрузка модели эмбеддингов: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(
        [r["text"] for r in records],
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # косинус через нормализованные векторы
    index.add(embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    # faiss.write_index не открывает пути с не-ASCII символами на Windows
    # (напр. C:\Users\Админ\...). Сериализуем в байты и пишем через Python.
    INDEX_FILE.write_bytes(faiss.serialize_index(index).tobytes())
    META_FILE.write_text(
        json.dumps({"model": MODEL_NAME, "records": records}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[index] готово. Сохранено в {INDEX_DIR} (векторов: {index.ntotal})")


if __name__ == "__main__":
    main()
