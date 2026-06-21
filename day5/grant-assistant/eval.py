"""
eval.py — простая оценка качества RAG.

Прогоняет набор тестовых вопросов через rag.answer() и проверяет,
что в ответе/источниках встречаются ожидаемые ключевые слова.
Запуск: python eval.py
"""

import json
from pathlib import Path

import rag

DATA_DIR = Path(__file__).parent / "data"
EVAL_FILE = DATA_DIR / "eval_questions.json"

# Набор по умолчанию, если data/eval_questions.json отсутствует.
DEFAULT_CASES = [
    {"question": "Какие гранты предлагает фонд Есенова?", "keywords": ["грант"]},
    {"question": "Как подать заявку на грант?", "keywords": ["заявк"]},
    {"question": "Какие требования к кандидатам?", "keywords": ["требован"]},
]


def load_cases() -> list[dict]:
    if EVAL_FILE.exists():
        return json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    return DEFAULT_CASES


def keyword_hit(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(kw.lower() in low for kw in keywords)


def main() -> None:
    cases = load_cases()
    passed = 0
    print(f"[eval] тестов: {len(cases)}\n")

    for i, case in enumerate(cases, 1):
        result = rag.answer(case["question"])
        ok = keyword_hit(result["answer"], case.get("keywords", []))
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {i}. {case['question']}")
        print(f"      ответ: {result['answer'][:120]}...")
        print(f"      источников: {len(result['sources'])}\n")

    print(f"[eval] пройдено: {passed}/{len(cases)}")


if __name__ == "__main__":
    main()
