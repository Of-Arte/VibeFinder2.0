"""
Unified Gemini agent layer for VibeFinder 2.0.

Three independent agent functions built on the google-generativeai SDK:
  1. classify_tracks_batch  — dynamically infers audio features for a track pool
  2. translate_artists_to_prefs — infers the user's target vibe from their picks
  3. generate_dj_intro — writes a short radio-DJ intro for the playlist

CRITICAL: classification is BATCHED into a single API call to stay well under
Gemini's 15 RPM free-tier limit. Never classify songs in a loop.

Every function degrades gracefully: if the key is missing or Gemini returns
malformed JSON, a deterministic heuristic fallback keeps the app running.
"""
import hashlib
import json
import logging
import re
import threading
from typing import Dict, List

from backend import config

logger = logging.getLogger(__name__)

# Request-scoped degradation flag. FastAPI runs sync endpoints on a per-request
# worker thread, so thread-local storage isolates one request from another.
# The server resets this at the start of a request and reads it at the end to
# tell the UI whether the ranking ran on real Gemini data or constant fallbacks.
_state = threading.local()


def reset_degraded() -> None:
    """Clear the degradation flag at the start of a request."""
    _state.degraded = False


def mark_degraded(reason: str) -> None:
    """Record that a ranking-affecting Gemini call fell back to constants."""
    _state.degraded = True
    logger.warning("VibeFinder degraded to fallback: %s", reason)


def is_degraded() -> bool:
    """True if any ranking-affecting Gemini call fell back this request."""
    return getattr(_state, "degraded", False)

# Allowed vocabularies (kept in sync with the recommender's scoring dimensions).
_GENRES = [
    "pop", "lofi", "rock", "jazz", "edm", "classical",
    "metal", "reggae", "hip hop", "blues", "folk", "world",
]
_MOODS = [
    "happy", "chill", "intense", "focused",
    "aggressive", "dramatic", "nostalgic",
]

# Map curated/common artists to standard genres for deterministic degraded mode lookup.
_ARTIST_GENRE_MAP = {
    "taylor swift": "pop",
    "billie eilish": "pop",
    "kendrick lamar": "hip hop",
    "daft punk": "edm",
    "radiohead": "rock",
    "miles davis": "jazz",
    "iron maiden": "metal",
    "bob marley": "reggae",
    "adele": "pop",
    "the weeknd": "pop",
    "fleet foxes": "folk",
    "ravi shankar": "world",
    "nujabes": "lofi",
    "beethoven": "classical",
    "arctic monkeys": "rock",
    "calvin harris": "edm",
}


def _get_fallback_artist_genre(artist_name: str) -> str:
    """Resolve an artist name to a genre in degraded/fallback mode.

    Looks up curated artist mapping first. Next, attempts dynamic lookup
    via the Deezer API. If both fail, hashes the name onto ``_GENRES``.
    """
    clean_name = (artist_name or "").strip().lower()
    if clean_name in _ARTIST_GENRE_MAP:
        return _ARTIST_GENRE_MAP[clean_name]
    if not clean_name:
        return "pop"
    
    from backend import deezer_client
    dynamic_genre = deezer_client.fetch_artist_genre(clean_name)
    if dynamic_genre:
        return dynamic_genre

    idx = int(_feature_hash(clean_name, "genre") * len(_GENRES)) % len(_GENRES)
    return _GENRES[idx]


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
        logger.warning(
            "Failed to initialise Gemini model %r; using fallbacks.",
            config.GEMINI_MODEL, exc_info=True,
        )
        return None


def _generate_json(prompt: str, max_output_tokens: int = None):
    """
    Call Gemini with JSON response mode and parse the result.

    Returns the parsed object, or None on any failure (missing key, network
    error, unparseable output) so callers can fall back deterministically.
    ``max_output_tokens`` caps the response so large batches never truncate.
    """
    model = _get_model()
    if model is None:
        return None
    try:
        import google.generativeai as genai

        gen_config = genai.types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.4,
            max_output_tokens=max_output_tokens,
        )
        resp = model.generate_content(prompt, generation_config=gen_config)
        text = (resp.text or "").strip()
        parsed = _safe_json_loads(text)
        if parsed is None:
            logger.warning("Gemini returned unparseable output: %r", text[:200])
        return parsed
    except Exception:
        logger.warning("Gemini generate_content call failed.", exc_info=True)
        return None


