"""
email_utils.py — отправка писем через MailerSend (SDK v2.x).

Ключи и адреса берутся ТОЛЬКО из .env (python-dotenv), ничего не хардкодим.
Отправитель (SENDER_EMAIL) должен быть на подтверждённом домене,
например info@app.commit.kz.
"""

import os

from dotenv import load_dotenv
from mailersend import EmailBuilder, MailerSendClient


def _config() -> tuple[str, str, str]:
    """Читает переменные окружения СВЕЖИМИ при каждом вызове.

    override=True — чтобы правки в .env подхватывались без перезапуска процесса
    (например, между нажатиями кнопки в Streamlit).
    Возвращает (api_key, sender_email, admin_email).
    """
    load_dotenv(override=True)
    return (
        os.getenv("MAILERSEND_API_KEY", ""),
        os.getenv("SENDER_EMAIL", ""),
        os.getenv("ADMIN_EMAIL", ""),
    )


def _send(subject: str, text: str) -> str:
    """
    Низкоуровневая отправка письма на ADMIN_EMAIL через MailerSend.
    Возвращает message_id. Бросает исключение при ошибке/неполной конфигурации.
    """
    api_key, sender, admin = _config()
    missing = [n for n, v in {
        "MAILERSEND_API_KEY": api_key,
        "SENDER_EMAIL": sender,
        "ADMIN_EMAIL": admin,
    }.items() if not v]
    if missing:
        raise RuntimeError("Не заданы переменные окружения: " + ", ".join(missing))

    client = MailerSendClient(api_key=api_key)
    email = (
        EmailBuilder()
        .from_email(sender, "Grant Assistant")
        .to(admin)
        .subject(subject)
        .text(text)
        .build()
    )
    response = client.emails.send(email)

    # message_id приходит в заголовке x-message-id.
    headers = getattr(response, "headers", None) or {}
    message_id = headers.get("x-message-id") or getattr(response, "request_id", None)
    return message_id or "(отправлено, message_id недоступен)"


def send_consultation(
    name: str, contact: str, topic: str = "", message: str = ""
) -> str:
    """
    Отправляет заявку на консультацию на ADMIN_EMAIL.
    Возвращает message_id. Бросает исключение при ошибке/неполной конфигурации.
    """
    body = (
        "Новая заявка на консультацию из чата помощника по грантам.\n\n"
        f"Имя:        {name}\n"
        f"Контакт:    {contact}\n"
        f"Программа/тема: {topic or '—'}\n"
        f"Сообщение:\n{message or '—'}\n"
    )
    return _send("Заявка на консультацию из чата помощника", body)


def forward_question(question: str, context: str = "") -> dict:
    """
    Пересылает вопрос пользователя администратору фонда.
    Возвращает {"ok": bool, "detail": str} (не бросает исключений).
    """
    body = (
        "Пользователь задал вопрос, на который помощник не нашёл ответ.\n\n"
        f"Вопрос:\n{question}\n\n"
        f"Контекст из базы:\n{context or '(пусто)'}"
    )
    try:
        mid = _send("Новый вопрос по грантам (нет ответа в базе)", body)
        return {"ok": True, "detail": mid}
    except Exception as exc:  # noqa: BLE001 — причину показываем вызывающему коду
        return {"ok": False, "detail": str(exc)}


if __name__ == "__main__":
    # Самотест: отправит заявку на ADMIN_EMAIL (нужны переменные в .env).
    try:
        print("message_id:", send_consultation(
            "Тест", "test@example.com", "Yessenov Data Lab", "Это тестовая заявка."
        ))
    except Exception as exc:  # noqa: BLE001
        print("Ошибка:", exc)
