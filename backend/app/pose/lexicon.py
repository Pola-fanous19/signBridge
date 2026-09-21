"""Lexicon loader.

Reads token -> pose-clip JSON files from data/lexicon.
Loads all three subfolders:
    - fixed/           (fixed grammar signs: WH, IX, POSS, ...)
    - words/           (real ASL words: HELLO, THANK-YOU, LOVE, ...)
    - fingerspelling/  (single-letter clips A..Z; used as fallback data)

If a token has a lexicon entry -> use it directly.
Otherwise the sequencer will fall back to letter-by-letter fingerspelling
using the algorithmic handshapes in fingerspell.py.
"""

import json
from app.config import LEXICON_DIR


class Lexicon:
    def __init__(self):
        self._cache = {}
        self._loaded = False
        self._stats = {"fixed": 0, "words": 0, "fingerspelling": 0, "errors": 0}

    def _load(self):
        if self._loaded:
            return
        for sub in ("fixed", "words", "fingerspelling"):
            d = LEXICON_DIR / sub
            if not d.exists():
                continue
            for f in d.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    # Only cache entries that actually contain playable frames.
                    # Fingerspelling files use a different schema (right_hand
                    # only) and are consumed by fingerspell.py, so we skip
                    # them here for word-level lookup.
                    if sub == "fingerspelling":
                        self._stats["fingerspelling"] += 1
                        continue
                    if isinstance(data.get("frames"), list) and data["frames"]:
                        key = f.stem.upper()
                        self._cache[key] = data
                        self._stats[sub] += 1
                except Exception:
                    self._stats["errors"] += 1
        self._loaded = True

    def get(self, token):
        self._load()
        return self._cache.get(token.upper())

    def has(self, token):
        self._load()
        return token.upper() in self._cache

    def stats(self):
        self._load()
        return {
            **self._stats,
            "total_cached": len(self._cache),
            "known_tokens": sorted(self._cache.keys()),
        }


LEXICON = Lexicon()
