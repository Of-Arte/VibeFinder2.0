"""
Central configuration for the VibeFinder 2.0 backend.

Loads environment variables from a local `.env` file (see `.env.example`).
Only GEMINI_API_KEY is required; the Spotify credentials are optional and,
when absent, the app transparently falls back to the public Deezer API.
"""
import os
from dotenv import load_dotenv

# Load .env from the project root regardless of the current working directory.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# --- API credentials -------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()

# --- Model / behaviour tuning ---------------------------------------------
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = _PROJECT_ROOT
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
CACHE_PATH = os.path.join(DATA_DIR, "track_cache.json")

# --- CORS ------------------------------------------------------------------
# Vite dev server default origin(s).
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def has_spotify_credentials() -> bool:
    """True when both Spotify client id and secret are configured."""
    return bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET)


def has_gemini() -> bool:
    """True when a Gemini API key is configured."""
    return bool(GEMINI_API_KEY)
