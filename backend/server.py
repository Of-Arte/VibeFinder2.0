"""
VibeFinder 2.0 FastAPI server.

Exposes POST /api/recommend, which orchestrates the full pipeline:
    Input -> Fetch (Spotify/Deezer) -> Cache -> Classifier -> Scorer -> DJ -> UI

Run with:  uvicorn backend.server:app --port 8000
"""
from typing import Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import agent, cache, config, deezer_client, spotify_client
from src.recommender import score_song

app = FastAPI(title="VibeFinder 2.0 API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / response schemas -------------------------------------------
class RecommendRequest(BaseModel):
    user_name: str = Field(default="", examples=["Alex"])
    selected_artists: List[str] = Field(
        default_factory=list, examples=[["Daft Punk", "The Weeknd", "Justice"]]
    )


class RecommendedTrack(BaseModel):
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    cover_url: str
    preview_url: str
    score: float
    reasons: List[str]


class RecommendResponse(BaseModel):
    user_name: str
    source: str  # "spotify" | "deezer"
    target_vibe: Dict
    dj_intro: str
    playlist: List[RecommendedTrack]


# --- Helpers ---------------------------------------------------------------
def _fetch_pool(selected_artists: List[str]) -> (List[Dict], str):
    """
    Retrieve a raw track pool, preferring Spotify and falling back to Deezer.

    Returns (pool, source_name).
    """
    if config.has_spotify_credentials():
        try:
            pool = spotify_client.fetch_tracks(selected_artists, limit=40)
            if pool:
                return pool, "spotify"
        except spotify_client.SpotifyError:
            pass  # Fall through to Deezer.

    pool = deezer_client.fetch_tracks(selected_artists, target_pool=40)
    return pool, "deezer"


def _classify_pool(pool: List[Dict]) -> List[Dict]:
    """
    Ensure every track in the pool has classified attributes.

    Uses the cache first; only the cache-miss tracks go to the batched
    Gemini classifier (a single API call), then results are cached.
    """
    store = cache.load_cache()

    unclassified: List[Dict] = []
    unclassified_idx: List[int] = []

    for i, track in enumerate(pool):
        cached = cache.get_cached(store, track["artist"], track["title"])
        if cached:
            track.update(cached)
        else:
            unclassified.append(track)
            unclassified_idx.append(i)

    if unclassified:
        classified = agent.classify_tracks_batch(unclassified)
        for local_i, attrs in enumerate(classified):
            track = pool[unclassified_idx[local_i]]
            track.update(attrs)
            cache.put_cached(store, track["artist"], track["title"], attrs)
        cache.save_cache(store)

    return pool


def _score_pool(pool: List[Dict], target_vibe: Dict, k: int = 5) -> List[Dict]:
    """Score every classified track against the target vibe and return the top k."""
    scored = []
    for track in pool:
        score, reasons = score_song(target_vibe, track)
        scored.append((track, score, reasons))
    scored.sort(key=lambda item: item[1], reverse=True)

    top: List[Dict] = []
    for track, score, reasons in scored[:k]:
        top.append(
            {
                "title": track.get("title", ""),
                "artist": track.get("artist", ""),
                "genre": track.get("genre", ""),
                "mood": track.get("mood", ""),
                "energy": float(track.get("energy", 0.5)),
                "tempo_bpm": float(track.get("tempo_bpm", 110)),
                "valence": float(track.get("valence", 0.5)),
                "danceability": float(track.get("danceability", 0.5)),
                "acousticness": float(track.get("acousticness", 0.5)),
                "cover_url": track.get("cover_url", ""),
                "preview_url": track.get("preview_url", ""),
                "score": score,
                "reasons": reasons,
            }
        )
    return top


# --- Routes ----------------------------------------------------------------
@app.get("/api/health")
def health() -> Dict:
    """Lightweight readiness probe reporting which integrations are configured."""
    return {
        "status": "ok",
        "gemini": config.has_gemini(),
        "spotify": config.has_spotify_credentials(),
    }


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest) -> RecommendResponse:
    """Full recommendation pipeline for a set of selected artists."""
    artists = [a.strip() for a in req.selected_artists if a and a.strip()]

    # 1. Fetch a raw track pool (Spotify primary, Deezer fallback).
    pool, source = _fetch_pool(artists)

    # 2. Classify (cache-first, batched Gemini for misses).
    pool = _classify_pool(pool)

    # 3. Translate artist picks -> target vibe (Gemini vibe translator).
    target_vibe = agent.translate_artists_to_prefs(artists)

    # 4. Score against the recommender core and take the top 5.
    playlist = _score_pool(pool, target_vibe, k=5)

    # 5. DJ intro over the ranked output.
    dj_intro = agent.generate_dj_intro(req.user_name, artists, playlist)

    return RecommendResponse(
        user_name=req.user_name,
        source=source,
        target_vibe=target_vibe,
        dj_intro=dj_intro,
        playlist=[RecommendedTrack(**t) for t in playlist],
    )
