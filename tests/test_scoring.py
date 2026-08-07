"""
Unit tests for the refactored scoring mechanism in src/recommender.py.

These focus on score_song and its component scorers rather than end-to-end
recommendation. A candidate pool made up entirely of one artist is treated as
valid input here — the scorer's job is to *rank* whatever pool it is given, not
to enforce artist diversity (that concern lives in the retrieval layer).
"""
import pytest

from src.recommender import (
    score_song,
    recommend_songs,
    ScoringWeights,
    DEFAULT_WEIGHTS,
    Recommender,
    Song,
    UserProfile,
)


# --- Helpers ---------------------------------------------------------------
def make_song(**overrides):
    """A fully-specified track dict; override individual audio features per test."""
    base = {
        "id": 1,
        "title": "Track",
        "artist": "Daft Punk",
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "tempo_bpm": 120.0,
        "valence": 0.8,
        "danceability": 0.8,
        "acousticness": 0.2,
    }
    base.update(overrides)
    return base


def enriched_vibe(**overrides):
    """A target vibe with the continuous target_* fields the translator now emits."""
    base = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.85,
        "likes_acoustic": False,
        "target_valence": 0.75,
        "target_danceability": 0.80,
        "target_acousticness": 0.20,
        "target_tempo_bpm": 118.0,
    }
    base.update(overrides)
    return base


def reasons_text(reasons):
    return " | ".join(reasons)


# --- Baseline / contract ---------------------------------------------------
def test_empty_prefs_scores_zero_with_no_reasons():
    """With no preferences, every scorer self-skips and the song scores 0."""
    score, reasons = score_song({}, make_song())
    assert score == 0.0
    assert reasons == []


def test_score_song_returns_rounded_float_and_reason_list():
    score, reasons = score_song(enriched_vibe(), make_song())
    assert isinstance(score, float)
    assert round(score, 2) == score  # never more than 2 decimals
    assert isinstance(reasons, list)
    assert all(isinstance(r, str) and r for r in reasons)


# --- Individual component math ---------------------------------------------
def test_exact_energy_match_awards_full_energy_weight():
    score, reasons = score_song({"target_energy": 0.8}, make_song(energy=0.8))
    assert score == pytest.approx(DEFAULT_WEIGHTS.energy)
    assert "Energy proximity (100% match" in reasons_text(reasons)


def test_energy_proximity_scales_with_distance():
    # distance 0.2 -> match 0.8 -> 0.8 * energy weight
    score, _ = score_song({"target_energy": 0.8}, make_song(energy=0.6))
    assert score == pytest.approx(0.8 * DEFAULT_WEIGHTS.energy)


def test_exact_genre_beats_partial_beats_none():
    exact, _ = score_song({"favorite_genre": "pop"}, make_song(genre="pop"))
    partial, _ = score_song({"favorite_genre": "pop"}, make_song(genre="indie pop"))
    none, _ = score_song({"favorite_genre": "pop"}, make_song(genre="metal"))
    assert exact == pytest.approx(DEFAULT_WEIGHTS.genre_exact)
    assert partial == pytest.approx(DEFAULT_WEIGHTS.genre_partial)
    assert none == 0.0
    assert exact > partial > none


def test_tempo_proximity_normalised_by_bpm_scale():
    # 30 BPM off over a 60 BPM scale -> match 0.5 -> 0.5 * tempo weight
    score, reasons = score_song(
        {"target_tempo_bpm": 120}, make_song(tempo_bpm=150)
    )
    assert score == pytest.approx(0.5 * DEFAULT_WEIGHTS.tempo)
    assert "Tempo proximity (50% match" in reasons_text(reasons)


def test_acoustic_boolean_dislike_rewards_produced_tracks():
    likes, _ = score_song({"likes_acoustic": True}, make_song(acousticness=0.9))
    dislikes, _ = score_song({"likes_acoustic": False}, make_song(acousticness=0.9))
    assert likes == pytest.approx(DEFAULT_WEIGHTS.acoustic * 0.9)
    assert dislikes == pytest.approx(DEFAULT_WEIGHTS.acoustic * (1.0 - 0.9))


def test_continuous_acoustic_target_overrides_boolean_preference():
    """When target_acousticness is present it wins over likes_acoustic."""
    _, reasons = score_song(
        {"likes_acoustic": True, "target_acousticness": 0.2},
        make_song(acousticness=0.2),
    )
    text = reasons_text(reasons)
    assert "Acousticness proximity" in text
    assert "Acoustic match" not in text  # boolean branch did not fire


def test_valence_bonus_only_for_happy_and_high_valence():
    with_bonus, r1 = score_song({"favorite_mood": "happy"}, make_song(valence=0.8))
    without, r2 = score_song({"favorite_mood": "happy"}, make_song(valence=0.6))
    assert "Upbeat valence bonus" in reasons_text(r1)
    assert "Upbeat valence bonus" not in reasons_text(r2)
    assert with_bonus == pytest.approx(without + DEFAULT_WEIGHTS.valence_bonus)


# --- Self-skipping behaviour -----------------------------------------------
def test_sparse_profile_only_exercises_available_components():
    """A genre-only profile must not emit energy/valence/tempo reasons."""
    _, reasons = score_song({"favorite_genre": "pop"}, make_song())
    text = reasons_text(reasons)
    assert "Exact genre match" in text
    for absent in ("Energy proximity", "Valence proximity",
                   "Danceability proximity", "Tempo proximity"):
        assert absent not in text


def test_enriched_vibe_exercises_continuous_components():
    _, reasons = score_song(enriched_vibe(), make_song())
    text = reasons_text(reasons)
    for present in ("Energy proximity", "Valence proximity",
                    "Danceability proximity", "Tempo proximity"):
        assert present in text


