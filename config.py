"""Central configuration. Loads .env and exposes typed settings."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# --- Credentials ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
ADOBE_CLIENT_ID = os.getenv("ADOBE_CLIENT_ID", "").strip()
SHEET_WEBHOOK_URL = os.getenv("SHEET_WEBHOOK_URL", "").strip()

# --- Models --- (empty env values fall back to the default, e.g. unset CI secrets)
ORCHESTRATOR_MODEL = (os.getenv("ORCHESTRATOR_MODEL") or "gemini-2.5-flash").strip()
SUMMARIZER_MODEL = (os.getenv("SUMMARIZER_MODEL") or "gemini-2.5-flash").strip()

# --- Tunables ---
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY") or "8")
TOP_N = int(os.getenv("TOP_N") or "5")
MAX_AGE_DAYS = int(os.getenv("MAX_AGE_DAYS") or "7")   # only use news ≤ this many days old

# --- Paths ---
ASSETS_DIR = ROOT / "assets"
OUTPUT_DIR = ROOT / "output"
LOGO_PATH = ASSETS_DIR / "logo_white.png"

OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)


def require(*names: str) -> list[str]:
    """Return the list of missing required env var names."""
    return [n for n in names if not globals().get(n)]
