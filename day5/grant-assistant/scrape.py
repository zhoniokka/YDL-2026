"""
scrape.py — сбор данных с сайта фонда Есенова для трёхъязычного бота
(казахский /kk/, русский /ru/, английский /en/).

Что делает:
  1. Берёт стартовые русские страницы (гранты и программы).
  2. Обходит подстраницы внутри пути /about-us/programs/ (глубина до 2),
     переходя только по внутренним ссылкам того же раздела.
  3. Для каждого собранного RU-URL добавляет казахскую и английскую версии
     (замена префикса /ru/ -> /kk/ и /en/).
  4. Извлекает чистый текст (trafilatura, запасной вариант — BeautifulSoup),
     убирая меню/шапку/футер/навигацию, берёт заголовок (title/og:title/h1).
  5. Сохраняет результат в data/pages.json.

Скрипт идемпотентный: повторный запуск перезаписывает data/pages.json.

Запуск:
    python scrape.py
"""

import json
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse
from urllib.robotparser import RobotFileParser

import requests
import trafilatura
from bs4 import BeautifulSoup

# Консоль Windows может быть в cp1251 и падать на казахских буквах — форсим UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# --- Конфигурация -----------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
PAGES_FILE = DATA_DIR / "pages.json"

DOMAIN = "yessenovfoundation.org"
BASE = f"https://{DOMAIN}"
ROBOTS_URL = f"{BASE}/robots.txt"

# Стартовые русские страницы (раздел про гранты и программы).
SEED_URLS = [
    "https://yessenovfoundation.org/ru/about-us/programs/",
    "https://yessenovfoundation.org/ru/about-us/programs/resources/yessenov-data-lab/yessenov-data-lab-2026/",
    "https://yessenovfoundation.org/ru/about-us/mission-and-reports/",
]

# Раздел, внутри которого обходим подстраницы.
PROGRAMS_PATH = "/ru/about-us/programs/"
PROGRAMS_START = f"{BASE}{PROGRAMS_PATH}"
CRAWL_MAX_DEPTH = 2

# Языки и соответствующие префиксы пути.
LANGS = ("kk", "ru", "en")

# Подстроки в URL, которые пропускаем (новости, истории, медиа).
SKIP_SUBSTRINGS = ("/category/", "/novosti/", "/istorii", "/wp-content/")

# Сеть.
TIMEOUT = 20            # секунд на запрос
MAX_RETRIES = 2         # дополнительных повторов при сетевой ошибке
RETRY_PAUSE = 3         # секунд между повторами
REQUEST_DELAY = 1.0     # секунд между запросами (вежливость)
USER_AGENT = "grant-assistant-bot/1.0 (+educational RAG project; contact admin)"

HEADERS = {"User-Agent": USER_AGENT}


# --- robots.txt -------------------------------------------------------------

