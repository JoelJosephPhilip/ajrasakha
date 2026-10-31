import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from classifier import disclaimers


def test_get_disclaimer_english():
    assert disclaimers.get_disclaimer("English") == disclaimers._load()["English"]


def test_get_disclaimer_language_specific_lookup():
    real = disclaimers._load()
    for language in ("Tamil", "Hindi", "Punjabi"):
        assert disclaimers.get_disclaimer(language) == real[language]
        assert disclaimers.get_disclaimer(language) != real["English"]


def test_get_disclaimer_unknown_language_falls_back_to_english():
    assert disclaimers.get_disclaimer("Klingon") == disclaimers._load()["English"]


def test_load_raises_on_wrong_row_count(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("#,Language,Translation\n0,English,only one row\n", encoding="utf-8")

    with pytest.raises(RuntimeError):
        disclaimers._load(bad_csv)
