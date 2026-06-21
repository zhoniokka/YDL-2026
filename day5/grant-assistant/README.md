# Grant Assistant — ИИ-помощник по грантам фонда Есенова

RAG-приложение: собирает материалы фонда, строит поисковый индекс и
отвечает на вопросы о грантах с помощью модели **Gemma**. Если ответа в базе
нет — вопрос можно переслать администратору фонда по почте (MailerSend).

## Структура проекта

```
grant-assistant/
├── app.py            # веб-интерфейс (Streamlit)
├── scrape.py         # сбор страниц фонда -> data/pages.jsonl
├── build_index.py    # построение FAISS-индекса -> data/index/
├── rag.py            # поиск по индексу + генерация ответа
├── gemma_client.py   # обёртка над API Gemma
├── email_utils.py    # отправка писем через MailerSend
├── eval.py           # простая оценка качества ответов
├── data/             # данные (индекс и .env в git не попадают)
├── requirements.txt
├── .env.example      # шаблон переменных окружения
└── .gitignore
```

## Шаги запуска

### 1. Виртуальное окружение и зависимости

```bash
python -m venv venv
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Переменные окружения

Скопируйте шаблон и заполните своими значениями:

```bash
# Windows (PowerShell):
copy .env.example .env
# macOS / Linux:
cp .env.example .env
```

Затем **вручную** впишите в `.env` свои значения:

| Переменная           | Что вписать                                                        |
|----------------------|-------------------------------------------------------------------|
| `GEMMA_API_KEY`      | Ключ API Gemma (Google AI Studio).                                |
| `MAILERSEND_API_KEY` | API-токен из личного кабинета MailerSend.                         |
| `ADMIN_EMAIL`        | Почта администратора фонда — туда уходят пересланные вопросы.     |
| `SENDER_EMAIL`       | Адрес отправителя, подтверждённый (verified) в MailerSend.        |

> Файлы `.env` и `.streamlit/secrets.toml` перечислены в `.gitignore`
> и **никогда** не попадают в репозиторий.

### 3. Сбор данных и построение индекса

По желанию укажите свои URL в `data/seeds.txt` (по одному в строке).

```bash
python scrape.py        # -> data/pages.jsonl
python build_index.py   # -> data/index/ (faiss.index + meta.json)
```

### 4. Запуск приложения

```bash
streamlit run app.py
```

### 5. Проверка качества (опционально)

```bash
python eval.py
```

## Замечания по безопасности

- Реальные ключи хранятся только в локальном `.env` (вне git).
- В коммиты попадает лишь шаблон `.env.example` с пустыми плейсхолдерами.
- Папка `data/index/` генерируется локально и тоже игнорируется git.