def load_robots() -> RobotFileParser:
    """Загружает robots.txt. При ошибке — пустой парсер (всё разрешено)."""
    rp = RobotFileParser()
    rp.set_url(ROBOTS_URL)
    try:
        resp = requests.get(ROBOTS_URL, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
            print(f"[robots] загружен {ROBOTS_URL}")
        else:
            print(f"[robots] нет robots.txt (HTTP {resp.status_code}) — разрешаем всё")
            rp.allow_all = True
    except requests.RequestException as exc:
        print(f"[robots] не удалось загрузить ({exc}) — разрешаем всё")
        rp.allow_all = True
    return rp


# --- Фильтры URL ------------------------------------------------------------

def normalize(url: str) -> str:
    """Убирает якорь (#...) и хвостовые пробелы."""
    return urldefrag(url.strip())[0]


def is_same_domain(url: str) -> bool:
    netloc = urlparse(url).netloc.lower()
    return netloc == DOMAIN or netloc == f"www.{DOMAIN}"


def is_skippable(url: str) -> bool:
    """True, если URL нужно пропустить (новости/истории/медиа/внешний)."""
    if not is_same_domain(url):
        return True
    low = url.lower()
    return any(sub in low for sub in SKIP_SUBSTRINGS)


def lang_of(url: str) -> str | None:
    """Определяет язык по префиксу пути (/kk/, /ru/, /en/)."""
    path = urlparse(url).path
    for lang in LANGS:
        if path.startswith(f"/{lang}/"):
            return lang
    return None


def to_lang(url: str, target_lang: str) -> str:
    """Меняет языковой префикс пути на target_lang (.../ru/... -> .../kk/...)."""
    parts = urlparse(url)
    path = parts.path
    cur = lang_of(url)
    if cur:
        path = path.replace(f"/{cur}/", f"/{target_lang}/", 1)
    return parts._replace(path=path).geturl()


# --- Сеть -------------------------------------------------------------------

def fetch(url: str) -> str | None:
    """Скачивает HTML с таймаутом и повторами. None при неудаче."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            return resp.text
        except requests.RequestException as exc:
            if attempt < MAX_RETRIES:
                print(f"[fetch] ошибка {url} ({exc}); повтор {attempt + 1}/{MAX_RETRIES}")
                time.sleep(RETRY_PAUSE)
            else:
                print(f"[fetch] не удалось {url}: {exc}")
    return None


# --- Извлечение текста и заголовка ------------------------------------------

def extract_title(soup: BeautifulSoup, url: str) -> str:
    """Заголовок: og:title -> <title> -> <h1> -> URL."""
    og = soup.find("meta", property="og:title")
    if og and og.get("content", "").strip():
        return og["content"].strip()
    if soup.title and soup.title.string and soup.title.string.strip():
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    return url


def extract_text(html: str) -> str:
    """Чистый текст: сначала trafilatura, затем BeautifulSoup как запас."""
    text = trafilatura.extract(
        html, include_comments=False, include_tables=True, favor_recall=True
    )
    if text and text.strip():
        return text.strip()

    # Запасной вариант: убираем неинформативные блоки и берём текст.
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "form",
                     "noscript", "aside"]):
        tag.decompose()
    lines = [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]
    return "\n".join(lines).strip()


# --- Обход раздела /about-us/programs/ --------------------------------------

def crawl_programs(robots: RobotFileParser) -> tuple[dict[str, str], set[str]]:
    """
    BFS по разделу /about-us/programs/ до глубины CRAWL_MAX_DEPTH.

    Возвращает (html_cache, discovered_urls), где html_cache хранит уже
    скачанный HTML, чтобы не качать те же страницы повторно.
    """
    html_cache: dict[str, str] = {}
    discovered: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(PROGRAMS_START, 0)])
    visited: set[str] = set()

    while queue:
        url, depth = queue.popleft()
        url = normalize(url)
        if url in visited:
            continue
        visited.add(url)

        if is_skippable(url):
            continue
        if not robots.can_fetch(USER_AGENT, url):
            print(f"[crawl] запрещено robots.txt: {url}")
            continue

        html = fetch(url)
        time.sleep(REQUEST_DELAY)
        if not html:
            continue

        html_cache[url] = html
        discovered.add(url)
        print(f"[crawl] глубина {depth}: {url}")

        if depth >= CRAWL_MAX_DEPTH:
            continue

        # Собираем внутренние ссылки, остающиеся внутри /about-us/programs/.
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            link = normalize(urljoin(url, a["href"]))
            if is_skippable(link):
                continue
            if PROGRAMS_PATH not in urlparse(link).path:
                continue
            if link not in visited:
                queue.append((link, depth + 1))

    return html_cache, discovered


# --- Сборка результата ------------------------------------------------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    robots = load_robots()

    # 1. Обход раздела «Программы» + стартовые страницы (все на /ru/).
    html_cache, discovered = crawl_programs(robots)
    ru_urls = set(SEED_URLS) | {u for u in discovered if lang_of(u) == "ru"}
    print(f"[plan] русских страниц найдено: {len(ru_urls)}")

    # 2. Трёхъязычность: для каждого RU-URL — версии kk/ru/en. Дедупликация.
    targets: list[str] = []
    seen: set[str] = set()
    for ru_url in sorted(ru_urls):
        for lang in LANGS:
            url = normalize(to_lang(ru_url, lang))
            if url not in seen and not is_skippable(url):
                seen.add(url)
                targets.append(url)
    print(f"[plan] всего URL к сбору (3 языка): {len(targets)}")

    # 3. Скачивание и извлечение текста.
    pages: list[dict] = []
    failed: list[str] = []
    empty: list[str] = []

    for url in targets:
        if not robots.can_fetch(USER_AGENT, url):
            print(f"[skip] запрещено robots.txt: {url}")
            failed.append(url)
            continue

        html = html_cache.get(url)
        if html is None:
            html = fetch(url)
            time.sleep(REQUEST_DELAY)
        if not html:
            failed.append(url)
            continue

        soup = BeautifulSoup(html, "html.parser")
        title = extract_title(soup, url)
        text = extract_text(html)

        if not text:
            print(f"[empty] текст не извлёкся: {url}")
            empty.append(url)
            continue

        pages.append({
            "url": url,
            "lang": lang_of(url) or "unknown",
            "title": title,
            "text": text,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"[ok] {lang_of(url)} | {title[:60]}")

    # 4. Идемпотентная перезапись результата.
    PAGES_FILE.write_text(
        json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 5. Сводка.
    per_lang = {lang: sum(1 for p in pages if p["lang"] == lang) for lang in LANGS}
    print("\n========== СВОДКА ==========")
    print(f"Собрано страниц:   {len(pages)}")
    print(f"  по языкам:       kk={per_lang['kk']}  ru={per_lang['ru']}  en={per_lang['en']}")
    print(f"Пустых (пропущено): {len(empty)}")
    print(f"Упало (ошибки/robots): {len(failed)}")
    if failed:
        for u in failed:
            print(f"   FAIL: {u}")
    print(f"Результат: {PAGES_FILE}")


if __name__ == "__main__":
    main()
