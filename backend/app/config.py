"""Configuration — loads .env automatically."""
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    # Load .env from the backend/ folder (two levels above this file)
    BACKEND_ROOT = Path(__file__).resolve().parent.parent
    load_dotenv(BACKEND_ROOT / ".env")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LEXICON_DIR = DATA_DIR / "lexicon"

DEFAULT_FPS = int(os.environ.get("SIGNBRIDGE_FPS", "30"))
HOLD_FRAMES = int(os.environ.get("SIGNBRIDGE_HOLD", "10"))
GAP_FRAMES  = int(os.environ.get("SIGNBRIDGE_GAP", "4"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
