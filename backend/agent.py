"""
Unified Gemini agent layer for VibeFinder 2.0.

Three independent agent functions built on the google-generativeai SDK:
  1. classify_tracks_batch  — dynamically infers audio features for a track pool
  2. translate_artists_to_prefs — infers the user's target vibe from their picks
  3. generate_dj_intro       — writes a short radio-DJ intro for the playlist

CRITICAL: classification is BATCHED into a single API call to stay well under
Gemini's 15 RPM free-tier limit. Never classify songs in a loop.

Every function degrades gracefully: if the key is missing or Gemini returns
malformed JSON, a deterministic heuristic fallback keeps the app running.
"""
import json
import re
from typing import Dict, List

from backend import config

# Allowed vocabularies (kept in sync with the recommender's scoring dimensions).
_GENRES = [
    "pop", "lofi", "rock", "jazz", "edm", "classical",
    "metal", "reggae", "hip hop", "blues", "folk", "world",
]
_MOODS = [
    "happy", "chill", "intense", "focused",
    "aggressive", "dramatic", "nostalgic",
]

# Lazily-initialized SDK model handle.
_model = None


def _get_model():
    """Configure and cache the Gemini model, or return None if unavailable."""
    global _model
    if _model is not None:
        return _model
    if not config.has_gemini():
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=config.GEMINI_API_KEY)
        _model = genai.GenerativeModel(config.GEMINI_MODEL)
        return _model
    except Exception:
        return None


def _generate_json(prompt: str):
    """
    Call Gemini with JSON response mode and parse the result.

    Returns the parsed object, or None on any failure (missing key, network
    error, unparseable output) so callers can fall back deterministically.
    """
    model = _get_model()
    if model is None:
        return None
    try:
        import google.generativeai as genai

        resp = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        text = (resp.text or "").strip()
        return _safe_json_loads(text)
    except Exception:
        return None


