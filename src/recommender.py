import csv
from typing import List, Dict, Tuple, Optional
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

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences based on the Algorithm Recipe.
    Returns a tuple of (numeric_score, explanation_reasons).
    """
    score = 0.0
    reasons = []

    # 1. Genre match logic
    target_genre = (user_prefs.get("favorite_genre") or user_prefs.get("genre") or "").strip().lower()
    song_genre = song.get("genre", "").strip().lower()
    if target_genre and song_genre:
        if target_genre == song_genre:
            score += 3.0
            reasons.append("Exact genre match (+3.0)")
        elif target_genre in song_genre or song_genre in target_genre:
            score += 1.5
            reasons.append("Partial genre match (+1.5)")

    # 2. Mood match logic
    target_mood = (user_prefs.get("favorite_mood") or user_prefs.get("mood") or "").strip().lower()
    song_mood = song.get("mood", "").strip().lower()
    if target_mood and song_mood:
        if target_mood == song_mood:
            score += 2.0
            reasons.append("Mood match (+2.0)")

    # 3. Energy similarity logic
    target_energy = user_prefs.get("target_energy") if "target_energy" in user_prefs else user_prefs.get("energy")
    if target_energy is not None:
        target_energy = float(target_energy)
        song_energy = float(song.get("energy", 0.5))
        distance = abs(song_energy - target_energy)
        energy_score = max(0.0, 2.0 * (1.0 - distance))
        score += energy_score
        reasons.append(f"Energy proximity ({1.0 - distance:.0%} match, +{energy_score:.2f})")

    # 4. Acousticness preference logic
    likes_acoustic = user_prefs.get("likes_acoustic")
    song_acoustic = float(song.get("acousticness", 0.5))
    if likes_acoustic is not None:
        if likes_acoustic:
            acoustic_score = 1.5 * song_acoustic
            score += acoustic_score
            reasons.append(f"Acoustic match (+{acoustic_score:.2f})")
        else:
            acoustic_score = 1.5 * (1.0 - song_acoustic)
            score += acoustic_score
            reasons.append(f"Produced/Electronic match (+{acoustic_score:.2f})")
    elif "acousticness" in user_prefs:
        target_acoustic = float(user_prefs["acousticness"])
        dist = abs(song_acoustic - target_acoustic)
        ac_score = max(0.0, 1.5 * (1.0 - dist))
        score += ac_score
        reasons.append(f"Acousticness proximity (+{ac_score:.2f})")

    # 5. Valence/Vibe bonus
    if target_mood == "happy" and float(song.get("valence", 0.0)) >= 0.7:
        score += 0.5
        reasons.append("Upbeat valence bonus (+0.5)")

    return round(score, 2), reasons

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

