"""
Deezer track-retrieval client — the sole track source for VibeFinder 2.0.

Deezer's public API needs no authentication. For each selected artist we:
  1. search the artist name -> artist id
  2. pull /artist/{id}/top for their signature tracks
  3. pull /artist/{id}/related to broaden the pool with similar artists' tops

Returns a standardized list of dicts:
    [{"title": ..., "artist": ..., "cover_url": ..., "preview_url": ...}]
"""
from typing import Dict, List, Optional

import requests

_API_BASE = "https://api.deezer.com"
_TIMEOUT = 10


class DeezerError(RuntimeError):
    """Raised when Deezer cannot fulfil a request."""


_DEEZER_ID_TO_GENRE = {
    132: "pop",          # Pop
    116: "hip hop",      # Rap/Hip Hop
    122: "hip hop",      # Reggaeton
    152: "rock",         # Rock
    113: "edm",          # Dance
    165: "pop",          # R&B
    85: "rock",          # Alternative
    186: "pop",          # Christian
    106: "edm",          # Electro
    466: "folk",         # Folk
    144: "reggae",       # Reggae
    129: "jazz",         # Jazz
    84: "folk",          # Country
    98: "classical",     # Classical
    173: "classical",    # Films/Games
    464: "metal",        # Metal
    169: "jazz",         # Soul & Funk
    2: "world",          # African Music
    16: "world",         # Asian Music
    153: "blues",        # Blues
    75: "world",         # Brazilian Music
    71: "world",         # Cumbia
    81: "world",         # Indian Music
    197: "world",        # Latin Music
}


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


def _standardize(track: dict) -> Dict:
    """Map a Deezer track object to our standardized dict shape.

    We keep the raw signal Deezer exposes (bpm, rank/popularity, duration) so
    that classification — and, critically, the deterministic fallback — can
    produce *distinct* per-track features instead of a flat constant.
    """
    album = track.get("album") or {}
    artist = track.get("artist") or {}
    return {
        "title": track.get("title", "Unknown Title"),
        "artist": artist.get("name", "Unknown Artist"),
        "cover_url": album.get("cover_medium") or album.get("cover") or "",
        # Deezer exposes a 30s preview under `preview`.
        "preview_url": track.get("preview") or "",
        # Raw signal — often sparse (bpm is frequently 0), but real when present.
        "deezer_bpm": float(track.get("bpm") or 0),
        "deezer_rank": int(track.get("rank") or 0),
        "deezer_duration": int(track.get("duration") or 0),
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


def fetch_artist_genre(artist_name: str) -> Optional[str]:
    """
    Resolve an artist's genre dynamically from their Deezer albums.
    Returns one of the supported genres, or None if unresolved.
    """
    clean_name = (artist_name or "").strip().lower()
    if not clean_name:
        return None
    try:
        artist_id = _search_artist_id(clean_name)
        if not artist_id:
            return None
        # Retrieve the artist's albums to extract genre_id
        albums_data = _get(f"/artist/{artist_id}/albums", {"limit": 3})
        items = albums_data.get("data", [])
        for album in items:
            genre_id = album.get("genre_id")
            if genre_id and int(genre_id) in _DEEZER_ID_TO_GENRE:
                return _DEEZER_ID_TO_GENRE[int(genre_id)]
    except Exception:
        # Gracefully absorb connection timeouts or other network/JSON errors
        pass
    return None
