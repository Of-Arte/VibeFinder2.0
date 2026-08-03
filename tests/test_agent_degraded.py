"""
Tests for the agent layer's request-scoped degradation flag.

These monkeypatch agent._generate_json so no live Gemini call is made. The flag
must trip only for *ranking-affecting* fallbacks (classifier / vibe translator),
not for the cosmetic DJ-intro fallback.
"""
import logging

import pytest

from backend import agent


@pytest.fixture(autouse=True)
def _reset_flag():
    """Every test starts from a clean (non-degraded) state."""
    agent.reset_degraded()
    yield
    agent.reset_degraded()


def _full_classification(idx):
    """A well-formed Gemini classification object for input id ``idx``."""
    return {
        "id": idx,
        "genre": "rock",
        "mood": "intense",
        "energy": 0.9,
        "acousticness": 0.1,
        "valence": 0.7,
        "tempo_bpm": 140,
        "danceability": 0.6,
    }


# --- Default / reset behaviour ---------------------------------------------
def test_is_degraded_defaults_to_false():
    assert agent.is_degraded() is False


def test_reset_clears_the_flag():
    agent.mark_degraded("something")
    assert agent.is_degraded() is True
    agent.reset_degraded()
    assert agent.is_degraded() is False


# --- Classifier ------------------------------------------------------------
def test_classifier_healthy_does_not_degrade(monkeypatch):
    tracks = [{"title": "A", "artist": "X"}, {"title": "B", "artist": "Y"}]
    monkeypatch.setattr(
        agent, "_generate_json",
        lambda prompt, max_output_tokens=None: [_full_classification(0), _full_classification(1)],
    )
    result = agent.classify_tracks_batch(tracks)
    assert agent.is_degraded() is False
    assert result[0]["energy"] == 0.9  # real value, not the 0.5 fallback


def test_classifier_total_outage_degrades(monkeypatch):
    tracks = [{"title": "A", "artist": "X"}, {"title": "B", "artist": "Y"}]
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    result = agent.classify_tracks_batch(tracks)
    assert agent.is_degraded() is True
    # Degraded, but the fallback must NOT be a shared constant: different
    # tracks must get different features so scores stay distinct.
    assert result[0]["energy"] != result[1]["energy"]


def test_fallback_never_collapses_to_a_constant(monkeypatch):
    """The core guarantee: N distinct tracks -> N distinct feature vectors.

    This is what keeps five same-artist songs from all scoring identically.
    """
    tracks = [
        {"title": t, "artist": "Billie Eilish"}
        for t in ("BIRDS OF A FEATHER", "WILDFLOWER", "CHIHIRO", "LUNCH", "SKINNY")
    ]
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    result = agent.classify_tracks_batch(tracks)

    def vector(c):
        return (c["energy"], c["valence"], c["danceability"],
                c["tempo_bpm"], c["acousticness"])

    vectors = [vector(c) for c in result]
    assert len(set(vectors)) == len(vectors)  # all five feature vectors differ


def test_fallback_is_deterministic(monkeypatch):
    """Same track -> same features on every run (stable, reproducible ranking)."""
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    a = agent.classify_tracks_batch([{"title": "CHIHIRO", "artist": "Billie Eilish"}])
    b = agent.classify_tracks_batch([{"title": "CHIHIRO", "artist": "Billie Eilish"}])
    assert a[0] == b[0]


def test_fallback_uses_real_deezer_bpm_when_present(monkeypatch):
    """A track carrying Deezer's real BPM should classify at that tempo."""
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    track = {"title": "WILDFLOWER", "artist": "Billie Eilish", "deezer_bpm": 92.0}
    result = agent.classify_tracks_batch([track])
    assert result[0]["tempo_bpm"] == 92.0


def test_classifier_partial_failure_degrades(monkeypatch):
    """Even one missing track means uniform scoring for it -> degraded."""
    tracks = [{"title": "A", "artist": "X"}, {"title": "B", "artist": "Y"}]
    # Gemini returns only id 0; id 1 is missing.
    monkeypatch.setattr(
        agent, "_generate_json", lambda prompt, max_output_tokens=None: [_full_classification(0)]
    )
    result = agent.classify_tracks_batch(tracks)
    assert agent.is_degraded() is True
    assert result[0]["energy"] == 0.9   # id 0 got real Gemini data
    assert result[1]["genre"] == "pop"  # id 1 fell back (derived, not constant)
    assert result[0] != result[1]       # the two tracks are not identical


def test_classifier_empty_pool_does_not_degrade(monkeypatch):
    # No tracks means nothing to classify and nothing to fall back on.
    called = {"n": 0}

    def _spy(prompt):
        called["n"] += 1
        return []

    monkeypatch.setattr(agent, "_generate_json", _spy)
    assert agent.classify_tracks_batch([]) == []
    assert agent.is_degraded() is False
    assert called["n"] == 0  # short-circuits before any API call


# --- Vibe translator -------------------------------------------------------
def test_vibe_healthy_does_not_degrade(monkeypatch):
    monkeypatch.setattr(
        agent, "_generate_json",
        lambda prompt, max_output_tokens=None: {
            "favorite_genre": "rock",
            "favorite_mood": "intense",
            "target_energy": 0.8,
            "likes_acoustic": True,
            "target_valence": 0.7,
            "target_danceability": 0.6,
            "target_acousticness": 0.2,
            "target_tempo_bpm": 130,
        },
    )
    vibe = agent.translate_artists_to_prefs(["Metallica"])
    assert agent.is_degraded() is False
    assert vibe["favorite_genre"] == "rock"
    assert vibe["target_valence"] == 0.7


def test_vibe_outage_degrades_and_returns_default_profile(monkeypatch):
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    vibe = agent.translate_artists_to_prefs(["Metallica"])
    assert agent.is_degraded() is True
    # Falls back to the broadly-agreeable default pop profile.
    assert vibe["favorite_genre"] == "pop"
    assert vibe["favorite_mood"] == "happy"
    # The continuous target_* keys still exist so the scorer stays whole.
    for key in ("target_valence", "target_danceability",
                "target_acousticness", "target_tempo_bpm"):
        assert key in vibe


# --- Scoping: DJ intro is cosmetic and must NOT trip the flag --------------
def test_dj_intro_fallback_does_not_degrade(monkeypatch):
    monkeypatch.setattr(agent, "_generate_json", lambda prompt, max_output_tokens=None: None)
    intro = agent.generate_dj_intro(["Adele"], [{"title": "Hello"}])
    assert isinstance(intro, str) and intro.strip()
    assert "Hello" in intro          # used the deterministic fallback text
    assert agent.is_degraded() is False  # cosmetic failure only


# --- Logging ---------------------------------------------------------------
def test_mark_degraded_emits_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="backend.agent"):
        agent.mark_degraded("classifier fell back for 3/5 tracks")
    assert any(
        "classifier fell back for 3/5 tracks" in rec.message
        for rec in caplog.records
    )
