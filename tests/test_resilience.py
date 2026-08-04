import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend import agent, deezer_client
import requests

client = TestClient(app)

def test_dynamic_fallback_genre_success(monkeypatch):
    """Verify that _get_fallback_artist_genre dynamically queries Deezer when Gemini is offline."""
    called_search = False
    called_albums = False

    def mock_search(name):
        nonlocal called_search
        called_search = True
        return "12345"

    def mock_get(path, params=None):
        nonlocal called_albums
        called_albums = True
        # Path: /artist/12345/albums
        return {"data": [{"genre_id": 464}]}  # Metal

    monkeypatch.setattr(deezer_client, "_search_artist_id", mock_search)
    monkeypatch.setattr(deezer_client, "_get", mock_get)

    genre = agent._get_fallback_artist_genre("Some Metal Artist")
    assert genre == "metal"
    assert called_search is True
    assert called_albums is True


def test_dynamic_fallback_genre_failure(monkeypatch):
    """Verify that if Deezer dynamic lookup fails/raises, we still fall back to name hash."""
    def mock_search(name):
        raise RuntimeError("Network offline")

    monkeypatch.setattr(deezer_client, "_search_artist_id", mock_search)

    # Some Metal Artist hashes to a default genre, let's verify we get a genre
    genre = agent._get_fallback_artist_genre("Some Random Artist")
    assert genre in agent._GENRES


def test_server_deezer_outage_returns_503(monkeypatch):
    """Verify that if Deezer is unreachable, the server returns 503 Service Unavailable."""
    def mock_fetch_tracks(artists, target_pool=40):
        raise deezer_client.DeezerError("Deezer API is offline.")

    monkeypatch.setattr(deezer_client, "fetch_tracks", mock_fetch_tracks)

    response = client.post(
        "/api/recommend",
        json={"user_name": "Test User", "selected_artists": ["Taylor Swift"]}
    )
    assert response.status_code == 503
    data = response.json()
    assert "The music metadata provider is currently unreachable" in data["detail"]
