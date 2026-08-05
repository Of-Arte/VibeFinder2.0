"""
Integration test suite for FastAPI server layer (backend/server.py).

Tests end-to-end pipeline execution, response shapes, fallback handling,
error codes (503), rate limiting (429), and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend import agent, deezer_client, ratelimit, config

client = TestClient(app)

# Sample track pool fixture for Deezer mocking
MOCK_DEEZER_POOL = [
    {
        "id": 101,
        "title": "One More Time",
        "artist": "Daft Punk",
        "deezer_bpm": 123.0,
        "deezer_rank": 850000,
        "cover_url": "http://example.com/cover1.jpg",
        "preview_url": "http://example.com/preview1.mp3",
    },
    {
        "id": 102,
        "title": "Around the World",
        "artist": "Daft Punk",
        "deezer_bpm": 121.0,
        "deezer_rank": 800000,
        "cover_url": "http://example.com/cover2.jpg",
        "preview_url": "http://example.com/preview2.mp3",
    },
    {
        "id": 103,
        "title": "D.A.N.C.E.",
        "artist": "Justice",
        "deezer_bpm": 115.0,
        "deezer_rank": 780000,
        "cover_url": "http://example.com/cover3.jpg",
        "preview_url": "http://example.com/preview3.mp3",
    },
    {
        "id": 104,
        "title": "Stress",
        "artist": "Justice",
        "deezer_bpm": 130.0,
        "deezer_rank": 700000,
        "cover_url": "http://example.com/cover4.jpg",
        "preview_url": "http://example.com/preview4.mp3",
    },
    {
        "id": 105,
        "title": "Genesis",
        "artist": "Justice",
        "deezer_bpm": 118.0,
        "deezer_rank": 720000,
        "cover_url": "http://example.com/cover5.jpg",
        "preview_url": "http://example.com/preview5.mp3",
    },
    {
        "id": 106,
        "title": "Harder Better Faster Stronger",
        "artist": "Daft Punk",
        "deezer_bpm": 123.0,
        "deezer_rank": 880000,
        "cover_url": "http://example.com/cover6.jpg",
        "preview_url": "http://example.com/preview6.mp3",
    },
]


def test_health_endpoint():
    """Verify GET /api/health returns ready status and environment state."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "gemini" in data
    assert isinstance(data["gemini"], bool)
    assert data["source"] == "deezer"


def test_recommend_successful_flow(monkeypatch):
    """Verify POST /api/recommend returns complete schema and top-5 ranked playlist."""
    # Reset rate limiting state before test
    ratelimit._HITS.clear()

    # Mock Deezer track fetcher
    monkeypatch.setattr(deezer_client, "fetch_tracks", lambda artists, target_pool=40: list(MOCK_DEEZER_POOL))

    # Mock agent methods to return non-degraded responses
    def mock_classify(pool):
        return [
            {
                "genre": "edm",
                "mood": "happy",
                "energy": 0.85,
                "acousticness": 0.1,
                "valence": 0.8,
                "tempo_bpm": track.get("deezer_bpm", 120.0),
                "danceability": 0.9,
            }
            for track in pool
        ]

    def mock_translate(artists, pool=None):
        return {
            "favorite_genre": "edm",
            "favorite_mood": "happy",
            "target_energy": 0.8,
            "likes_acoustic": False,
            "target_valence": 0.75,
            "target_danceability": 0.85,
            "target_acousticness": 0.15,
            "target_tempo_bpm": 120.0,
        }

    monkeypatch.setattr(agent, "classify_tracks_batch", mock_classify)
    monkeypatch.setattr(agent, "translate_artists_to_prefs", mock_translate)
    monkeypatch.setattr(agent, "generate_dj_intro", lambda artists, songs: "Welcome to French Touch Radio!")

    payload = {
        "user_name": "Alex",
        "selected_artists": ["Daft Punk", "Justice"],
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["user_name"] == "Alex"
    assert data["source"] == "deezer"
    assert data["dj_intro"] == "Welcome to French Touch Radio!"
    assert data["degraded"] is False

    playlist = data["playlist"]
    assert len(playlist) == 5

    # Verify score ordering (descending)
    scores = [track["score"] for track in playlist]
    assert scores == sorted(scores, reverse=True)

    # Verify track fields & types
    first_track = playlist[0]
    assert "title" in first_track
    assert "artist" in first_track
    assert "genre" in first_track
    assert "mood" in first_track
    assert isinstance(first_track["energy"], float)
    assert isinstance(first_track["score"], float)
    assert isinstance(first_track["reasons"], list)


def test_recommend_degraded_flow(monkeypatch):
    """Verify POST /api/recommend gracefully falls back and sets degraded=True when Gemini fails."""
    ratelimit._HITS.clear()
    monkeypatch.setattr(deezer_client, "fetch_tracks", lambda artists, target_pool=40: list(MOCK_DEEZER_POOL))

    # Force Gemini generation failure so fallback & degradation logic executes
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)

    payload = {
        "user_name": "Sam",
        "selected_artists": ["Daft Punk"],
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["user_name"] == "Sam"
    assert data["degraded"] is True
    assert "VibeFinder Radio" in data["dj_intro"] or len(data["dj_intro"]) > 0
    assert len(data["playlist"]) == 5


def test_recommend_empty_artist_list(monkeypatch):
    """Verify POST /api/recommend handles empty/blank artist list without crashing."""
    ratelimit._HITS.clear()
    monkeypatch.setattr(deezer_client, "fetch_tracks", lambda artists, target_pool=40: list(MOCK_DEEZER_POOL))

    payload = {
        "user_name": "Guest",
        "selected_artists": ["  ", ""],
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user_name"] == "Guest"
    assert len(data["playlist"]) == 5


def test_recommend_deezer_outage_503(monkeypatch):
    """Verify POST /api/recommend returns HTTP 503 Service Unavailable on Deezer API failure."""
    ratelimit._HITS.clear()

    def mock_fetch_error(artists, target_pool=40):
        raise deezer_client.DeezerError("Deezer network unreachable")

    monkeypatch.setattr(deezer_client, "fetch_tracks", mock_fetch_error)

    payload = {
        "user_name": "Test",
        "selected_artists": ["Daft Punk"],
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 503
    data = response.json()
    assert "The music metadata provider is currently unreachable" in data["detail"]


def test_recommend_rate_limiting(monkeypatch):
    """Verify client is throttled with HTTP 429 when exceeding RATE_LIMIT_MAX_REQUESTS."""
    ratelimit._HITS.clear()
    monkeypatch.setattr(deezer_client, "fetch_tracks", lambda artists, target_pool=40: list(MOCK_DEEZER_POOL))
    monkeypatch.setattr(config, "RATE_LIMIT_MAX_REQUESTS", 2)

    payload = {"user_name": "Spammer", "selected_artists": ["Daft Punk"]}

    # Request 1: OK
    r1 = client.post("/api/recommend", json=payload)
    assert r1.status_code == 200

    # Request 2: OK
    r2 = client.post("/api/recommend", json=payload)
    assert r2.status_code == 200

    # Request 3: Exceeds limit -> 429
    r3 = client.post("/api/recommend", json=payload)
    assert r3.status_code == 429
    assert "Rate limit reached" in r3.json()["detail"]
