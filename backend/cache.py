"""
Simple JSON-file cache for classified tracks.

Prevents re-classifying identical tracks on subsequent runs (a reproducibility
guardrail against Gemini's 15 RPM free-tier limit). Keys are the normalized
"{artist}-{title}" string; values are the classified attribute dictionaries.
"""
import json
import os
import threading
from typing import Dict, Optional

from backend import config

# Serialize file writes across concurrent requests within one process.
_LOCK = threading.Lock()


def _key(artist: str, title: str) -> str:
    """Build the canonical cache key for a track."""
    return f"{(artist or '').strip().lower()}-{(title or '').strip().lower()}"


def load_cache() -> Dict[str, dict]:
    """Read the whole cache file, returning an empty dict if it is missing/corrupt."""
    path = config.CACHE_PATH
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        # A corrupt cache should never crash the app; just treat it as empty.
        return {}


def save_cache(cache: Dict[str, dict]) -> None:
    """Persist the full cache dictionary to disk (atomically-ish)."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with _LOCK:
        tmp_path = config.CACHE_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, indent=2, ensure_ascii=False)
        os.replace(tmp_path, config.CACHE_PATH)


def get_cached(cache: Dict[str, dict], artist: str, title: str) -> Optional[dict]:
    """Return the classified dict for a track, or None on a cache miss."""
    return cache.get(_key(artist, title))


def put_cached(cache: Dict[str, dict], artist: str, title: str, classified: dict) -> None:
    """Insert/replace a track's classified attributes in the in-memory cache."""
    cache[_key(artist, title)] = classified
