"""
gemma_client.py — обёртка над Gemma API (OpenAI-совместимый эндпоинт).

Вызов: POST {GEMMA_BASE_URL}/chat/completions с заголовком
Authorization: Bearer <GEMMA_API_KEY>, тело — список messages[].
Ключ и базовый URL берутся из окружения через python-dotenv и НИКОГДА
не хардкодятся.

Главная функция: ask_gemma(system, user, temperature=0.0).
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

GEMMA_API_KEY = os.getenv("GEMMA_API_KEY", "")
# Базовый URL OpenAI-совместимого API, БЕЗ хвостового /chat/completions.
# Например: https://openrouter.ai/api/v1  или  http://localhost:1234/v1
GEMMA_BASE_URL = os.getenv("GEMMA_BASE_URL", "").rstrip("/")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4")
TIMEOUT = 60


# --- Официальный отказ на трёх языках ---------------------------------------
# Смысл один и тот же, контакты во всех версиях идентичны.
REFUSAL = {
    "ru": (
        "К сожалению, точной информации по этому вопросу у меня нет. Пожалуйста, "
        "уточните на сайте фонда (yessenovfoundation.org, раздел «Программы») или "
        "свяжитесь с фондом напрямую: телефон +7 (771) 759-59-44, эл. почта "
        "info@yessenovfoundation.org."
    ),
    "kk": (
        "Өкінішке орай, бұл сұрақ бойынша менде нақты ақпарат жоқ. Қордың сайтынан "
        "тексеріңіз (yessenovfoundation.org, «Бағдарламалар» бөлімі) немесе қормен "
        "тікелей байланысыңыз: телефон +7 (771) 759-59-44, электрондық пошта "
        "info@yessenovfoundation.org."
    ),
    "en": (
        "Unfortunately, I don't have exact information on this question. Please check "
        "the foundation's website (yessenovfoundation.org, the “Programs” section) or "
        "contact the foundation directly: phone +7 (771) 759-59-44, email "
        "info@yessenovfoundation.org."
    ),
}


def refusal_text(lang: str) -> str:
    """Возвращает официальный отказ на нужном языке (по умолчанию ru)."""
    return REFUSAL.get(lang, REFUSAL["ru"])


def ask_gemma(system: str, user: str, temperature: float = 0.0) -> str:
    """Отправляет запрос в Gemma (OpenAI chat/completions) и возвращает текст."""
    if not GEMMA_API_KEY:
        return (
            "[Ошибка] Не задан GEMMA_API_KEY. "
            "Скопируйте .env.example в .env и впишите ключ."
        )
    if not GEMMA_BASE_URL:
        return (
            "[Ошибка] Не задан GEMMA_BASE_URL (базовый URL OpenAI-совместимого API). "
            "Впишите его в .env, например: GEMMA_BASE_URL=https://openrouter.ai/api/v1"
        )

    url = f"{GEMMA_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GEMMA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GEMMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": 1024,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.RequestException as exc:
        return f"[Ошибка обращения к Gemma] {exc}"
    except (KeyError, IndexError):
        return "[Ошибка] Не удалось разобрать ответ модели Gemma."


if __name__ == "__main__":
    print(ask_gemma("Ты помощник.", "Скажи привет одним предложением."))
