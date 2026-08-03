# VibeFinder 2.0: The AI DJ & Dynamic Profiler

## Base Project Identification
**Original Project:** VibeFinder 1.0 (Modules 1-3)
**Original Summary:** VibeFinder 1.0 was a static CLI music recommendation engine that connected a user's personal taste profile with matching songs from a hardcoded 18-song CSV catalog. It calculated numeric scores based on genre, mood, energy level, acoustic attributes, and valence to return a ranked list of suggestions.

## Title and Summary
**VibeFinder 2.0** evolves the static CLI tool into a React frontend where users pick their favorite artists in a curated onboarding flow. The FastAPI backend leverages the **Deezer API** to fetch similar tracks, uses **Gemini** to classify those and generate a personalized intro and the mathematically ranked playlist.

## Architecture Overview
The system relies on an **Agentic Workflow** composed of three distinct LLM agents wrapped around a deterministic mathematical scoring engine:
1. **The Vibe Translator Agent**: Calculates the target algorithmic metrics (energy, mood, genre) from human inputs (artist names).
2. **The Classifier Agent**: Classifies raw tracks pulled from the Deezer API, using a batched strategy to prevent rate limits.
3. **The DJ Agent**: Generates a personalized intro and summarizes the final playlist into natural language commentary.

*(See assets/diagrams/architecture.mmd for the full visual flow: Input -> Fetch -> Classifier -> Scorer -> DJ -> UI).*

## Setup Instructions

### 1. Backend (FastAPI)
1. From the **project root** (the backend runs as the `backend` package, so do not `cd` into it):
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # or .venv\Scripts\activate on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the root directory:
   ```text
   GEMINI_API_KEY=your_gemini_api_key
   ```
5. Start the server:
   ```bash
   uvicorn backend.server:app --reload --port 8000
   ```

### 2. Frontend (React + Vite)
1. Open a new terminal and navigate to the frontend: `cd frontend`
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open the provided localhost link (usually `http://localhost:5173`) in your browser.

## Sample Interactions (Execution Evidence)

These are **real, unedited responses** captured from `POST /api/recommend` (playlists trimmed to keep the snippet short; cover/preview URLs truncated).

### Example 1: High Energy EDM

**Request:**
```json
{
  "user_name": "Alex",
  "selected_artists": ["Daft Punk", "Justice", "The Weeknd"]
}
```

**Response `200 OK`:**
```json
{
  "user_name": "Alex",
  "source": "deezer",
  "target_vibe": {
    "favorite_genre": "edm",
    "favorite_mood": "intense",
    "target_energy": 0.85,
    "likes_acoustic": false
  },
  "dj_intro": "If you've been craving that heavy French touch and neon-soaked groove, I see you. Stay locked right here because we're diving straight into the dark, pulsating world of \"World Away\" with the Marie Davidson Remix.",
  "playlist": [
    {
      "title": "World Away (Marie Davidson Remix)",
      "artist": "Etienne de Crécy",
      "genre": "edm",
      "mood": "intense",
      "energy": 0.85,
      "tempo_bpm": 125.0,
      "valence": 0.45,
      "danceability": 0.7,
      "acousticness": 0.04,
      "cover_url": "https://cdn-images.dzcdn.net/images/cover/8adff8867bde078c...",
      "preview_url": "https://cdnt-preview.dzcdn.net/api/1/1/f/d/f/0/fdf1bafbdeb...",
      "score": 8.44,
      "reasons": [
        "Exact genre match (+3.0)",
        "Mood match (+2.0)",
        "Energy proximity (100% match, +2.00)",
        "Produced/Electronic match (+1.44)"
      ]
    }
    // ... 4 more tracks
  ]
}
```

> Note: the DJ intro never addresses the listener by name — the name is untrusted free-text and is deliberately kept out of the LLM prompt (see model card). Personalization comes from the selected artists and the top track; the UI greets the user by name separately.

### Example 2: Chill Acoustic

**Request:**
```json
{
  "user_name": "Sarah",
  "selected_artists": ["Fleet Foxes", "Bob Marley", "Taylor Swift"]
}
```

**Response `200 OK`:**
```json
{
  "user_name": "Sarah",
  "source": "deezer",
  "target_vibe": {
    "favorite_genre": "folk",
    "favorite_mood": "chill",
    "target_energy": 0.5,
    "likes_acoustic": true
  },
  "dj_intro": "From the soaring harmonies of Fleet Foxes and the timeless grooves of Bob Marley to the brilliant storytelling of Taylor Swift, your taste spans generations. Now, get ready to feel inspired as you listen to José González and 'Stay Alive' right here on your airwaves.",
  "playlist": [
    {
      "title": "Stay Alive (From \"The Secret Life of Walter Mitty\" Soundtrack)",
      "artist": "José González",
      "genre": "folk",
      "mood": "chill",
      "energy": 0.48,
      "tempo_bpm": 118.0,
      "valence": 0.52,
      "danceability": 0.58,
      "acousticness": 0.85,
      "cover_url": "https://cdn-images.dzcdn.net/images/cover/3e8f8b9ff3d770fd...",
      "preview_url": "https://cdnt-preview.dzcdn.net/api/1/1/7/f/9/0/7f9fea3d3ab...",
      "score": 8.23,
      "reasons": [
        "Exact genre match (+3.0)",
        "Mood match (+2.0)",
        "Energy proximity (98% match, +1.96)",
        "Acoustic match (+1.27)"
      ]
    }
  ]
}
```

## Design Decisions
- **Agentic Workflow**: This project uses multiple LLM agents that handle distinct tasks: translation, classification, and text generation.
- **Batched Classification**: To avoid hitting rate limits while using Gemini API for the classification task, I bundled the tracks into a single JSON array payload.
- **Request Rate Limiting**: Because each recommendation makes several Gemini calls, the `/api/recommend` endpoint caps each client (by IP) at **3 playlist generations per rolling hour**, returning HTTP `429` afterward. Both the limit and the window are configurable via the `RATE_LIMIT_MAX_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` env vars. The counter lives in process memory (a lightweight cost guardrail, not a security boundary) and resets on restart.
- **Artist Selection**: By restricting the user to selecting from a curated list of 16 real-world artists, I tried to prevent edge-case hallucinations and ensure the translator always has solid context to work from.

## Testing Summary
- **Automated Testing**: The core scoring mathematical logic from src/recommender.py is fully covered by Pytest (test_recommender.py), ensuring that our backend integration did not break the VibeFinder 1.0 logic. 
- **LLM Reliability**: By enforcing `response_mime_type="application/json"` and structuring the batched payload carefully, Gemini returned reliable JSON during local testing. A deterministic fallback system guarantees a valid response even when a Gemini call fails or returns malformed output.
- **API Reliability**: The Deezer API requires no authentication keys, making the system immediately reproducible for anyone cloning the repository without additional credential setup.

## Reflection
This project made me realize the complexities of combining deterministic algorithms with non-deterministic LLMs. I learned that rate limits are a major constraint, forcing creative architecture and engineering solutions. I saw how LLM's can be used to create a more personalized user experience, but can also introduce new challenges like hallucination and bias. Using deterministic techniques and guardrails can help mitigate these risks. 

*(See model_card.md for a deeper reflection on AI, ethics, and model biases).*