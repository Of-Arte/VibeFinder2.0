"""
VibeFinder 2.0 FastAPI server.

Exposes POST /api/recommend, which orchestrates the full pipeline:
    Input -> Fetch (Deezer) -> Classifier -> Scorer -> DJ -> UI

Run with:  uvicorn backend.server:app --port 8000
"""
from typing import Dict, List, Tuple

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend import agent, config, deezer_client, ratelimit, __version__
from src.recommender import score_song

app = FastAPI(title="VibeFinder API", version=__version__)

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
    source: str  # "deezer"
    target_vibe: Dict
    dj_intro: str
    playlist: List[RecommendedTrack]
    # True when a ranking-affecting Gemini call fell back to constants, so the
    # UI can warn that scores may be uniform rather than personalized.
    degraded: bool = False


# --- Helpers ---------------------------------------------------------------
def _fetch_pool(selected_artists: List[str]) -> Tuple[List[Dict], str]:
    """
    Retrieve a raw track pool of 30-50 tracks from the keyless Deezer API.

    Returns (pool, source_name).
    """
    pool = deezer_client.fetch_tracks(
        selected_artists, target_pool=config.CLASSIFY_POOL_SIZE
    )
    return pool, "deezer"


def _classify_pool(pool: List[Dict]) -> List[Dict]:
    """
    Ensure every track in the pool has classified attributes.

    The whole pool goes to the batched Gemini classifier in a single API call.
    """
    if pool:
        classified = agent.classify_tracks_batch(pool)
        for track, attrs in zip(pool, classified):
            track.update(attrs)

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
    """Lightweight readiness probe reporting version and configured integrations."""
    return {
        "status": "ok",
        "version": __version__,
        "gemini": config.has_gemini(),
        "source": "deezer",
    }


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest, request: Request):
    """Full recommendation pipeline for a set of selected artists."""
    # 0. Per-client rate limit: avoid sending too many requests at once to Deezer,
    #    Gemini, or our backend server.
    client_id = request.client.host if request.client else "unknown"
    if not ratelimit.check(client_id):
        return JSONResponse(
            status_code=429,
            content={
                "detail": (
                    f"Rate limit reached. You can generate up to "
                    f"{config.RATE_LIMIT_MAX_REQUESTS} playlists per "
                    f"{config.RATE_LIMIT_WINDOW_SECONDS} seconds to prevent "
                    f"overloading the backend and external APIs. "
                    f"Please try again in a moment."
                )
            },
        )

    artists = [a.strip() for a in req.selected_artists if a and a.strip()]

    # Reset the request-scoped degradation flag before any Gemini calls.
    agent.reset_degraded()

    # 1. Fetch a raw track pool from Deezer.
    import requests
    from backend.deezer_client import DeezerError
    try:
        pool, source = _fetch_pool(artists)
    except (DeezerError, requests.RequestException, Exception) as e:
        import logging
        logging.getLogger(__name__).error("Deezer API fetch failed: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="The music metadata provider is currently unreachable. Please check your network connection and try again later."
        )

    # 2. Classify (batched Gemini, single API call).
    pool = _classify_pool(pool)

    # 3. Translate artist picks -> target vibe (Gemini vibe translator).
    target_vibe = agent.translate_artists_to_prefs(artists, pool)

    # 4. Score against the recommender core and take the top 5.
    playlist = _score_pool(pool, target_vibe, k=5)

    # 5. DJ intro over the ranked output. The user's name is deliberately NOT
    #    passed to the agent (untrusted free text -> prompt-injection risk); the
    #    UI greets the user by name separately using the returned user_name.
    dj_intro = agent.generate_dj_intro(artists, playlist)

    return RecommendResponse(
        user_name=req.user_name,
        source=source,
        target_vibe=target_vibe,
        dj_intro=dj_intro,
        playlist=[RecommendedTrack(**t) for t in playlist],
        degraded=agent.is_degraded(),
    )
