"""
Deezer track-retrieval client (fallback for when Spotify keys are absent).

Deezer's public API needs no authentication. For each selected artist we:
  1. search the artist name -> artist id
  2. pull /artist/{id}/top for their signature tracks
  3. pull /artist/{id}/related to broaden the pool with similar artists' tops

Returns the same standardized dict shape as the Spotify client:
    [{"title": ..., "artist": ..., "cover_url": ..., "preview_url": ...}]
"""
from typing import Dict, List, Optional

import requests

_API_BASE = "https://api.deezer.com"
_TIMEOUT = 10


class DeezerError(RuntimeError):
    """Raised when Deezer cannot fulfil a request."""


def _get(path: str, params: Optional[dict] = None) -> dict:
    """Perform a GET against the Deezer API and return parsed JSON."""
    resp = requests.get(f"{_API_BASE}{path}", params=params or {}, timeout=_TIMEOUT)
    if resp.status_code != 200:
        raise DeezerError(f"Deezer request failed: {resp.status_code}")
    return resp.json()


def _search_artist_id(name: str) -> Optional[str]:
    """Resolve an artist name to its Deezer id (best match)."""
    data = _get("/search/artist", {"q": name, "limit": 1})
    items = data.get("data", [])
    return str(items[0]["id"]) if items else None


def _standardize(track: dict) -> Dict[str, str]:
    """Map a Deezer track object to our standardized dict shape."""
    album = track.get("album") or {}
    artist = track.get("artist") or {}
    return {
        "title": track.get("title", "Unknown Title"),
        "artist": artist.get("name", "Unknown Artist"),
        "cover_url": album.get("cover_medium") or album.get("cover") or "",
        # Deezer exposes a 30s preview under `preview`.
        "preview_url": track.get("preview") or "",
    }


def _artist_top(artist_id: str, limit: int = 10) -> List[dict]:
    """Fetch an artist's top tracks."""
    data = _get(f"/artist/{artist_id}/top", {"limit": limit})
    return data.get("data", [])


def _artist_related(artist_id: str, limit: int = 5) -> List[dict]:
    """Fetch artists related to the given artist."""
    data = _get(f"/artist/{artist_id}/related", {"limit": limit})
    return data.get("data", [])


def fetch_tracks(selected_artists: List[str], target_pool: int = 40) -> List[Dict[str, str]]:
    """
    Build a raw track pool (aim for 30-50 tracks) from Deezer.

    Raises DeezerError only if no artist could be resolved at all.
    """
    pool: List[Dict[str, str]] = []
    seen = set()

    def _add(track: dict) -> None:
        std = _standardize(track)
        dedupe_key = f"{std['artist'].lower()}-{std['title'].lower()}"
        if dedupe_key not in seen and std["title"] != "Unknown Title":
            seen.add(dedupe_key)
            pool.append(std)

    resolved_any = False
    for name in selected_artists:
        artist_id = _search_artist_id(name)
        if not artist_id:
            continue
        resolved_any = True

        # Signature tracks for the seed artist.
        for track in _artist_top(artist_id, limit=10):
            _add(track)

        # Broaden with related artists' top tracks until we hit the target.
        for related in _artist_related(artist_id, limit=5):
            if len(pool) >= target_pool:
                break
            related_id = str(related.get("id", ""))
            if not related_id:
                continue
            for track in _artist_top(related_id, limit=5):
                _add(track)
                if len(pool) >= target_pool:
                    break

        if len(pool) >= target_pool:
            break

    if not resolved_any:
        raise DeezerError("No Deezer artist ids resolved from selections.")

    return pool[:target_pool]