def _safe_json_loads(text: str):
    """Parse JSON, tolerating markdown code fences, stray prose, or trailing commas."""
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
    # Try stripping trailing commas from the cleaned JSON
    try:
        return json.loads(re.sub(r',\s*([\]}])', r'\1', cleaned))
    except json.JSONDecodeError:
        pass
    # Last resort: extract the first {...} or [...] block.
    match = re.search(r"(\[.*\]|\{.*\})", cleaned, flags=re.DOTALL)
    if match:
        extracted = match.group(1)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            try:
                return json.loads(re.sub(r',\s*([\]}])', r'\1', extracted))
            except json.JSONDecodeError:
                return None
    return None


# --------------------------------------------------------------------------
# Deterministic fallbacks (used when Gemini is unavailable or misbehaves).
# --------------------------------------------------------------------------
def _feature_hash(seed: str, salt: str) -> float:
    """
    Deterministic pseudo-value in [0, 1) derived from a track identity and a
    feature name. Same track + same feature always yields the same number, but
    different tracks (or features) spread across the range — so a fallback pool
    gets *distinct* audio features instead of one repeated constant.
    """
    digest = hashlib.sha256(f"{salt}:{seed}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0x100000000


def _fallback_classification(track: Dict) -> Dict:
    """
    Deterministic per-track attributes for when Gemini is unavailable.

    This must NEVER return the same values for different tracks: identical
    features collapse every score to the same number and make the ranking
    meaningless. Real Deezer signal is used where present (bpm, popularity);
    everything else is spread deterministically by a hash of the track identity.
    """
    seed = f"{track.get('artist', '')}|{track.get('title', '')}".strip().lower()

    # Tempo: use Deezer's real BPM when it reported one, else spread 70-180 BPM.
    bpm = float(track.get("deezer_bpm") or 0)
    tempo = bpm if bpm > 0 else 70.0 + _feature_hash(seed, "tempo") * 110.0

    # Popularity (0..~1M) nudges energy/danceability upward for bigger hits.
    rank = int(track.get("deezer_rank") or 0)
    popularity = max(0.0, min(1.0, rank / 900000.0)) if rank else 0.5

    # Continuous features: hash-spread, lightly anchored to real signal so the
    # values are plausible, not just noise.
    energy = round(0.35 + 0.55 * _feature_hash(seed, "energy") + 0.10 * popularity, 3)
    valence = round(_feature_hash(seed, "valence"), 3)
    danceability = round(0.30 + 0.50 * _feature_hash(seed, "dance") + 0.10 * popularity, 3)
    acousticness = round(_feature_hash(seed, "acoustic") * 0.8, 3)
    energy = min(1.0, energy)
    danceability = min(1.0, danceability)

    # Mood derived from the derived vibe so it reads coherently.
    if energy >= 0.6 and valence >= 0.55:
        mood = "happy"
    elif energy >= 0.6:
        mood = "intense"
    elif valence < 0.4:
        mood = "nostalgic"
    else:
        mood = "chill"

    # Genre derived from artist mapping or deterministic identity hash.
    genre = _get_fallback_artist_genre(track.get("artist", ""))

    return {
        "genre": genre,
        "mood": mood,
        "energy": energy,
        "acousticness": acousticness,
        "valence": valence,
        "tempo_bpm": round(tempo, 1),
        "danceability": danceability,
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
def _classify_chunk(chunk: List[Dict]) -> Dict[int, Dict]:
    """
    Classify one chunk of tracks in a single Gemini call.

    Returns an index->classification map (indices are chunk-local, 0..len-1).
    Missing indices are left for the caller to fill via the fallback, so a
    partial or failed response degrades only the tracks it actually dropped.
    """
    indexed = [
        {"id": i, "title": t.get("title", ""), "artist": t.get("artist", "")}
        for i, t in enumerate(chunk)
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

    parsed = _generate_json(prompt, max_output_tokens=config.CLASSIFY_MAX_OUTPUT_TOKENS)

    by_id: Dict[int, Dict] = {}
    if isinstance(parsed, list):
        for obj in parsed:
            if isinstance(obj, dict) and "id" in obj:
                try:
                    by_id[int(obj["id"])] = _coerce_classification(obj)
                except (TypeError, ValueError):
                    continue
    return by_id


def classify_tracks_batch(unclassified_tracks_list: List[Dict]) -> List[Dict]:
    """
    Classify a list of tracks using chunked Gemini calls.

    The pool is split into chunks of config.CLASSIFY_BATCH_SIZE so a single
    failing chunk degrades only its own tracks (each to a distinct fallback),
    rather than collapsing the entire pool. Never issues a call per track.

    Input:  [{"title": ..., "artist": ...}, ...]
    Output: parallel list of classified dicts, aligned by index with the input.
    """
    if not unclassified_tracks_list:
        return []

    batch_size = max(1, config.CLASSIFY_BATCH_SIZE)
    results: List[Dict] = []
    missing = 0

    for start in range(0, len(unclassified_tracks_list), batch_size):
        chunk = unclassified_tracks_list[start:start + batch_size]
        by_id = _classify_chunk(chunk)
        for local_i, track in enumerate(chunk):
            classification = by_id.get(local_i)
            if classification is None:
                classification = _fallback_classification(track)
                missing += 1
            results.append(classification)

    # If any track fell back the ranking can't discriminate it on real signal,
    # so flag the request as degraded.
    if missing:
        mark_degraded(
            f"classifier fell back for {missing}/{len(unclassified_tracks_list)} tracks"
        )
    return results


# --------------------------------------------------------------------------
# Agent 2: Vibe Translator
# --------------------------------------------------------------------------
def _calculate_fallback_target_vibe(artists: List[str], pool: List[Dict]) -> Dict:
    """
    Compute the user's target vibe profile from the features of the tracks in the pool
    that match the selected artists.
    """
    from collections import Counter

    # Filter pool to tracks belonging to selected artists
    selected_set = {a.strip().lower() for a in artists}
    matching_tracks = [
        t for t in pool
        if t.get("artist", "").strip().lower() in selected_set
    ]
    # If no matches, fallback to the entire pool
    if not matching_tracks:
        matching_tracks = pool

    if not matching_tracks:
        # Final fallback if pool is empty
        fallback_genre = _get_fallback_artist_genre(artists[0] if artists else "")
        return {
            "favorite_genre": fallback_genre,
            "favorite_mood": "happy",
            "target_energy": 0.6,
            "likes_acoustic": False,
            "target_valence": 0.6,
            "target_danceability": 0.6,
            "target_acousticness": 0.3,
            "target_tempo_bpm": 118.0,
        }

    # Extract genres and moods
    genres = [t.get("genre") for t in matching_tracks if t.get("genre")]
    moods = [t.get("mood") for t in matching_tracks if t.get("mood")]

    if genres:
        favorite_genre, _ = Counter(genres).most_common(1)[0]
    else:
        favorite_genre = _get_fallback_artist_genre(artists[0] if artists else "")

    if moods:
        favorite_mood, _ = Counter(moods).most_common(1)[0]
    else:
        favorite_mood = "happy"

    energies = [float(t.get("energy", 0.5)) for t in matching_tracks]
    valences = [float(t.get("valence", 0.5)) for t in matching_tracks]
    danceabilities = [float(t.get("danceability", 0.5)) for t in matching_tracks]
    acousticnesses = [float(t.get("acousticness", 0.5)) for t in matching_tracks]
    tempos = [float(t.get("tempo_bpm", 110.0)) for t in matching_tracks]

    target_energy = round(sum(energies) / len(energies), 3)
    target_valence = round(sum(valences) / len(valences), 3)
    target_danceability = round(sum(danceabilities) / len(danceabilities), 3)
    target_acousticness = round(sum(acousticnesses) / len(acousticnesses), 3)
    target_tempo_bpm = round(sum(tempos) / len(tempos), 1)

    return {
        "favorite_genre": favorite_genre,
        "favorite_mood": favorite_mood,
        "target_energy": target_energy,
        "likes_acoustic": target_acousticness >= 0.5,
        "target_valence": target_valence,
        "target_danceability": target_danceability,
        "target_acousticness": target_acousticness,
        "target_tempo_bpm": target_tempo_bpm,
    }


def translate_artists_to_prefs(artists: List[str], pool: List[Dict] = None) -> Dict:
    """
    Infer the user's target vibe from their selected artists.

    Returns a dict shaped for the recommender's scorer:
        {favorite_genre, favorite_mood, target_energy, likes_acoustic,
         target_valence, target_danceability, target_acousticness,
         target_tempo_bpm}

    The continuous target_* fields let the recommender score valence,
    danceability, tempo, and acousticness proximity — the features that
    actually separate tracks within a single-genre pool.
    """
    prompt = (
        "Given these favorite artists, infer the listener's target music profile.\n"
        f"Artists: {json.dumps(artists, ensure_ascii=False)}\n\n"
        "Output ONLY a JSON object with keys: "
        f"favorite_genre (one of {_GENRES}), "
        f"favorite_mood (one of {_MOODS}), "
        "target_energy (0.0-1.0), likes_acoustic (true/false), "
        "target_valence (0.0-1.0), target_danceability (0.0-1.0), "
        "target_acousticness (0.0-1.0), target_tempo_bpm (integer 40-240)."
    )

    def _unit(value, default: float) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default

    parsed = _generate_json(prompt)
    if isinstance(parsed, dict):
        genre = str(parsed.get("favorite_genre", "pop")).strip().lower()
        mood = str(parsed.get("favorite_mood", "chill")).strip().lower()
        try:
            tempo = max(40.0, min(240.0, float(parsed.get("target_tempo_bpm", 110))))
        except (TypeError, ValueError):
            tempo = 110.0
        return {
            "favorite_genre": genre if genre in _GENRES else "pop",
            "favorite_mood": mood if mood in _MOODS else "chill",
            "target_energy": _unit(parsed.get("target_energy"), 0.6),
            "likes_acoustic": bool(parsed.get("likes_acoustic", False)),
            "target_valence": _unit(parsed.get("target_valence"), 0.5),
            "target_danceability": _unit(parsed.get("target_danceability"), 0.5),
            "target_acousticness": _unit(parsed.get("target_acousticness"), 0.5),
            "target_tempo_bpm": tempo,
        }

    # Deterministic fallback: profile calculated via algorithm from the pool
    mark_degraded("vibe translation fell back to the default artist-derived profile")
    if pool:
        return _calculate_fallback_target_vibe(artists, pool)

    fallback_genre = _get_fallback_artist_genre(artists[0] if artists else "")
    return {
        "favorite_genre": fallback_genre,
        "favorite_mood": "happy",
        "target_energy": 0.6,
        "likes_acoustic": False,
        "target_valence": 0.6,
        "target_danceability": 0.6,
        "target_acousticness": 0.3,
        "target_tempo_bpm": 118.0,
    }


# --------------------------------------------------------------------------
# Agent 3: DJ Intro
# --------------------------------------------------------------------------
def generate_dj_intro(artists: List[str], top_songs: List[Dict]) -> str:
    """Write a 2-3 sentence radio-DJ intro (<60 words) for the playlist.

    SECURITY: the listener's name is intentionally NOT used here. It is
    untrusted free-text input, and passing it to the LLM would be a
    prompt-injection vector. Personalization comes entirely from the (curated,
    safe) selected artists and the top track; the intro never addresses the
    listener by name. The UI still greets the user by name separately, using
    the name only as display text.
    """
    top_title = top_songs[0].get("title", "your first track") if top_songs else "your first track"

    prompt = (
        "Write a 2-3 sentence custom radio DJ intro for a listener based on "
        f"their love for {', '.join(artists)}. Do NOT address the listener by "
        "name or invent a name; speak to them generically (e.g. \"you\"). "
        f'Mention they are about to hear "{top_title}". Keep it under 60 words. '
        'Return ONLY the intro text as a JSON object: {"intro": "..."}.'
    )

    parsed = _generate_json(prompt)
    if isinstance(parsed, dict) and parsed.get("intro"):
        return str(parsed["intro"]).strip()

    # Deterministic fallback (no name referenced).
    return (
        "Welcome to VibeFinder Radio! We tuned into your love for "
        f"{', '.join(artists)} and lined up a set made just for you. "
        f'First up: "{top_title}" — turn it up.'
    )
