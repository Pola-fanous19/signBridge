"""Gemini API gloss backend.

Reads GEMINI_API_KEY from the environment (loaded via .env in config.py).
Falls back to rule-based if the key is missing or the API call fails.
Also exposes check_gemini() so the frontend can render a connection icon.

Model selection: we try a list of currently-supported Gemini models in order
and cache the first one that works. This makes the app resilient to Google
retiring model names over time.
"""

import time
from app.config import GEMINI_API_KEY
from app.gloss.rule_based import to_gloss as _rule_to_gloss

# Ordered fallback list — first working model wins.
CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-pro",
]

_STATE = {
    "checked_at": 0.0,
    "connected": False,
    "reason": "not-checked",
    "model": CANDIDATE_MODELS[0],
}


def _pick_working_model(genai):
    """Return the first candidate model that responds successfully."""
    last_error = "no candidates tried"
    for name in CANDIDATE_MODELS:
        try:
            m = genai.GenerativeModel(name)
            resp = m.generate_content("ping")
            if resp and (resp.text or "").strip():
                return name, m, None
            last_error = f"{name}: empty response"
        except Exception as e:
            last_error = f"{name}: {type(e).__name__}"
            continue
    return None, None, last_error


def _do_check(force: bool = False):
    """Cache Gemini status for 30 seconds to avoid hammering the API."""
    now = time.time()
    if not force and (now - _STATE["checked_at"]) < 30 and _STATE["checked_at"] > 0:
        return _STATE

    _STATE["checked_at"] = now
    if not GEMINI_API_KEY:
        _STATE["connected"] = False
        _STATE["reason"] = "no-api-key"
        return _STATE

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        name, _, err = _pick_working_model(genai)
        if name:
            _STATE["connected"] = True
            _STATE["reason"] = "ok"
            _STATE["model"] = name
        else:
            _STATE["connected"] = False
            _STATE["reason"] = err or "no working model"
    except Exception as e:
        _STATE["connected"] = False
        _STATE["reason"] = f"error: {type(e).__name__}"
    return _STATE


def check_gemini():
    s = _do_check(force=False)
    return {
        "configured": bool(GEMINI_API_KEY),
        "connected": s["connected"],
        "reason":    s["reason"],
        "model":     s["model"],
    }


def to_gloss(text: str):
    if not GEMINI_API_KEY:
        return _rule_to_gloss(text)
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        # Ensure we have a validated model name (populates _STATE['model'])
        if not _STATE["connected"] or (time.time() - _STATE["checked_at"]) > 300:
            _do_check(force=True)
        if not _STATE["connected"]:
            return _rule_to_gloss(text)

        model = genai.GenerativeModel(_STATE["model"])
        prompt = (
            "Convert this English sentence to ASL gloss. Return ONLY the gloss "
            "as UPPERCASE tokens separated by single spaces, no explanation, "
            "no punctuation. Use topic-comment order, drop articles and "
            "copulas, move time words to the front, and move WH words to the "
            "end for questions.\n\n"
            f"English: {text}\nGloss:"
        )
        resp = model.generate_content(prompt)
        gloss_str = (resp.text or "").strip().upper()
        # Strip trailing punctuation just in case the model added any
        gloss_str = gloss_str.replace(".", "").replace(",", "").replace("!", "")
        if not gloss_str:
            return _rule_to_gloss(text)

        # Mark connection as OK because a call just succeeded
        _STATE["connected"] = True
        _STATE["reason"] = "ok"
        _STATE["checked_at"] = time.time()

        tokens = [{"token": w, "kind": "sign"} for w in gloss_str.split()]
        return {
            "gloss_string": gloss_str,
            "tokens": tokens,
            "non_manual": {"question": True, "brow_raise": True} if text.rstrip().endswith("?") else None,
        }
    except Exception as e:
        _STATE["connected"] = False
        _STATE["reason"] = f"error: {type(e).__name__}"
        _STATE["checked_at"] = time.time()
        return _rule_to_gloss(text)
