# VibeFinder 2.0 — Model Card

## Model Overview
- **Model**: `gemini-flash-lite-latest` via `google-generativeai` SDK
- **Task**: Multi-agent music preference inference, batched track feature classification, and personalized radio DJ intro generation.
- **Orchestration**: Three specialized agent functions operating with JSON response mode.

---

## Model Behavior

### Prompting Patterns

#### 1. Agent 1: Vibe Translator
* **Goal**: Infer continuous user taste parameters from artist selections.
* **Prompt Pattern**:
  <details>
  <summary><code>View Example</code></summary>

  ```text
  You are a music-taste inference engine. Translate artist lists into user vibe vectors.

  [Example 1]
  Input: ["Daft Punk", "Justice"]
  Output: {"favorite_genre": "edm", "favorite_mood": "intense", "target_energy": 0.85, "likes_acoustic": false, "target_valence": 0.55, "target_danceability": 0.80, "target_acousticness": 0.05, "target_tempo_bpm": 124}

  [Example 2]
  Input: ["Fleet Foxes", "Bob Marley"]
  Output: {"favorite_genre": "folk", "favorite_mood": "chill", "target_energy": 0.45, "likes_acoustic": true, "target_valence": 0.65, "target_danceability": 0.55, "target_acousticness": 0.75, "target_tempo_bpm": 105}

  [Target Execution]
  Input: ["Kendrick Lamar", "The Weeknd"]
  Output: {"favorite_genre": "hip hop", "favorite_mood": "intense", "target_energy": 0.75, "likes_acoustic": false, "target_valence": 0.55, "target_danceability": 0.65, "target_acousticness": 0.15, "target_tempo_bpm": 120}
  ```
  </details>

#### 2. Agent 2: Song Classifier
* **Goal**: Extract multi-dimensional audio feature estimations from track titles and artists in a single array payload.
* **Prompt Pattern**:
  <details>
  <summary><code>View Example</code></summary>

  ```text
  You are a music-analysis engine. Map each input track ID to system parameters.
  Allowed genres: ['pop', 'lofi', 'rock', 'jazz', 'edm', 'classical', 'metal', 'reggae', 'hip hop', 'blues', 'folk', 'world']
  Allowed moods: ['happy', 'chill', 'intense', 'focused', 'aggressive', 'dramatic', 'nostalgic']

  [Example Input]
  [{"id": 0, "title": "Get Lucky", "artist": "Daft Punk"}, {"id": 1, "title": "Redemption Song", "artist": "Bob Marley"}]

  [Example Output]
  [
    {"id": 0, "genre": "edm", "mood": "happy", "energy": 0.82, "acousticness": 0.04, "valence": 0.86, "tempo_bpm": 116, "danceability": 0.79},
    {"id": 1, "genre": "reggae", "mood": "chill", "energy": 0.38, "acousticness": 0.88, "valence": 0.64, "tempo_bpm": 116, "danceability": 0.62}
  ]
  ```
  </details>

#### 3. Agent 3: DJ Intro
* **Goal**: Write a short, personalized DJ intro for the curated playlist that references the selected artists and the top track.
* **Prompt Pattern**:
  <details>
  <summary><code>View Example</code></summary>

  ```text
  Write a 2-3 sentence custom radio DJ intro for a listener based on their love for [Artists]. Do NOT address the listener by name or invent a name; speak to them generically (e.g. "you"). Mention they are about to hear "[Top Title]". Keep it under 60 words. Return ONLY the intro text as a JSON object: {"intro": "..."}

  [Example Input]
  Artists: ["Daft Punk", "Justice"]
  Top Title: "Get Lucky"

  [Example Output]
  {"intro": "You're locked in to VibeFinder Radio! We're serving up a high-energy mix inspired by your love for Daft Punk and Justice. Up first is the legendary track \"Get Lucky\"—turn up the volume!"}

  [Target Execution]
  Input: ["Kendrick Lamar", "The Weeknd"] (Top Title: "Starboy")
  Output: {"intro": "If you've been craving that masterclass lyricism from Kendrick and the dark, hypnotic grooves of The Weeknd, you're in the right place. Turn it up because you're about to hear 'Starboy'."}
  ```
  </details>

---

## Recommendation Algorithm & Proximity Logic

The system utilizes a hybrid approach: specialized LLM agents extract music preference targets and song attributes, which are then fed into a deterministic mathematical scoring engine to rank recommendations.

### Proximity Scoring Formula
For continuous features, the proximity score is computed by normalizing the absolute difference between the target preference and the song's actual value. The unit_scale is set to 60.0 BPM to normalize the difference over a reasonable BPM window.

