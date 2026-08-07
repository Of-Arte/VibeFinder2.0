# VibeFinder Product & Engineering Roadmap

This roadmap outlines the counted iterations and release plan leading from **VibeFinder 2.0** to **VibeFinder 3.0**.

---

## Milestone Overview

| Iteration | Version | Status | Milestone Focus |
| :--- | :--- | :--- | :--- |
| **Iteration 1** | `v2.0.0` | **Completed** | Full-Stack Web Init (FastAPI + React UI + Agentic DJ Scaffold) |
| **Iteration 2** | `v2.1.0` | **Completed (Current)** | Deezer API pool, Weighted Scoring, Gemini Resilience & System Evaluation |
| **Iteration 3** | `v2.2.0` | **Next Up** | Session Persistence, History Logging & Spotify/Apple Music Sync |
| **Iteration 4** | `v2.3.0` | Planned | Real-Time Audio Visualizer & Customizable DJ Personas |
| **Major 3.0** | `v3.0.0` | **Target Vision** | Real-Time Neural Voice Audio DJ, Voice Commands & Autonomous Radio Agent |

---

## Iteration Breakouts

### Iteration 1 — `v2.0.0`: Full-Stack Web Initialization (Completed)
- [x] **React + Vite Frontend**: Initial artist selection onboarding grid, responsive dark UI, preview player scaffold.
- [x] **FastAPI Backend Server**: Initial API structure (`POST /api/recommend`, `GET /api/health`).
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

### Iteration 4 — `v2.3.0`: Interactive DJ Personas & Audio Visuals
- [ ] **Audio Feature Visualizer**:
  - Real-time audio playback for each track.
- [ ] **Seamless Crossfading**:
  - Smooth Web Audio API gain node crossfading between audio previews.

---

## VibeFinder 3.0 — `v3.0.0`: The Autonomous Interactive Voice DJ

**Goal**: Transform VibeFinder from a web playlist generator into a live, voice-interactive AI radio station.

### Key Pillars of 3.0:
1. **Streaming Audio Voice DJ**:
   - High-fidelity neural voice synthesis (Gemini Multimodal Live / ElevenLabs integration) delivering spoken transitions between tracks in real time over Web Audio.
2. **Real-time Voice Interaction**:
   - Hands-free mic input ("*Hey DJ, tone down the energy for a bit*") triggering instant live playlist re-alignment.
3. **Multi-Modal Context Awareness**:
   - Integration with ambient context (time of day, weather API, calendar state) to autonomously infer current listener vibe without manual artist selection.
4. **Autonomous Multi-Agent Radio Station**:
   - Specialized background sub-agents providing track trivia, artist backstories, and contextual banter between songs.
