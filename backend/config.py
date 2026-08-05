"""
Central configuration for the VibeFinder 2.0 backend.

Loads environment variables from a local `.env` file (see `.env.example`).
Only GEMINI_API_KEY is required. Track retrieval uses the public, keyless
Deezer API.
"""
import os
from dotenv import load_dotenv

# Load .env from the project root regardless of the current working directory.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# --- API credentials -------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# --- Model / behaviour tuning ---------------------------------------------
# Flash-Lite tier for cheap, fast classification. The exact `gemini-2.5-flash-lite`
# id is gated ("no longer available to new users") on this key, so we pin the
# `gemini-flash-lite-latest` alias, which resolves to the current stable
# Flash-Lite model. Override via the GEMINI_MODEL env var if needed.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip()

# --- Classification sizing -------------------------------------------------
# We only surface the top 5, so a large pool just adds latency, token cost, and
# truncation risk. Cap how many tracks we fetch and classify, and chunk the
# Gemini classification so one failing chunk degrades in isolation rather than
# collapsing the whole pool to fallbacks.
CLASSIFY_POOL_SIZE = int(os.getenv("CLASSIFY_POOL_SIZE", "24"))
CLASSIFY_BATCH_SIZE = int(os.getenv("CLASSIFY_BATCH_SIZE", "12"))
# Upper bound on classifier output tokens (each track ~90 tokens of JSON).
CLASSIFY_MAX_OUTPUT_TOKENS = int(os.getenv("CLASSIFY_MAX_OUTPUT_TOKENS", "4096"))

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = _PROJECT_ROOT

# --- Rate limiting ---------------------------------------------------------
# To prevent overloading our backend or the external Deezer and Gemini APIs
# with too many requests at once, each client's requests are rate-limited.
# Since demo users supply their own API keys and there are no user accounts,
# this acts as a rate-limiting safety guardrail rather than a cost control.
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# --- CORS ------------------------------------------------------------------
# Vite dev server default origin(s).
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def has_gemini() -> bool:
    """True when a Gemini API key is configured."""
    return bool(GEMINI_API_KEY)
