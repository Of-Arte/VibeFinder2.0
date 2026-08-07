import csv
from typing import List, Dict, Tuple, Optional, Iterable
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    cover_url: str = ""
    preview_url: str = ""

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic for Song and UserProfile objects.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _song_to_dict(self, song: Song) -> Dict:
        return {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "genre": song.genre,
            "mood": song.mood,
            "energy": song.energy,
            "tempo_bpm": song.tempo_bpm,
            "valence": song.valence,
            "danceability": song.danceability,
            "acousticness": song.acousticness,
            "cover_url": song.cover_url,
            "preview_url": song.preview_url,
        }

    def _user_to_dict(self, user: UserProfile) -> Dict:
        return {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Returns top k recommended songs sorted by score descending."""
        user_prefs = self._user_to_dict(user)
        scored_songs = []
        for song in self.songs:
            song_dict = self._song_to_dict(song)
            score, _ = score_song(user_prefs, song_dict)
            scored_songs.append((song, score))
        
        scored_songs.sort(key=lambda x: x[1], reverse=True)
        return [song for song, score in scored_songs[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns plain language explanation for why a song was recommended."""
        user_prefs = self._user_to_dict(user)
        song_dict = self._song_to_dict(song)
        _, reasons = score_song(user_prefs, song_dict)
        return ", ".join(reasons) if reasons else "Matches baseline profile criteria."

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file and converts numerical fields to appropriate types.
    """
    songs = []
    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            songs.append({
                "id": int(row["id"]),
                "title": row["title"],
                "artist": row["artist"],
                "genre": row["genre"],
                "mood": row["mood"],
                "energy": float(row["energy"]),
                "tempo_bpm": float(row["tempo_bpm"]),
                "valence": float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs

@dataclass(frozen=True)
class ScoringWeights:
    """
    Tunable weights for each scoring component.

    Categorical matches (genre, mood) are deliberately modest: within a
    single-genre or single-artist candidate pool they fire identically for
    every track and therefore carry no ranking information. The continuous
    proximity features (energy, valence, danceability, tempo) are what
    actually separate tracks, so they carry the bulk of the weight.
    """
    genre_exact: float = 2.0
    genre_partial: float = 1.0
    mood_exact: float = 1.5
    energy: float = 2.0
    valence: float = 1.5
    danceability: float = 1.5
    acoustic: float = 1.5
    tempo: float = 1.0
    valence_bonus: float = 0.5
    # Tempo distance is normalised over this BPM window before scoring.
    tempo_scale_bpm: float = 60.0


DEFAULT_WEIGHTS = ScoringWeights()

# A scored contribution: (points_awarded, human-readable explanation).
Component = Tuple[float, str]


def _target(prefs: Dict, *keys: str) -> Optional[float]:
    """Return the first present, non-None preference value among ``keys``."""
    for key in keys:
        value = prefs.get(key)
        if value is not None:
            return value
    return None


def _proximity(target: float, actual: float, weight: float,
               unit_scale: float = 1.0) -> Tuple[float, float]:
    """
    Score closeness between a target and an actual value.

    Returns (points, match_fraction) where match_fraction is a 0..1 closeness
    used only for display. Distance is normalised by ``unit_scale`` so features
    on different ranges (e.g. tempo in BPM) can share the same 0..1 math.
    """
    distance = abs(actual - target) / unit_scale
    match = max(0.0, 1.0 - distance)
    return weight * match, match


def _score_genre(prefs: Dict, song: Dict, w: ScoringWeights) -> Iterable[Component]:
    genre = str(song.get("genre", "")).strip().lower()
    if not genre:
        return []

    # If new weighted genres are present
    weighted_genres = prefs.get("favorite_genres")
    if isinstance(weighted_genres, dict):
        components = []
        for target, weight in weighted_genres.items():
            target_clean = str(target).strip().lower()
            if target_clean == genre:
                pts = w.genre_exact * weight
                components.append((pts, f"Exact genre match ({target_clean}, weight {weight:.2f}, +{pts:.2f})"))
            elif target_clean in genre or genre in target_clean:
                pts = w.genre_partial * weight
                components.append((pts, f"Partial genre match ({target_clean}, weight {weight:.2f}, +{pts:.2f})"))
        if components:
            return [max(components, key=lambda x: x[0])]

    # Fallback to legacy behavior
    target = (prefs.get("favorite_genre") or prefs.get("genre") or "").strip().lower()
    if not target:
        return []
    if target == genre:
        return [(w.genre_exact, f"Exact genre match (+{w.genre_exact:.1f})")]
    if target in genre or genre in target:
        return [(w.genre_partial, f"Partial genre match (+{w.genre_partial:.1f})")]
    return []


def _score_mood(prefs: Dict, song: Dict, w: ScoringWeights) -> Iterable[Component]:
    mood = str(song.get("mood", "")).strip().lower()
    if not mood:
        return []

    # If new weighted moods are present
    weighted_moods = prefs.get("favorite_moods")
    if isinstance(weighted_moods, dict):
        components = []
        for target, weight in weighted_moods.items():
            target_clean = str(target).strip().lower()
            if target_clean == mood:
                pts = w.mood_exact * weight
                components.append((pts, f"Mood match ({target_clean}, weight {weight:.2f}, +{pts:.2f})"))
        if components:
            return [max(components, key=lambda x: x[0])]

    # Fallback to legacy behavior
    target = (prefs.get("favorite_mood") or prefs.get("mood") or "").strip().lower()
    if target and target == mood:
        return [(w.mood_exact, f"Mood match (+{w.mood_exact:.1f})")]
    return []


def _score_energy(prefs: Dict, song: Dict, w: ScoringWeights) -> Iterable[Component]:
    target = _target(prefs, "target_energy", "energy")
    if target is None:
        return []
    points, match = _proximity(float(target), float(song.get("energy", 0.5)), w.energy)
    return [(points, f"Energy proximity ({match:.0%} match, +{points:.2f})")]


def _score_valence(prefs: Dict, song: Dict, w: ScoringWeights) -> Iterable[Component]:
    target = _target(prefs, "target_valence", "valence")
    if target is None:
        return []
    points, match = _proximity(float(target), float(song.get("valence", 0.5)), w.valence)
    return [(points, f"Valence proximity ({match:.0%} match, +{points:.2f})")]


def _score_danceability(prefs: Dict, song: Dict, w: ScoringWeights) -> Iterable[Component]:
    target = _target(prefs, "target_danceability", "danceability")
    if target is None:
        return []
    points, match = _proximity(float(target), float(song.get("danceability", 0.5)), w.danceability)
    return [(points, f"Danceability proximity ({match:.0%} match, +{points:.2f})")]


def _score_tempo(prefs: Dict, song: Dict, w: ScoringWeights) -> Iterable[Component]:
    target = _target(prefs, "target_tempo_bpm", "tempo_bpm")
    if target is None:
        return []
    points, match = _proximity(
        float(target), float(song.get("tempo_bpm", 110.0)), w.tempo,
        unit_scale=w.tempo_scale_bpm,
    )
    return [(points, f"Tempo proximity ({match:.0%} match, +{points:.2f})")]


def _score_acoustic(prefs: Dict, song: Dict, w: ScoringWeights) -> Iterable[Component]:
    song_acoustic = float(song.get("acousticness", 0.5))
    # Prefer a continuous target when the vibe provides one; otherwise fall
    # back to the boolean like/dislike preference.
    target = _target(prefs, "target_acousticness", "acousticness")
    if target is not None:
        points, match = _proximity(float(target), song_acoustic, w.acoustic)
        return [(points, f"Acousticness proximity ({match:.0%} match, +{points:.2f})")]
    likes_acoustic = prefs.get("likes_acoustic")
    if likes_acoustic is None:
        return []
    if likes_acoustic:
        points = w.acoustic * song_acoustic
        return [(points, f"Acoustic match (+{points:.2f})")]
    points = w.acoustic * (1.0 - song_acoustic)
    return [(points, f"Produced/Electronic match (+{points:.2f})")]


def _score_valence_bonus(prefs: Dict, song: Dict, w: ScoringWeights) -> Iterable[Component]:
    # Check weighted moods first
    weighted_moods = prefs.get("favorite_moods")
    happy_weight = 0.0
    if isinstance(weighted_moods, dict):
        happy_weight = float(weighted_moods.get("happy", 0.0))
    else:
        target_mood = (prefs.get("favorite_mood") or prefs.get("mood") or "").strip().lower()
        if target_mood == "happy":
            happy_weight = 1.0

    if happy_weight > 0.0 and float(song.get("valence", 0.0)) >= 0.7:
        pts = w.valence_bonus * happy_weight
        return [(pts, f"Upbeat valence bonus (+{pts:.1f})")]
    return []


# Ordered scoring pipeline. Each scorer is pure and self-skips when its target
# preference is absent, so a sparse profile (e.g. the OOP UserProfile path)
# simply exercises fewer components than an enriched vibe target.
_SCORERS = (
    _score_genre,
    _score_mood,
    _score_energy,
    _score_valence,
    _score_danceability,
    _score_tempo,
    _score_acoustic,
    _score_valence_bonus,
)


def score_song(user_prefs: Dict, song: Dict,
               weights: ScoringWeights = DEFAULT_WEIGHTS) -> Tuple[float, List[str]]:
    """
    Score a single song against user preferences by summing weighted components.

    Returns (numeric_score, explanation_reasons). Continuous proximity features
    (energy, valence, danceability, tempo) do the discriminating work; the
    categorical genre/mood matches only break ranking ties when the pool spans
    multiple genres.
    """
    total = 0.0
    reasons: List[str] = []
    for scorer in _SCORERS:
        for points, reason in scorer(user_prefs, song, weights):
            total += points
            reasons.append(reason)
    return round(total, 2), reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of recommendation logic.
    Scores all songs, sorts descending, and returns top k recommendation tuples (song_dict, score, explanation).
    """
    scored_list = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = ", ".join(reasons) if reasons else "Baseline score"
        scored_list.append((song, score, explanation))

    scored_list.sort(key=lambda item: item[1], reverse=True)
    return scored_list[:k]

