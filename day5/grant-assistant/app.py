"""
app.py — Streamlit-чат трёхъязычного помощника по грантам фонда Есенова.

Оформление в стиле Yessenov Foundation: широкий макет, фирменная тема
(.streamlit/config.toml), сайдбар с логотипом, инфо о фонде и формой
записи на консультацию.

Запуск:
    streamlit run app.py
"""

from pathlib import Path

import streamlit as st

import rag
import email_utils

# set_page_config должен идти первым вызовом Streamlit.
st.set_page_config(
    page_title="Grant Assistant — фонд Есенова",
    page_icon="🎓",
    layout="wide",
)

# Акцентный цвет дублирует primaryColor из .streamlit/config.toml.
ACCENT = "#0B3D91"

# Лёгкий фирменный акцент: цвет заголовка и скруглённые «пузыри» сообщений.
st.markdown(
    f"""
    <style>
      h1 {{ color: {ACCENT}; }}
      [data-testid="stChatMessage"] {{
          border-radius: 14px;
          padding: 0.6rem 0.9rem;
          margin-bottom: 0.3rem;
      }}
      [data-testid="stSidebar"] img {{ border-radius: 8px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Тяжёлые ресурсы: загружаем один раз -----------------------------------

@st.cache_resource(show_spinner="Загружаю модель и индекс…")
def get_resources():
    """Прогрев индекса и модели эмбеддингов (один раз на сессию приложения)."""
    return rag.load_resources()


# --- Логотип (локально, с откатом на URL) -----------------------------------

LOGO_PATH = Path(__file__).parent / "assets" / "logo-yessenov.jpg"
LOGO_URL = (
    "https://yessenovfoundation.org/wp-content/uploads/2025/02/"
    "logo-yessenov-foundation-2025.jpg"
)
LOGO_SRC = str(LOGO_PATH) if LOGO_PATH.exists() else LOGO_URL


# --- Локализация интерфейса -------------------------------------------------

LANG_OPTIONS = {"Қаз": "kk", "Рус": "ru", "Eng": "en"}

UI = {
    "kk": {
        "title": "🎓 Есенов қорының гранттары бойынша көмекші",
        "intro": "Қор гранттары, бағдарламалары мен өтінімдер туралы сұрақ қойыңыз.",
        "examples_label": "Сұрақ үлгілері:",
        "examples": [
            "Қор қандай гранттар ұсынады?",
            "Грантқа қалай өтінім беруге болады?",
            "Yessenov Data Lab 2026 деген не?",
        ],
        "input_placeholder": "Сұрағыңызды жазыңыз…",
        "spinner": "Жауап іздеп жатырмын…",
        "sources_label": "Дереккөздер",
        "about_title": "Қор туралы",
        "about": (
            "Шахмардан Есенов қоры Қазақстанның зияткерлік әлеуетін дамытады. "
            "Қор дарынды студенттерді, жас ғалымдарды және ғылым мен технология "
            "саласындағы білім беру бағдарламаларын қолдайды."
        ),
        "form_title": "Кеңеске жазылу",
        "name_label": "Аты-жөні *",
        "contact_label": "Email немесе телефон *",
        "topic_label": "Қызықтыратын бағдарлама/тақырып",
        "message_label": "Хабарлама / сұрақ",
        "submit_label": "Өтінім жіберу",
        "err_required": "Атыңызды және кемінде бір байланыс (email немесе телефон) жазыңыз.",
        "sending": "Өтінім жіберілуде…",
        "sent_ok": "Өтінім жіберілді! Қор сізбен байланысады.",
        "sent_err": "Өтінімді жіберу мүмкін болмады:",
    },
    "ru": {
        "title": "🎓 Помощник по грантам фонда Есенова",
        "intro": "Задайте вопрос о грантах, программах и заявках фонда.",
        "examples_label": "Примеры вопросов:",
        "examples": [
            "Какие гранты предлагает фонд?",
            "Как подать заявку на грант?",
            "Что такое Yessenov Data Lab 2026?",
        ],
        "input_placeholder": "Напишите ваш вопрос…",
        "spinner": "Ищу ответ…",
        "sources_label": "Источники",
        "about_title": "О фонде",
        "about": (
            "Фонд Шахмардана Есенова развивает интеллектуальный потенциал "
            "Казахстана. Поддерживает талантливых студентов, молодых учёных и "
            "образовательные программы в области науки и технологий."
        ),
        "form_title": "Записаться на консультацию",
        "name_label": "Имя *",
        "contact_label": "Email или телефон *",
        "topic_label": "Интересующая программа/тема",
        "message_label": "Сообщение / вопрос",
        "submit_label": "Отправить заявку",
        "err_required": "Заполните имя и хотя бы один контакт (email или телефон).",
        "sending": "Отправляю заявку…",
        "sent_ok": "Заявка отправлена! Фонд свяжется с вами.",
        "sent_err": "Не удалось отправить заявку:",
    },
    "en": {
        "title": "🎓 Yessenov Foundation Grants Assistant",
        "intro": "Ask about the foundation's grants, programs and applications.",
        "examples_label": "Example questions:",
        "examples": [
            "What grants does the foundation offer?",
            "How do I apply for a grant?",
            "What is Yessenov Data Lab 2026?",
        ],
        "input_placeholder": "Type your question…",
        "spinner": "Looking for an answer…",
        "sources_label": "Sources",
        "about_title": "About the foundation",
        "about": (
            "The Shakhmardan Yessenov Foundation develops Kazakhstan's "
            "intellectual potential. It supports talented students, young "
            "scientists and educational programs in science and technology."
        ),
        "form_title": "Book a consultation",
        "name_label": "Name *",
        "contact_label": "Email or phone *",
        "topic_label": "Program/topic of interest",
        "message_label": "Message / question",
        "submit_label": "Submit request",
        "err_required": "Please enter your name and at least one contact (email or phone).",
        "sending": "Sending your request…",
        "sent_ok": "Request sent! The foundation will contact you.",
        "sent_err": "Could not send the request:",
    },
}


# --- Состояние --------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content, sources}]


# --- Сайдбар ----------------------------------------------------------------

with st.sidebar:
    # 1. Переключатель языка.
    labels = list(LANG_OPTIONS.keys())
    choice = st.radio(
        "Тіл / Язык / Language",
        labels,
        index=labels.index("Рус"),  # по умолчанию ru
        horizontal=True,
    )
    lang = LANG_OPTIONS[choice]
    t = UI[lang]

    # 2. Логотип и краткая инфо о фонде на выбранном языке.
    st.image(LOGO_SRC, use_container_width=True)
    st.markdown(f"**{t['about_title']}**")
    st.caption(t["about"])

    # 3. Форма записи на консультацию (в expander, чтобы не загромождать).
    with st.expander(t["form_title"]):
        with st.form("consultation_form", clear_on_submit=True):
            f_name = st.text_input(t["name_label"])
            f_contact = st.text_input(t["contact_label"])
            f_topic = st.text_input(t["topic_label"])
            f_message = st.text_area(t["message_label"])
            submitted = st.form_submit_button(t["submit_label"])

        # Обработка строго по submit формы — никаких авто-отправок.
        if submitted:
            if not f_name.strip() or not f_contact.strip():
                st.error(t["err_required"])
            else:
                try:
                    with st.spinner(t["sending"]):
                        message_id = email_utils.send_consultation(
                            f_name.strip(),
                            f_contact.strip(),
                            f_topic.strip(),
                            f_message.strip(),
                        )
                    st.success(f"{t['sent_ok']} (id: {message_id})")
                except Exception as exc:  # noqa: BLE001 — показываем причину
                    st.error(f"{t['sent_err']} {exc}")


# Прогрев ресурсов (покажет FileNotFoundError понятным сообщением).
try:
    get_resources()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()


# --- Шапка ------------------------------------------------------------------

st.title(t["title"])
st.write(t["intro"])


# --- Рендер ответа ассистента (общий для истории и новых сообщений) ---------

def show_assistant(content: str, sources: list[str]) -> None:
    if not sources:
        # Пустой sources == официальный отказ «нет информации».
        st.warning(content)
    else:
        st.markdown(content)
        links = "\n".join(f"- [{url}]({url})" for url in sources)
        st.markdown(f"**{t['sources_label']}**\n{links}")


# --- Кнопки-примеры ---------------------------------------------------------

st.caption(t["examples_label"])
cols = st.columns(len(t["examples"]))
for i, example in enumerate(t["examples"]):
    if cols[i].button(example, key=f"example_{lang}_{i}"):
        st.session_state.pending_question = example
        st.rerun()


# --- История чата -----------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            show_assistant(msg["content"], msg.get("sources", []))
        else:
            st.markdown(msg["content"])


# --- Новый вопрос: из chat_input ИЛИ из кнопки-примера ----------------------

prompt = st.chat_input(t["input_placeholder"])
if not prompt and st.session_state.get("pending_question"):
    prompt = st.session_state.pop("pending_question")

if prompt:
    # 1. Показать и сохранить вопрос пользователя.
    st.session_state.messages.append(
        {"role": "user", "content": prompt, "sources": []}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Получить и показать ответ.
    with st.chat_message("assistant"):
        with st.spinner(t["spinner"]):
            result = rag.answer(prompt, lang)
        show_assistant(result["answer"], result["sources"])

    # 3. Сохранить ответ в историю.
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
    })
