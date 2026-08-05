# VibeFinder 2.0 — Model Card & Specialization Report

## Model Overview
- **Model**: `gemini-flash-lite-latest` via `google-generativeai` SDK
- **Task**: Multi-agent music preference inference, batched track feature classification, and personalized radio DJ intro generation.
- **Orchestration**: Three specialized agent functions operating with JSON response mode (`response_mime_type="application/json"`, `temperature=0.4`).

---

## Specialization Behavior

### Prompting Patterns

#### 1. Agent 1: Vibe Translator
* **Goal**: Infer continuous user taste parameters from artist selections.
* **Prompt Exemplar Pattern**:
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

#### 2. Agent 2: Song Classifier
* **Goal**: Extract multi-dimensional audio feature estimations from track titles and artists in a single array payload.
* **Prompt Exemplar Pattern**:
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

#### 3. Agent 3: DJ Intro
* **Goal**: Write a short, personalized DJ intro for the curated playlist that references the selected artists and the top track.
* **Prompt Exemplar Pattern**:
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

---

### Output Analysis

#### 1. Classification & Schema Compliance

- **Unconstrained Baseline Output**:
  ```text
  "Sure! Here is the analysis for Get Lucky by Daft Punk: The song is energetic (around 8/10) with a funk-pop vibe and happy mood. Tempo is pretty fast."
  ```
  *Issue*: Unparseable plain text, non-standard genre (`funk-pop`), unnormalized scale (`8/10`).

- **Specialized Gemini Output**:
  ```json
  {"id": 0, "genre": "edm", "mood": "happy", "energy": 0.82, "acousticness": 0.04, "valence": 0.86, "tempo_bpm": 116, "danceability": 0.79}
  ```
  *Advantage*: Strict JSON compliance, exact matching with system genre, normalized floats $[0.0, 1.0]$.

## Limitations
The LLM classifier is a key component created to test replacing paid third-party music APIs after encountering access friction. Because the classifier estimates song attributes from titles and artists instead of listening to raw audio, it can mislabel obscure songs. Additionally, the track pool retrieved from public APIs favors mainstream artists, creating a bias toward popular music.

## Misuse and Prevention
- **Misuse Case**: An AI that dynamically generates recommendations based on user inputs could be tricked into generating inappropriate, hateful, or off-brand content if untrusted free-text were fed into the prompt.
- **Prevention**: We keep untrusted text out of the LLM prompts as much as possible. The only free-text field is the user's name, and it is never sent to any Gemini call. Everything that reaches the model is from a fixed curated list of options, so the model always has safe context. Finally, all Gemini calls use strict JSON output and Pydantic validation, which acts as a guardrail against the LLM breaking out of its classification role.

## Surprises
I was surprised how consistent the energy levels matched my expectations for the artists selected. Even though the model does not have access to audio features, it was able to predict the energy level of the songs based on the artist and song name alone. To maintain reliability, I used a curated list of 16 popular artists to choose from, and also limited the LLM output using JSON schema and strict validation. 

## AI Collaboration
- **Helpful Suggestion**: When designing the system architecture, AI suggested using API's like deezer or spotify to fetch songs and also suggested using gemini flash for classification. This was a good suggestion as it helped me create a broader system outside the limitations of the initial csv file.
- **Flawed Suggestion**: Initially, the AI suggested fetching songs from Spotify's recommendation endpoint, which required user authentication. It failed to account for the lack of access to that specific endpoint causing a roadblock in the planning stage. This led me to using deezer API which does not require user authentication but lacked the ability to fetch songs based on metadata like energy and valence. Additionally, the AI suggested using gemini flash for classification task which was a good suggestion, but it failed to account for the lack of access to the specific gemini-2.5-flash-lite model.