# --- Weight configurability ------------------------------------------------
def test_custom_weights_change_the_score():
    prefs, song = {"target_energy": 0.8}, make_song(energy=0.6)
    default, _ = score_song(prefs, song)
    boosted, _ = score_song(prefs, song, weights=ScoringWeights(energy=4.0))
    assert boosted == pytest.approx(2.0 * default)


def test_zero_weights_produce_zero_score():
    zeroed = ScoringWeights(
        genre_exact=0.0, genre_partial=0.0, mood_exact=0.0, energy=0.0,
        valence=0.0, danceability=0.0, acoustic=0.0, tempo=0.0, valence_bonus=0.0,
    )
    score, _ = score_song(enriched_vibe(), make_song(), weights=zeroed)
    assert score == 0.0


# --- Discrimination on a single-artist pool --------------------------------
def _daft_punk_pool():
    """Five Daft Punk 'pop' tracks that differ only on the continuous axes."""
    return [
        make_song(title="Get Lucky", energy=0.81, valence=0.86,
                  danceability=0.79, acousticness=0.10, tempo_bpm=116),
        make_song(title="Instant Crush", energy=0.70, valence=0.42,
                  danceability=0.55, acousticness=0.18, tempo_bpm=105),
        make_song(title="One More Time", energy=0.93, valence=0.90,
                  danceability=0.83, acousticness=0.05, tempo_bpm=123),
        make_song(title="Around the World", energy=0.88, valence=0.66,
                  danceability=0.90, acousticness=0.08, tempo_bpm=121),
        make_song(title="Veridis Quo", energy=0.55, valence=0.30,
                  danceability=0.48, acousticness=0.35, tempo_bpm=98),
    ]


def test_same_artist_pool_yields_distinct_scores():
    """The exact scenario that used to collapse to five identical 5.55s."""
    vibe = enriched_vibe()
    scores = [score_song(vibe, t)[0] for t in _daft_punk_pool()]
    assert len(set(scores)) == len(scores)  # every track separable


def test_same_artist_ranking_favours_closest_vibe():
    vibe = enriched_vibe()
    ranked = recommend_songs(vibe, _daft_punk_pool(), k=5)
    titles = [song["title"] for song, _score, _why in ranked]
    # 'Get Lucky' is closest to the target vibe; 'Veridis Quo' is farthest.
    assert titles[0] == "Get Lucky"
    assert titles[-1] == "Veridis Quo"
    # Scores are sorted strictly descending (no ties in this pool).
    pool_scores = [score for _s, score, _w in ranked]
    assert pool_scores == sorted(pool_scores, reverse=True)
    assert len(set(pool_scores)) == len(pool_scores)


def test_recommend_songs_respects_k():
    ranked = recommend_songs(enriched_vibe(), _daft_punk_pool(), k=3)
    assert len(ranked) == 3
    assert all(len(item) == 3 for item in ranked)  # (song, score, explanation)


# --- OOP path parity -------------------------------------------------------
def test_oop_recommender_separates_same_artist_tracks():
    songs = [
        Song(id=1, title="High Vibe", artist="Daft Punk", genre="pop",
             mood="happy", energy=0.85, tempo_bpm=118, valence=0.9,
             danceability=0.85, acousticness=0.1),
        Song(id=2, title="Low Vibe", artist="Daft Punk", genre="pop",
             mood="happy", energy=0.30, tempo_bpm=90, valence=0.3,
             danceability=0.4, acousticness=0.6),
    ]
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.85, likes_acoustic=False)
    results = Recommender(songs).recommend(user, k=2)
    assert [s.title for s in results] == ["High Vibe", "Low Vibe"]


# --- Weighted preference path tests ----------------------------------------
def test_weighted_genre_and_mood_scoring():
    # Test that weighted genres and moods yield scaled points
    prefs = {
        "favorite_genres": {"pop": 0.6, "jazz": 0.4},
        "favorite_moods": {"happy": 0.8, "chill": 0.2},
    }
    pop_happy_song = make_song(genre="pop", mood="happy", valence=0.5)
    score, reasons = score_song(prefs, pop_happy_song)
    expected_genre_pts = DEFAULT_WEIGHTS.genre_exact * 0.6
    expected_mood_pts = DEFAULT_WEIGHTS.mood_exact * 0.8
    assert score == pytest.approx(expected_genre_pts + expected_mood_pts)
    
    text = " | ".join(reasons)
    assert "Exact genre match (pop, weight 0.60" in text
    assert "Mood match (happy, weight 0.80" in text


def test_other_features_outrank_low_weighted_genre():
    # Song 1: Low-weighted genre ("jazz" at 0.1 weight), but perfect match on energy/valence/tempo
    # Song 2: High-weighted genre ("pop" at 0.9 weight), but very poor features (0 match)
    prefs = {
        "favorite_genres": {"pop": 0.9, "jazz": 0.1},
        "target_energy": 0.8,
        "target_valence": 0.8,
        "target_tempo_bpm": 120.0,
    }
    jazz_perfect_song = make_song(
        genre="jazz",
        energy=0.8,
        valence=0.8,
        tempo_bpm=120.0,
    )
    pop_poor_song = make_song(
        genre="pop",
        energy=0.0, # distance 0.8 -> match 0.2 -> 0.2 * energy weight (0.4 pts)
        valence=0.0, # distance 0.8 -> match 0.2 -> 0.2 * valence weight (0.3 pts)
        tempo_bpm=60.0, # distance 60 -> match 0.0 -> 0 pts
    )
    
    score_jazz, _ = score_song(prefs, jazz_perfect_song)
    score_pop, _ = score_song(prefs, pop_poor_song)
    
    # Jazz should outrank pop because the feature proximity scores dominate over the low-weighted genre
    assert score_jazz > score_pop

