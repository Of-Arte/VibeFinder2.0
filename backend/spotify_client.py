"""
Spotify track-retrieval client.

Uses the Client Credentials flow (public, non-user data only) to search artist
names -> ids, then hits the Recommendations endpoint to build a raw track pool.
Returns a standardized list of dicts:
    [{"title": ..., "artist": ..., "cover_url": ..., "preview_url": ...}]

If anything goes wrong (missing creds, network error, deprecated endpoint),
the caller is expected to fall back to Deezer.
"""
import time
from typing import Dict, List, Optional

import requests

from backend import config

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE = "https://api.spotify.com/v1"
_TIMEOUT = 10

# Cache the app token in-process until it expires.
_token_cache = {"access_token": None, "expires_at": 0.0}


class SpotifyError(RuntimeError):
    """Raised when Spotify cannot fulfil a request; signals the caller to fall back."""


def _get_app_token() -> str:
    """Fetch (and cache) a Client Credentials access token."""
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    if not config.has_spotify_credentials():
        raise SpotifyError("Spotify credentials are not configured.")

    resp = requests.post(
        _TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(config.SPOTIFY_CLIENT_ID, config.SPOTIFY_CLIENT_SECRET),
        timeout=_TIMEOUT,
    )
    if resp.status_code != 200:
        raise SpotifyError(f"Token request failed: {resp.status_code} {resp.text}")

    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise SpotifyError("Token response missing access_token.")
    _token_cache["access_token"] = token
    _token_cache["expires_at"] = now + float(payload.get("expires_in", 3600))
    return token


def _request(method: str, path: str, token: str, **kwargs) -> requests.Response:
    """Perform an authenticated Spotify request with basic 429 backoff."""
    url = f"{_API_BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"

    for attempt in range(3):
        resp = requests.request(method, url, headers=headers, timeout=_TIMEOUT, **kwargs)
        if resp.status_code == 429:
            # Respect Retry-After; back off instead of hammering the API.
            retry_after = int(resp.headers.get("Retry-After", "1"))
            time.sleep(min(retry_after, 5))
            continue
        return resp
    raise SpotifyError("Rate limited by Spotify after retries.")


def _search_artist_id(name: str, token: str) -> Optional[str]:
    """Resolve an artist name to its Spotify id (best match)."""
    resp = _request(
        "GET",
        "/search",
        token,
        params={"q": name, "type": "artist", "limit": 1},
    )
    if resp.status_code != 200:
        raise SpotifyError(f"Artist search failed: {resp.status_code}")
    items = resp.json().get("artists", {}).get("items", [])
    return items[0]["id"] if items else None


def _standardize(track: dict) -> Dict[str, str]:
    """Map a Spotify track object to our standardized dict shape."""
    images = (track.get("album") or {}).get("images") or []
    cover_url = images[0]["url"] if images else ""
    artists = track.get("artists") or []
    artist_name = artists[0]["name"] if artists else "Unknown Artist"
    return {
        "title": track.get("name", "Unknown Title"),
        "artist": artist_name,
        "cover_url": cover_url,
        "preview_url": track.get("preview_url") or "",
    }


def fetch_tracks(selected_artists: List[str], limit: int = 40) -> List[Dict[str, str]]:
    """
    Build a raw track pool from Spotify recommendations seeded by the given artists.

    Raises SpotifyError on any failure so the caller can fall back to Deezer.
    """
    token = _get_app_token()

    seed_ids: List[str] = []
    for name in selected_artists[:5]:  # Spotify allows up to 5 seed artists.
        artist_id = _search_artist_id(name, token)
        if artist_id:
            seed_ids.append(artist_id)

    if not seed_ids:
        raise SpotifyError("No Spotify artist ids resolved from selections.")

    resp = _request(
        "GET",
        "/recommendations",
        token,
        params={"seed_artists": ",".join(seed_ids), "limit": limit},
    )
    if resp.status_code != 200:
        raise SpotifyError(f"Recommendations failed: {resp.status_code} {resp.text}")

    tracks = resp.json().get("tracks", [])
    pool = [_standardize(t) for t in tracks]
    if not pool:
        raise SpotifyError("Spotify returned an empty recommendation pool.")
    return pool