def _safe_json_loads(text: str):
    """Parse JSON, tolerating markdown code fences or stray prose."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip ```json fences and retry.
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Last resort: extract the first {...} or [...] block.
    match = re.search(r"(\[.*\]|\{.*\})", cleaned, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


# --------------------------------------------------------------------------
# Deterministic fallbacks (used when Gemini is unavailable or misbehaves).
# --------------------------------------------------------------------------
def _fallback_classification(track: Dict) -> Dict:
    """A neutral, deterministic attribute set so scoring can still proceed."""
    return {
        "genre": "pop",
        "mood": "chill",
        "energy": 0.5,
        "acousticness": 0.5,
        "valence": 0.5,
        "tempo_bpm": 110,
        "danceability": 0.5,
    }


def _coerce_classification(raw: Dict) -> Dict:
    """Clamp/validate one Gemini classification object into our schema."""
    def _num(key, default, lo=0.0, hi=1.0):
        try:
            return max(lo, min(hi, float(raw.get(key, default))))
        except (TypeError, ValueError):
            return default

    genre = str(raw.get("genre", "pop")).strip().lower()
    mood = str(raw.get("mood", "chill")).strip().lower()
    try:
        tempo = float(raw.get("tempo_bpm", 110))
    except (TypeError, ValueError):
        tempo = 110.0
    return {
        "genre": genre if genre in _GENRES else "pop",
        "mood": mood if mood in _MOODS else "chill",
        "energy": _num("energy", 0.5),
        "acousticness": _num("acousticness", 0.5),
        "valence": _num("valence", 0.5),
        "tempo_bpm": max(40.0, min(240.0, tempo)),
        "danceability": _num("danceability", 0.5),
    }


# --------------------------------------------------------------------------
# Agent 1: Batched Classifier
# --------------------------------------------------------------------------
def classify_tracks_batch(unclassified_tracks_list: List[Dict]) -> List[Dict]:
    """
    Classify a list of tracks in ONE batched Gemini call.

    Input:  [{"title": ..., "artist": ...}, ...]
    Output: parallel list of classified dicts (genre, mood, energy, ...),
            aligned by index with the input list.
    """
    if not unclassified_tracks_list:
        return []

    indexed = [
        {"id": i, "title": t.get("title", ""), "artist": t.get("artist", "")}
        for i, t in enumerate(unclassified_tracks_list)
    ]

    prompt = (
        "You are a music-analysis engine. Analyze these tracks and map each to "
        "our system parameters using your knowledge of the songs.\n\n"
        f"Input: {json.dumps(indexed, ensure_ascii=False)}\n\n"
        "Output ONLY a JSON array of objects, one per input id, with keys: "
        "id, "
        f"genre (one of {_GENRES}), "
        f"mood (one of {_MOODS}), "
        "energy (0.0-1.0), acousticness (0.0-1.0), valence (0.0-1.0), "
        "tempo_bpm (integer), danceability (0.0-1.0)."
    )

    parsed = _generate_json(prompt)

    # Build an id -> classification map from whatever Gemini returned.
    by_id: Dict[int, Dict] = {}
    if isinstance(parsed, list):
        for obj in parsed:
            if isinstance(obj, dict) and "id" in obj:
                try:
                    by_id[int(obj["id"])] = _coerce_classification(obj)
                except (TypeError, ValueError):
                    continue

    results: List[Dict] = []
    for i, track in enumerate(unclassified_tracks_list):
        results.append(by_id.get(i) or _fallback_classification(track))
    return results


# --------------------------------------------------------------------------
# Agent 2: Vibe Translator
# --------------------------------------------------------------------------
def translate_artists_to_prefs(artists: List[str]) -> Dict:
    """
    Infer the user's target vibe from their selected artists.

    Returns a dict shaped for the recommender's UserProfile:
        {favorite_genre, favorite_mood, target_energy, likes_acoustic}
    """
    prompt = (
        "Given these favorite artists, infer the listener's target music profile.\n"
        f"Artists: {json.dumps(artists, ensure_ascii=False)}\n\n"
        "Output ONLY a JSON object with keys: "
        f"favorite_genre (one of {_GENRES}), "
        f"favorite_mood (one of {_MOODS}), "
        "target_energy (0.0-1.0), likes_acoustic (true/false)."
    )

    parsed = _generate_json(prompt)
    if isinstance(parsed, dict):
        genre = str(parsed.get("favorite_genre", "pop")).strip().lower()
        mood = str(parsed.get("favorite_mood", "chill")).strip().lower()
        try:
            energy = max(0.0, min(1.0, float(parsed.get("target_energy", 0.6))))
        except (TypeError, ValueError):
            energy = 0.6
        likes_acoustic = bool(parsed.get("likes_acoustic", False))
        return {
            "favorite_genre": genre if genre in _GENRES else "pop",
            "favorite_mood": mood if mood in _MOODS else "chill",
            "target_energy": energy,
            "likes_acoustic": likes_acoustic,
        }

    # Deterministic fallback: a broadly agreeable, energetic pop profile.
    return {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.6,
        "likes_acoustic": False,
    }


# --------------------------------------------------------------------------
# Agent 3: DJ Intro
# --------------------------------------------------------------------------
def generate_dj_intro(user_name: str, artists: List[str], top_songs: List[Dict]) -> str:
    """Write a 2-3 sentence radio-DJ intro (<60 words) for the playlist."""
    top_title = top_songs[0].get("title", "your first track") if top_songs else "your first track"
    name = user_name.strip() or "friend"

    prompt = (
        f"Write a 2-3 sentence custom radio DJ intro for {name} based on their "
        f"love for {', '.join(artists)}. Mention they are about to hear "
        f'"{top_title}". Keep it under 60 words. Return ONLY the intro text as '
        'a JSON object: {"intro": "..."}.'
    )

    parsed = _generate_json(prompt)
    if isinstance(parsed, dict) and parsed.get("intro"):
        return str(parsed["intro"]).strip()

    # Deterministic fallback.
    return (
        f"Welcome to VibeFinder Radio, {name}! We tuned into your love for "
        f"{', '.join(artists)} and lined up a set made just for you. "
        f'First up: "{top_title}" — turn it up.'
    )
