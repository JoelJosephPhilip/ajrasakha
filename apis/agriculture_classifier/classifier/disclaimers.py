"""Disclaimer-text lookup, keyed by language name. The CSV in data/ is the
single source of truth - swap that file to update any language's text.
Self-contained: no import from any other apis/* service or ai/ajrasakha/*.
"""

import csv
import logging
from pathlib import Path

log = logging.getLogger("agriculture_classifier.disclaimers")

# The 23 names from the CSV's own Language column (stripped), in CSV order.
OFFICIAL_LANGUAGES = [
    "English",
    "Assamese",
    "Bengali",
    "Bodo",
    "Dogri",
    "Gujarati",
    "Hindi",
    "Kannada",
    "Kashmiri",
    "Konkani",
    "Maithili",
    "Malayalam",
    "Manipuri (Meitei)",
    "Marathi",
    "Nepali",
    "Odia",
    "Punjabi",
    "Sanskrit",
    "Santali",
    "Sindhi",
    "Tamil",
    "Telugu",
    "Urdu",
]

_DISCLAIMERS_PATH = Path(__file__).resolve().parent.parent / "data" / "agriculture_disclaimers.csv"
_EXPECTED_ROW_COUNT = len(OFFICIAL_LANGUAGES)

_cache: dict[str, str] | None = None


def _load(path: Path = _DISCLAIMERS_PATH) -> dict[str, str]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = {row["Language"].strip(): row["Translation"] for row in csv.DictReader(f)}
    if len(rows) != _EXPECTED_ROW_COUNT:
        raise RuntimeError(
            f"Disclaimer CSV at {path} has {len(rows)} rows, expected {_EXPECTED_ROW_COUNT}"
        )
    return rows


def get_disclaimer(language: str) -> str:
    global _cache
    if _cache is None:
        _cache = _load()
    if language in _cache:
        return _cache[language]
    # Never log the disclaimer text itself, only the language that missed.
    log.warning("No disclaimer for language=%r, falling back to English", language)
    return _cache["English"]