### Scoring Weights
The final score of a track is the sum of all weighted matching components:

| Feature / Match Type | Weight | Description |
| :--- | :--- | :--- |
| **Exact Genre** | 2.0 | Awarded if target genre matches song genre exactly |
| **Partial Genre** | 1.0 | Awarded if target genre is a substring of song genre (or vice-versa) |
| **Exact Mood** | 1.5 | Awarded if target mood matches song mood exactly |
| **Energy Proximity** | 2.0 | Proximity score based on target energy |
| **Valence Proximity** | 1.5 | Proximity score based on target valence |
| **Danceability Proximity** | 1.5 | Proximity score based on target danceability |
| **Acousticness Proximity** | 1.5 | Proximity score based on target acousticness |
| **Tempo Proximity** | 1.0 | Proximity score based on target tempo (normalized over 60.0 BPM) |
| **Valence Bonus** | 0.5 | Upbeat valence bonus if target mood is "happy" and song valence $\ge 0.7$ |

### Categorical vs. Continuous Features
Continuous features do the primary ranking, while matches on categorical features (genre, mood) are designed to guide the broader direction and break ranking ties.

---

## Model Evaluation & Performance

To ensure the recommendation system is accurate and fast, we run an evaluation script (evaluate.py) across **7 test profiles**  against a controlled pool of songs.

Here is a summary of the model's performance:

| Metric | Target | Backup Mode (No API Keys) | Live Gemini API Mode |
| :--- | :--- | :--- | :--- |
| **Alignment** | > 0.80 | 0.86  | 0.82  |
| **Latency** | < 2.0s | 1.1 ms | 4.3s  |
| **Fallback Rate** | 0% | 100%  | 0.0%  |

* **Raw Output**: Without structural JSON output constraints, raw model outputs failed to parse $100\%$ of the time, resulting in total degradation.
* **Backup Mode**: When offline or without API keys, the system relies on deterministic math/hashing backups to keep running instantly, but it will not benefit from Gemini's dynamic analysis.

### Known Limitations & Biases
* **Wrong Recommendation Example (Genre Dominance)**:
  * **The Scenario**: A user selects Taylor Swift, Dua Lipa, and Billie Eilish, leading to an inferred target of "happy pop" with an energy target of 0.728.
  * **The Issue**: Billie Eilish's song Bad Guy is recommended. In reality, Bad Guy is a dark, low-energy, and moody song.
  * **Why it gets it wrong**: Because the system awards large point bonuses for exact genre matches, Bad Guy outscores actual happy, upbeat songs of other genres. The point boost overshadows the actual mood and energy mismatch.

### What Changed Because of the Results
* **From loops to batches**: Initially, we classified songs one-by-one (taking > 8 seconds and hitting rate limits instantly). We changed this to batch-classify songs in one single request, dropping latency to under 1.5 seconds.
* **Continuous scoring**: VibeFinder 1.0 only filtered by broad genre, causing tie-scores. We upgraded the system to score the exact distance of musical attributes, providing unique and accurate rankings.

### Misuse and Prevention
- **Misuse Case**: An AI that dynamically generates recommendations based on user inputs could be tricked into generating inappropriate, hateful, or off-brand content if untrusted free-text were fed into the prompt.
- **Prevention**: We keep untrusted text out of the LLM prompts as much as possible. The only free-text field is the user's name, and it is never sent to any Gemini call. Everything that reaches the model is from a fixed curated list of options, so the model always has safe context. Finally, all Gemini calls use strict JSON output as a guardrail to prevent breaking out of its intended role.

### Surprises
I was surprised how consistent the energy levels matched my expectations for the artists selected. Even though the model does not have access to audio features, it was able to predict the energy level of the songs based on the artist and song name alone. To maintain reliability, I used a curated list of 16 popular artists to choose from, and also limited the LLM output using JSON schema and strict validation. 

### AI Collaboration
- **Helpful Suggestion**: When designing the system architecture, AI suggested using API's like deezer or spotify to fetch songs and also suggested using gemini flash for classification. This was a good suggestion as it helped me create a broader system outside the limitations of the initial csv file.
- **Flawed Suggestion**: Initially, the AI suggested fetching songs from Spotify's recommendation endpoint, which required user authentication. It failed to account for the lack of access to that specific endpoint causing a roadblock in the planning stage. This led me to using deezer API which does not require user authentication but lacked the ability to fetch songs based on metadata like energy and valence. Additionally, the AI suggested using gemini flash for classification task which was a good suggestion, but it failed to account for the lack of access to the specific gemini-2.5-flash-lite model.
