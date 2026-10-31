"""MiniMax chat-completions client for the agriculture classifier. Every
call goes through _chat_completion() - the one seam tests monkeypatch so no
automated test ever makes a real network call. Self-contained: no import
from any other apis/* service or ai/ajrasakha/*.
"""

import json
import logging
import time

import httpx

from . import config
from .models import LLMUnavailableError

log = logging.getLogger("agriculture_classifier.llm_client")

_CLASSIFY_SYSTEM_PROMPT = (
    "You decide whether a farmer's question is related to agriculture - "
    "crop cultivation, pest and disease management, fertilizers, irrigation, "
    "or other agriculture-related topics. The question may be written in "
    "any language or script (including Indian regional languages, Hinglish, "
    "or romanized/transliterated text) and may contain spelling mistakes - "
    "classify based on the question's meaning, not its exact spelling. "
    'Respond only with a JSON object of this exact shape: {"is_agriculture": true|false}.'
)

# Unicode script block -> the official languages that use it. Several
# scripts are shared by multiple languages (Devanagari alone covers 8 of our
# 23), so this narrows the LLM's choice to only the genuinely ambiguous
# candidates instead of asking it to pick freely from all 23 - measured
# directly against MiniMax-M2.7 (data/eval, not committed): a flat 23-way
# prompt scored 19/23 and was inconsistent run-to-run on Bodo/Dogri/Konkani/
# Sanskrit; narrowing to the script's actual candidates scored 23/23.
_SCRIPT_RANGES: list[tuple[tuple[int, int], list[str]]] = [
    ((0x0900, 0x097F), ["Hindi", "Marathi", "Nepali", "Sanskrit", "Maithili", "Bodo", "Konkani", "Dogri"]),  # Devanagari
    ((0x0980, 0x09FF), ["Bengali", "Assamese"]),  # Bengali-Assamese
    ((0x0A00, 0x0A7F), ["Punjabi"]),  # Gurmukhi
    ((0x0A80, 0x0AFF), ["Gujarati"]),
    ((0x0B00, 0x0B7F), ["Odia"]),
    ((0x0B80, 0x0BFF), ["Tamil"]),
    ((0x0C00, 0x0C7F), ["Telugu"]),
    ((0x0C80, 0x0CFF), ["Kannada"]),
    ((0x0D00, 0x0D7F), ["Malayalam"]),
    ((0x0600, 0x06FF), ["Urdu", "Kashmiri", "Sindhi"]),  # Perso-Arabic
    ((0x1C50, 0x1C7F), ["Santali"]),  # Ol Chiki
    ((0xABC0, 0xABFF), ["Manipuri (Meitei)"]),  # Meitei Mayek
]


def _script_candidates(text: str) -> list[str]:
    """Deterministic, LLM-free script detection - counts each character's
    Unicode block and returns the official languages that use the
    best-represented script. No script match (Latin/romanized/punctuation/
    numbers) returns ["English"], matching this service's existing
    convention for transliterated text."""
    counts: dict[int, int] = {}
    for ch in text:
        cp = ord(ch)
        for i, (lo_hi, _langs) in enumerate(_SCRIPT_RANGES):
            lo, hi = lo_hi
            if lo <= cp <= hi:
                counts[i] = counts.get(i, 0) + 1
                break
    if not counts:
        return ["English"]
    best_index = max(counts, key=counts.get)
    return _SCRIPT_RANGES[best_index][1]


def _narrowed_language_prompt(candidates: list[str]) -> str:
    return (
        "Identify which of these specific languages the user's text is "
        "written in - it is definitely one of: " + ", ".join(candidates) + ". "
        'Respond only with a JSON object of this exact shape: '
        '{"language": "<one of the listed names>"}.'
    )


def classify_agriculture(question: str) -> bool:
    messages = [
        {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    content = _chat_completion(messages, temperature=0.0, call_name="classify_agriculture")
    try:
        parsed = json.loads(content)
        return bool(parsed["is_agriculture"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise LLMUnavailableError(f"Could not parse agriculture-classification response: {exc}") from exc


def detect_language(question: str) -> str:
    """Script detection first (deterministic, no LLM call) narrows to the
    languages that actually use that script. A single-language script
    (Tamil, Telugu, Gujarati, ...) returns directly - no ambiguity, no LLM
    needed. Only a shared script (Devanagari, Perso-Arabic, Bengali-Assamese)
    calls MiniMax, and only to disambiguate within that narrowed set."""
    candidates = _script_candidates(question)
    if len(candidates) == 1:
        return candidates[0]

    messages = [
        {"role": "system", "content": _narrowed_language_prompt(candidates)},
        {"role": "user", "content": question},
    ]
    content = _chat_completion(messages, temperature=0.0, call_name="detect_language")
    try:
        parsed = json.loads(content)
        language = str(parsed["language"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise LLMUnavailableError(f"Could not parse language-detection response: {exc}") from exc

    if language not in candidates:
        # The model answered outside the narrowed set it was given - fall
        # back to the script's most common language rather than guessing.
        log.warning("detect_language returned %r outside narrowed candidates %r", language, candidates)
        return candidates[0]
    return language


def _chat_completion(messages: list[dict], call_name: str = "unknown", **kwargs) -> str:
    if not config.MINIMAX_BASE_URL:
        raise LLMUnavailableError("MINIMAX_BASE_URL is not set")

    url = config.MINIMAX_BASE_URL.rstrip("/") + config.MINIMAX_CHAT_PATH
    headers = {"Content-Type": "application/json"}
    if config.MINIMAX_API_KEY:
        headers["Authorization"] = f"Bearer {config.MINIMAX_API_KEY}"

    payload = {"model": config.MINIMAX_MODEL, "messages": messages, "seed": config.MINIMAX_SEED, **kwargs}
    # Input size, not output - what we sent, to correlate a slow/timed-out
    # call with how much the model had to read. Logged on failure only.
    content_chars = sum(len(m.get("content", "")) for m in messages)

    t0 = time.monotonic()
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=config.MINIMAX_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        # MiniMax's official API reports some failures via base_resp inside
        # an HTTP 200 rather than an HTTP error status; absent on the
        # OpenAI-compatible shape, hence .get().
        base_resp = data.get("base_resp")
        if base_resp and base_resp.get("status_code") not in (None, 0):
            raise LLMUnavailableError(f"MiniMax reported an error: {base_resp}")
        return data["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        elapsed = time.monotonic() - t0
        log.error(
            "%s failed after %.1fs (budget %.0fs, input %d chars, model %s): %s",
            call_name, elapsed, config.MINIMAX_TIMEOUT_SECONDS, content_chars, config.MINIMAX_MODEL, exc,
        )
        raise LLMUnavailableError(f"MiniMax call failed: {exc}") from exc
