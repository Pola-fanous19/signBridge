"""Offline rule-based English -> ASL-gloss converter.

Applies standard ASL grammar transformations:
  * drop copulas / auxiliaries (is, am, are, was, were, be)
  * drop articles (a, an, the)
  * move time expressions to the front
  * move WH-words to the end for questions
  * uppercase everything
"""

import re

DROP = {"a", "an", "the", "is", "am", "are", "was", "were", "be",
        "been", "being", "do", "does", "did", "of"}
WH = {"WHO", "WHAT", "WHERE", "WHEN", "WHY", "HOW", "WHICH"}
TIME_WORDS = {"YESTERDAY", "TODAY", "TOMORROW", "NOW", "LATER", "SOON",
              "MORNING", "EVENING", "NIGHT", "TONIGHT"}


def to_gloss(text: str):
    text = text.strip()
    if not text:
        return {"gloss_string": "", "tokens": [], "non_manual": None}

    is_question = text.rstrip().endswith("?")
    words = [w for w in re.split(r"\s+", text) if w]
    cleaned = []
    for w in words:
        stripped = re.sub(r"[^\w'-]", "", w)
        if not stripped:
            continue
        if stripped.lower() in DROP:
            continue
        cleaned.append(stripped.upper())

    time_words = [w for w in cleaned if w in TIME_WORDS]
    others     = [w for w in cleaned if w not in TIME_WORDS]
    ordered    = time_words + others

    if is_question:
        whs   = [w for w in ordered if w in WH]
        rest  = [w for w in ordered if w not in WH]
        ordered = rest + whs

    tokens = []
    for w in ordered:
        kind = "sign" if w.isalpha() else "fingerspell"
        tokens.append({"token": w, "kind": kind})

    non_manual = None
    if is_question:
        non_manual = {"brow_raise": True, "question": True}

    return {
        "gloss_string": " ".join(t["token"] for t in tokens),
        "tokens": tokens,
        "non_manual": non_manual,
    }
