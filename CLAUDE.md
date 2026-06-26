# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal **daily ML / data-science learning workspace**. Each `dayN/` folder is a self-contained exercise — usually a Jupyter notebook plus its dataset(s). There is no shared package, build system, or test suite; days do not import from each other. Most "code" lives inside `.ipynb` files, not `.py` modules.

The one real application is `day5/grant-assistant/` (a Streamlit RAG app) — see below.

## Critical: git layout

The git repository is rooted at **`ydl2026/`** (the parent of all `dayN/` folders), even though work usually happens inside a single day. Consequences:

- `git add -A` from inside a day folder stages the **entire repo**. Always stage explicit paths.
- The root `.gitignore` excludes secrets (`.env`, `creds.txt`), all `*.png`, `__pycache__/`, `.ipynb_checkpoints/`, and large/re-downloadable data files (e.g. `day3/911.csv`). When adding a new large dataset (>~100 MB) or generated image, add it to `.gitignore` rather than committing it.

## Secrets & LLM access

Two patterns coexist; **never hardcode keys**, never commit `.env` or `creds.txt`:

- `day1/load_env.py` — a zero-dependency stdlib `.env` loader (`os.environ.setdefault`).
- `day5/grant-assistant/` — uses `python-dotenv` (`load_dotenv()`).

LLM calls go through an **OpenAI-compatible endpoint** (`GEMMA_BASE_URL`, default `https://llm.alem.ai/v1`), model `gemma4`, `Authorization: Bearer <key>`. The canonical wrapper is `day5/grant-assistant/gemma_client.py::ask_gemma(system, user, temperature)`, which POSTs to `{BASE_URL}/chat/completions` and degrades gracefully (returns an `[Ошибка ...]` string instead of raising when keys are missing or the request fails). Notebooks and code in this repo are bilingual (Russian/Kazakh/English); comments and user-facing text are often in Russian.

## Running things

**Notebooks** (the default unit of work): open in Jupyter and run cells top-to-bottom. Datasets are read by relative path from the notebook's own folder, so run from within that `dayN/`.

**Kaggle-style competition days** (`day4`, `day9`): a notebook trains on `train.csv`, predicts on `test.csv`, and writes `submission*.csv` matching `sample_submission.csv`. Models used: scikit-learn plus `xgboost` / `lightgbm` / `catboost` (CatBoost writes a `catboost_info/` training-log dir — it is disposable). `day9/inception.ipynb` is sleep-stage classification from EEG features.

**grant-assistant** (`day5/grant-assistant/`) — full pipeline:
```bash
cd day5/grant-assistant
python -m venv venv && venv\Scripts\Activate.ps1   # PowerShell
pip install -r requirements.txt
cp .env.example .env            # then fill in keys
python scrape.py                # foundation pages -> data/pages.jsonl
python build_index.py           # -> data/index/ (FAISS index + meta.json)
streamlit run app.py            # web UI
python eval.py                  # optional answer-quality check
```
Architecture: `scrape.py` (BeautifulSoup/trafilatura) → `build_index.py` (sentence-transformers embeddings → FAISS) → `rag.py` (retrieve + generate via `gemma_client`) → `app.py` (Streamlit UI). If retrieval finds no answer, `email_utils.py` forwards the question to the foundation admin via MailerSend. `gemma_client.refusal_text(lang)` holds the official RU/KK/EN refusal message.

## Day-by-day map

| Day  | Topic |
|------|-------|
| day1 | Python basics, `.env` loader, image-gen script, `tetris.html` |
| day2 | Titanic notebook (`work.ipynb`) |
| day3 | EDA: UK universities; 911-calls capstone |
| day4 | Titanic linear regression (competition submission) |
| day5 | **grant-assistant** — Streamlit RAG app (the main project) |
| day6 | Housing prices, apple quality |
| day7 | Concrete compressive strength regression (see `Concrete_Readme.txt`) |
| day8 | Wholesale customers clustering |
| day9 | EEG sleep-stage classification (gradient-boosting; Kaggle-style) |

## Conventions

- Per-day `CLAUDE.md` files may exist (e.g. `day1/CLAUDE.md`) with folder-specific notes — read the one for the day you're working in.
- Datasets live alongside their notebook; keep new data files inside the relevant `dayN/`.
- No linter or test runner is configured. Don't assume `pytest`/`ruff` exist unless you add them.
