# VibeFinder Product & Engineering Roadmap

This roadmap outlines the planned iterations and release plan leading from **VibeFinder 2.0** to **VibeFinder 3.0**.

---

## Milestone Overview

| Iteration | Version | Status | Milestone Focus |
| :--- | :--- | :--- | :--- |
| **Iteration 1** | `v2.0.0` | **Completed** | Full-Stack Web Init (FastAPI + React UI + Agentic DJ Scaffold) |
| **Iteration 2** | `v2.1.0` | **Completed** | Deezer API pool, Weighted Scoring, Gemini Resilience & System Evaluation |
| **Iteration 3** | `v2.2.0` | **Next Up** | Session Persistence, History Logging & Spotify/Apple Music Sync |
| **Iteration 4** | `v2.3.0` | Planned | Full Audio Playback & TTS Integration |
| **Major 3.0** | `v3.0.0` | **Target Vision** | Real-Time Personalized DJ & Autonomous Radio Agent |

---

## Iteration Breakouts

### Iteration 1 — `v2.0.0`: Full-Stack Web Initialization (Completed)
- [x] **React + Vite Frontend**: Initial artist selection onboarding grid, responsive dark UI, preview player scaffold.
- [x] **FastAPI Backend Server**: Initial API structure (`POST /api/recommendations` returning `201 Created`, `GET /api/health`).
- [x] **Agentic Pipeline Scaffold**: Basic multi-agent orchestration for vibe translation and DJ intros.

---

### Iteration 2 — `v2.1.0`: Keyless Deezer API, Agent Resilience & Weighted Scoring (Current)
- [x] **Deezer API Integration**: Keyless live track pool fetching replacing static CSV files.
- [x] **Weighted Multi-Attribute Scoring**: Resolved single-genre dominance bias in `recommender.py` and `agent.py`.
- [x] **Gemini Resilience & Degraded Fallbacks**: Chunked track classification with deterministic fallbacks and UI degraded indicators.
- [x] **Evaluation Harness & CI/CD**: Added system evaluation harness (`evaluate.py`), rate-limiting, Docker support, and GitHub Actions tests.

---

### Iteration 3 — `v2.2.0`: Session Persistence & Export Integrations (Next)
- [ ] **Session & History Tracking**:
  - LocalStorage / SQLite session history so users can review past playlists and generated DJ intros.
- [ ] **Playlist Export**:
  - OAuth integration for exporting generated VibeFinder playlists directly to Spotify and Apple Music accounts.
- [ ] **User Feedback Loop**:
  - Track-level "thumbs up / thumbs down" buttons to re-rank current playlist dynamically.

---

### Iteration 4 — `v2.3.0`: TTS Integration & Audio Playback
- [ ] **Web Audio API audio player**:
  - Real-time audio playback for each track using YouTube Music API.
- [ ] **Text-to-speech integration**:
  - Live TTS narration for the radio DJ with crossfading between songs.

---

## VibeFinder 3.0 — `v3.0.0`: The Autonomous Interactive Voice DJ

**Goal**: Transform VibeFinder from a web playlist generator into a live, autonomous AI radio station.

### Key Pillars of 3.0:
1. **Streaming Audio Voice DJ**:
   - Real-time Text-to-Speech (Gemini Multimodal Live / ElevenLabs integration) delivering spoken transitions between songs.
2. **Multi-Modal Context Awareness**:
   - Integration with ambient context (time of day, weather API, calendar state) to autonomously infer current listener vibe.
3. **User Feedback Loop**:
   - Real-time feedback mechanism for users to adjust the playlist based on their preferences.
4. **Social Connectivity**:
   - Integration with social media platforms to share playlists and recommendations with friends.
