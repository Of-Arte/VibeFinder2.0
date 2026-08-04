import pytest
from backend import agent

def test_legacy_fallback_no_pool(monkeypatch):
    """Verify that when no pool is passed, legacy hardcoded fallback is used."""
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    vibe = agent.translate_artists_to_prefs(["Taylor Swift"])
    assert vibe["favorite_genre"] == "pop"
    assert vibe["favorite_mood"] == "happy"
    assert vibe["target_energy"] == 0.6
    assert vibe["target_valence"] == 0.6
    assert vibe["target_danceability"] == 0.6
    assert vibe["target_acousticness"] == 0.3
    assert vibe["target_tempo_bpm"] == 118.0
    assert vibe["likes_acoustic"] is False

def test_dynamic_fallback_matching_artists(monkeypatch):
    """Verify that fallback uses average/mode of matching artist tracks in the pool."""
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    
    pool = [
        # Match "Taylor Swift" (case insensitive)
        {"artist": "Taylor Swift", "genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.9, "danceability": 0.7, "acousticness": 0.1, "tempo_bpm": 120.0},
        {"artist": "taylor swift", "genre": "pop", "mood": "chill", "energy": 0.6, "valence": 0.7, "danceability": 0.5, "acousticness": 0.3, "tempo_bpm": 100.0},
        # Match "The Weeknd" (case insensitive)
        {"artist": "The Weeknd", "genre": "pop", "mood": "chill", "energy": 0.4, "valence": 0.5, "danceability": 0.9, "acousticness": 0.2, "tempo_bpm": 110.0},
        # Non-matching artist (should be ignored since we have matching ones)
        {"artist": "Iron Maiden", "genre": "metal", "mood": "intense", "energy": 0.95, "valence": 0.1, "danceability": 0.3, "acousticness": 0.05, "tempo_bpm": 160.0},
    ]

    vibe = agent.translate_artists_to_prefs(["Taylor Swift", "The Weeknd"], pool=pool)

    # Mode calculations:
    # genres: ["pop", "pop", "pop"] -> "pop"
    # moods: ["happy", "chill", "chill"] -> "chill"
    assert vibe["favorite_genre"] == "pop"
    assert vibe["favorite_mood"] == "chill"

    # Mean calculations:
    # energy: (0.8 + 0.6 + 0.4) / 3 = 0.6
    # valence: (0.9 + 0.7 + 0.5) / 3 = 0.7
    # danceability: (0.7 + 0.5 + 0.9) / 3 = 0.7
    # acousticness: (0.1 + 0.3 + 0.2) / 3 = 0.2
    # tempo_bpm: (120.0 + 100.0 + 110.0) / 3 = 110.0
    assert vibe["target_energy"] == pytest.approx(0.6)
    assert vibe["target_valence"] == pytest.approx(0.7)
    assert vibe["target_danceability"] == pytest.approx(0.7)
    assert vibe["target_acousticness"] == pytest.approx(0.2)
    assert vibe["target_tempo_bpm"] == pytest.approx(110.0)
    assert vibe["likes_acoustic"] is False

def test_dynamic_fallback_no_matching_artists(monkeypatch):
    """Verify that if no artists match, it aggregates the entire pool."""
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    
    pool = [
        {"artist": "Taylor Swift", "genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.8, "danceability": 0.8, "acousticness": 0.6, "tempo_bpm": 120.0},
        {"artist": "The Weeknd", "genre": "pop", "mood": "happy", "energy": 0.4, "valence": 0.4, "danceability": 0.4, "acousticness": 0.6, "tempo_bpm": 100.0},
    ]

    vibe = agent.translate_artists_to_prefs(["Iron Maiden"], pool=pool)

    # Mode: "pop", "happy"
    # Mean:
    # energy: (0.8 + 0.4) / 2 = 0.6
    # acousticness: (0.6 + 0.6) / 2 = 0.6 >= 0.5 -> likes_acoustic should be True
    assert vibe["favorite_genre"] == "pop"
    assert vibe["favorite_mood"] == "happy"
    assert vibe["target_energy"] == pytest.approx(0.6)
    assert vibe["target_acousticness"] == pytest.approx(0.6)
    assert vibe["likes_acoustic"] is True

def test_dynamic_fallback_empty_pool(monkeypatch):
    """Verify that if the pool is empty, it uses the fallback defaults."""
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    vibe = agent.translate_artists_to_prefs(["Taylor Swift"], pool=[])
    assert vibe["favorite_genre"] == "pop"
    assert vibe["favorite_mood"] == "happy"
    assert vibe["target_energy"] == 0.6
