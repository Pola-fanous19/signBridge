"""Assemble a pose clip from a sequence of gloss tokens.

Rule:
  1. If the token exists in the lexicon (fixed/ or words/) -> play its frames.
  2. Otherwise -> fingerspell it letter-by-letter using fingerspell.py.

This is exactly the behavior the user asked for:
  "when a gloss word exists in the lexicon, use it; otherwise, take it
   letter by letter."
"""

from app.pose.schema import neutral_frame
from app.pose.fingerspell import fingerspell_clip
from app.pose.lexicon import LEXICON
from app.config import DEFAULT_FPS, HOLD_FRAMES, GAP_FRAMES


def sequence(tokens, fps=DEFAULT_FPS):
    frames = []
    enriched = []
    tokens_found = 0
    tokens_fingerspelled = 0
    missing = []

    for t in tokens:
        tok = t.get("token", "")
        kind = t.get("kind", "sign")
        start = len(frames)

        # Try lexicon first (unless the caller explicitly marked as fingerspell)
        entry = None if kind == "fingerspell" else LEXICON.get(tok)

        if entry and isinstance(entry.get("frames"), list) and entry["frames"]:
            for f in entry["frames"]:
                # Direct-MHR entries already carry quaternion rigs. Do not
                # label those frames as MediaPipe data: the renderer must take
                # the direct path before attempting Kalidokit inference.
                frame = dict(f)
                if not frame.get("isMhrDirect"):
                    frame["isHolisticResult"] = True
                frames.append(frame)
            tokens_found += 1
            source = "lexicon"
        else:
            # Fingerspell letter-by-letter using algorithmic handshapes
            word = "".join(c for c in tok if c.isalpha())
            if not word:
                enriched.append({**t, "frames": 0, "start": start,
                                 "end": start, "source": "skip"})
                continue
            sub_clip, _ = fingerspell_clip(
                word, fps=fps, hold=HOLD_FRAMES, gap=GAP_FRAMES,
            )
            frames.extend(sub_clip["frames"])
            tokens_fingerspelled += 1
            if kind == "sign":
                missing.append(tok)
            source = "fingerspell"

        end = len(frames) - 1
        enriched.append({
            **t,
            "frames": end - start + 1,
            "start": start,
            "end": end,
            "source": source,
        })

    if not frames:
        frames.append(neutral_frame())

    stats = {
        "total_frames": len(frames),
        "total_seconds": round(len(frames) / fps, 2),
        "tokens": len(tokens),
        "tokens_found": tokens_found,
        "tokens_fingerspelled": tokens_fingerspelled,
        "missing_tokens": missing,
        "lexicon": LEXICON.stats(),
    }
    clip = {"frames": frames, "fps": fps}
    return clip, stats, enriched
