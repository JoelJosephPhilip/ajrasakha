import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classifier import llm_client


def test_script_candidates_single_script_languages():
    assert llm_client._script_candidates("வேளாண்மை") == ["Tamil"]
    assert llm_client._script_candidates("ಕೃಷಿ") == ["Kannada"]
    assert llm_client._script_candidates("How is the weather?") == ["English"]


def test_script_candidates_shared_script_returns_all_candidates():
    devanagari_candidates = llm_client._script_candidates("कृषि संबंधित प्रश्न")
    assert set(devanagari_candidates) == {
        "Hindi", "Marathi", "Nepali", "Sanskrit", "Maithili", "Bodo", "Konkani", "Dogri",
    }


def test_detect_language_skips_llm_for_single_script(monkeypatch):
    def _fail_if_called(*args, **kwargs):
        raise AssertionError("_chat_completion should not be called for an unambiguous script")

    monkeypatch.setattr(llm_client, "_chat_completion", _fail_if_called)

    assert llm_client.detect_language("வேளாண்மை பற்றிய கேள்வி") == "Tamil"


def test_detect_language_calls_narrowed_llm_for_shared_script(monkeypatch):
    monkeypatch.setattr(llm_client, "_chat_completion", lambda messages, **kw: '{"language": "Hindi"}')
    assert llm_client.detect_language("कृषि संबंधित प्रश्न") == "Hindi"


def test_detect_language_falls_back_when_llm_answers_outside_candidates(monkeypatch):
    monkeypatch.setattr(llm_client, "_chat_completion", lambda messages, **kw: '{"language": "English"}')
    result = llm_client.detect_language("कृषि संबंधित प्रश्न")
    assert result == "Hindi"  # first candidate for Devanagari, not the out-of-set answer
